#!/usr/bin/env python3
"""
Mobile Text Input Web Application
A web application that allows text input from mobile devices with automatic clipboard copying and keyboard simulation
"""

import pyperclip
from nicegui import ui, app
from datetime import datetime
import time
import logging
import sys
import platform
import tempfile
import os
import asyncio
from pathlib import Path
from fastapi import Request
import json
from typing import Dict, List, Optional, Any
from instance_manager import create_application_instance_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Import keyboard simulation library
try:
    from pynput.keyboard import Key, Controller

    keyboard_controller = Controller()
    KEYBOARD_AVAILABLE = True
    PYNPUT_AVAILABLE = True
    logger.info("✅ pynput keyboard simulation library loaded successfully")
except ImportError:
    KEYBOARD_AVAILABLE = False
    PYNPUT_AVAILABLE = False
    keyboard_controller = None
    logger.warning("⚠️ pynput not available - keyboard simulation disabled")

# Import voice-to-text libraries
try:
    import whisper
    import torch

    WHISPER_AVAILABLE = True
    TORCH_AVAILABLE = True
    logger.info("✅ OpenAI Whisper loaded successfully")

    # Check for CUDA availability
    if torch.cuda.is_available():
        logger.info("✅ CUDA available - GPU acceleration enabled")
        logger.info(f"🚀 CUDA device count: {torch.cuda.device_count()}")
        logger.info(f"🎯 CUDA device name: {torch.cuda.get_device_name(0)}")
        CUDA_AVAILABLE = True
    else:
        logger.info("💻 CUDA not available - using CPU for voice processing")
        CUDA_AVAILABLE = False

except ImportError as e:
    WHISPER_AVAILABLE = False
    TORCH_AVAILABLE = False
    CUDA_AVAILABLE = False
    logger.warning(f"⚠️ Voice-to-text libraries not available: {e}")

# OS detection and platform-specific setup
CURRENT_OS = platform.system()
logger.info(f"🖥️ Detected operating system: {CURRENT_OS}")

# Windows-specific imports and setup
if CURRENT_OS == "Windows":
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Windows API constants
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        # Window show states
        SW_RESTORE = 9
        SW_SHOW = 5
        SW_SHOWMAXIMIZED = 3
        SW_SHOWMINIMIZED = 2
        SW_SHOWNA = 8
        SW_SHOWNOACTIVATE = 4
        SW_SHOWNORMAL = 1

        WINDOWS_FALLBACK = True
        logger.info("✅ Windows native keyboard simulation available")
        logger.info("✅ Windows API for window management available")
    except ImportError:
        WINDOWS_FALLBACK = False
        user32 = None
        kernel32 = None
        logger.warning("⚠️ Windows native APIs not available")
else:
    WINDOWS_FALLBACK = False
    user32 = None
    kernel32 = None
    SW_RESTORE = SW_SHOW = SW_SHOWMAXIMIZED = None
    SW_SHOWMINIMIZED = SW_SHOWNA = SW_SHOWNOACTIVATE = SW_SHOWNORMAL = None

# macOS detection
IS_MACOS = CURRENT_OS == "Darwin"
IS_WINDOWS = CURRENT_OS == "Windows"

if IS_MACOS:
    logger.info("🍎 macOS detected - will use Cmd+V for paste operations")
elif IS_WINDOWS:
    logger.info("🪟 Windows detected - will use Ctrl+V for paste operations")
else:
    logger.info("🐧 Linux detected - will use Ctrl+V for paste operations")


class VoiceProcessor:
    """Handle voice-to-text processing using OpenAI Whisper with GPU support"""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_loading = False
        self.device = "cuda" if CUDA_AVAILABLE else "cpu"
        self.supported_formats = {
            ".mp3",
            ".wav",
            ".m4a",
            ".mp4",
            ".mpeg",
            ".mpga",
            ".webm",
            ".ogg",
        }

        if not WHISPER_AVAILABLE:
            logger.error("❌ Whisper not available - voice processing disabled")
        else:
            logger.info("✅ Whisper available - model will load on first use")

    def load_model(self):
        """Load the Whisper model with GPU support if available"""
        if self.model_loading or self.model_loaded:
            return

        self.model_loading = True
        try:
            model_size = "medium"  # Balance between accuracy and speed
            logger.info(f"🔄 Loading Whisper {model_size} model on {self.device}...")

            # Load model with device specification
            self.model = whisper.load_model(model_size, device=self.device)
            self.model_loaded = True

            logger.info(f"✅ Whisper {model_size} model loaded successfully")
            logger.info(f"🎯 Using device: {self.device}")
            logger.info("📝 Model supports: transcription and translation")
            logger.info("🌍 Languages: Supports 99 languages")

            if CUDA_AVAILABLE:
                logger.info("🚀 GPU acceleration enabled for voice processing")
            else:
                logger.info("💻 Using CPU for voice processing")

        except Exception as e:
            logger.error(f"❌ Failed to load Whisper model: {e}")
            self.model_loaded = False
        finally:
            self.model_loading = False

    def is_supported_format(self, filename):
        """Check if the audio file format is supported"""
        return Path(filename).suffix.lower() in self.supported_formats

    def transcribe_audio(self, audio_file_path, language=None):
        """
        Transcribe audio file to text with GPU acceleration if available

        Args:
            audio_file_path (str): Path to the audio file
            language (str, optional): Language code (e.g., 'en', 'es', 'fr')

        Returns:
            dict: Transcription result with text and metadata
        """
        # Lazy load the model on first use
        if not self.model_loaded and not self.model_loading:
            logger.info("🔄 Loading Whisper model on first use...")
            self.load_model()

        if not self.model_loaded:
            return {"success": False, "error": "Whisper model failed to load"}

        if not os.path.exists(audio_file_path):
            return {"success": False, "error": "Audio file not found"}

        if not self.is_supported_format(audio_file_path):
            return {"success": False, "error": "Unsupported audio format"}

        try:
            logger.info(f"🎤 Starting transcription: {Path(audio_file_path).name}")
            logger.info(f"🎯 Using device: {self.device}")
            start_time = time.time()

            # Transcribe the audio with device specification
            options = {}
            if language:
                options["language"] = language

            # Ensure model is on correct device
            if CUDA_AVAILABLE and hasattr(self.model, "to"):
                self.model.to(self.device)

            result = self.model.transcribe(audio_file_path, **options)

            processing_time = time.time() - start_time
            text = result["text"].strip()

            logger.info(f"✅ Transcription completed in {processing_time:.2f} seconds")
            logger.info(f"🎯 Processed on: {self.device}")
            logger.info(
                f"📝 Transcribed text: '{text[:100]}{'...' if len(text) > 100 else ''}'"
            )
            logger.info(f"🌍 Detected language: {result.get('language', 'unknown')}")

            return {
                "success": True,
                "text": text,
                "language": result.get("language"),
                "processing_time": processing_time,
                "duration": result.get("duration", 0),
                "device": self.device,
            }

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            return {"success": False, "error": str(e)}

    def get_model_info(self):
        """Get information about the loaded model"""
        if self.model_loading:
            return {"status": "Loading Whisper model...", "device": self.device}
        elif not self.model_loaded:
            return {"status": "Model will load on first use", "device": self.device}

        return {
            "model": "medium",
            "size": "~769MB",
            "accuracy": "Better accuracy for most languages",
            "speed": "Moderate processing speed",
            "languages": "99 languages supported",
            "device": self.device,
            "cuda_available": CUDA_AVAILABLE,
        }


class ButtonConfig:
    """Load and manage button configuration from JSON file"""

    def __init__(self, config_file: str = "button_config.json"):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self.current_os = self._get_os_key()
        self.load_config()

    def _get_os_key(self) -> str:
        """Get the OS key for configuration lookup"""
        os_name = platform.system().lower()
        if os_name == "darwin":
            return "macos"
        elif os_name == "windows":
            return "windows"
        else:
            return "linux"

    def load_config(self):
        """Load button configuration from JSON file"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            logger.info(f"✅ Loaded button configuration from {self.config_file}")
        except FileNotFoundError:
            logger.error(f"❌ Configuration file {self.config_file} not found")
            self.config = {"buttons": []}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {self.config_file}: {e}")
            self.config = {"buttons": []}

    def get_all_buttons(self) -> List[Dict[str, Any]]:
        """Get all buttons from the configuration"""
        return self.config.get("buttons", [])

    def get_button_label(self, button: Dict[str, Any]) -> str:
        """Get button label (now always a string)"""
        return button.get("label", "Unknown")

    def get_key_sequence(
        self, button: Dict[str, Any]
    ) -> Optional[List[Dict[str, str]]]:
        """Get OS-appropriate key sequence for a button"""
        key_sequence = button.get("key_sequence")
        if not key_sequence:
            return None

        # Return the sequence for the current OS
        return key_sequence.get(self.current_os, key_sequence.get("linux"))

    def get_button_classes(self, button: Dict[str, Any]) -> str:
        """Get CSS classes for a button with default square styling"""
        default_classes = "w-24 h-24 bg-blue-500"
        config_classes = button.get("classes", "")

        if config_classes:
            return f"{default_classes} {config_classes}"
        return default_classes


class KeySimulator:
    """Sequence-based key simulation handler with hook system"""

    def __init__(self):
        self.current_os = platform.system()
        self.hooks = {}  # Dictionary to store hooks for button IDs

    def register_hook(self, button_id: str, hook_function):
        """Register a hook function to be called before key simulation"""
        if button_id not in self.hooks:
            self.hooks[button_id] = []
        self.hooks[button_id].append(hook_function)
        logger.info(f"🔗 Registered hook for button: {button_id}")

    def execute_hooks(self, button_id: str) -> bool:
        """Execute all registered hooks for a button"""
        if button_id in self.hooks:
            for hook_func in self.hooks[button_id]:
                try:
                    result = hook_func()
                    if (
                        result is False
                    ):  # Hook can return False to prevent key simulation
                        return False
                except Exception as e:
                    logger.error(f"❌ Hook execution failed for {button_id}: {e}")
                    return False
        return True

    def simulate_key_sequence(self, key_sequence: List[Dict[str, str]]) -> bool:
        """
        Simulate a sequence of key actions

        Args:
            key_sequence: List of key actions [{"key": "ctrl", "action": "down"}, ...]

        Returns:
            bool: True if simulation was successful, False otherwise
        """
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available")
            return False

        try:
            for key_action in key_sequence:
                key = key_action.get("key")
                action = key_action.get("action")

                if not key or not action:
                    logger.error("❌ Invalid key action in sequence")
                    return False

                success = self._simulate_key_action(key, action)
                if not success:
                    return False

                # Small delay between key actions for reliability
                time.sleep(0.01)

            return True

        except Exception as e:
            logger.error(f"❌ Key sequence simulation failed: {e}")
            return False

    def _simulate_key_action(self, key: str, action: str) -> bool:
        """
        Simulate a single key action (down, up, or press)

        Args:
            key: The key to simulate
            action: The action to perform ('down', 'up', or 'press')

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if action == "press":
                return self._press_key(key)
            elif action == "down":
                return self._key_down(key)
            elif action == "up":
                return self._key_up(key)
            else:
                logger.error(f"❌ Invalid key action: {action}")
                return False
        except Exception as e:
            logger.error(f"❌ Key action simulation failed: {e}")
            return False

    def _key_down(self, key: str) -> bool:
        """Press a key down (and hold)"""
        try:
            if self.current_os == "Windows" and WINDOWS_FALLBACK:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 0, 0)  # Key down
                    return True

            if PYNPUT_AVAILABLE:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.press(pynput_key)
                return True

            return False
        except Exception as e:
            logger.error(f"❌ Key down failed: {e}")
            return False

    def _key_up(self, key: str) -> bool:
        """Release a key"""
        try:
            if self.current_os == "Windows" and WINDOWS_FALLBACK:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 2, 0)  # Key up
                    return True

            if PYNPUT_AVAILABLE:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.release(pynput_key)
                return True

            return False
        except Exception as e:
            logger.error(f"❌ Key up failed: {e}")
            return False

    def _get_windows_vk_code(self, key: str) -> Optional[int]:
        """Get Windows virtual key code for a key"""
        vk_codes = {
            "ctrl": 0x11,
            "shift": 0x10,
            "alt": 0x12,
            "cmd": 0x5B,  # Left Windows key
            "enter": 0x0D,
            "backspace": 0x08,
            "space": 0x20,
            "tab": 0x09,
            "a": 0x41,
            "b": 0x42,
            "c": 0x43,
            "d": 0x44,
            "e": 0x45,
            "f": 0x46,
            "g": 0x47,
            "h": 0x48,
            "i": 0x49,
            "j": 0x4A,
            "k": 0x4B,
            "l": 0x4C,
            "m": 0x4D,
            "n": 0x4E,
            "o": 0x4F,
            "p": 0x50,
            "q": 0x51,
            "r": 0x52,
            "s": 0x53,
            "t": 0x54,
            "u": 0x55,
            "v": 0x56,
            "w": 0x57,
            "x": 0x58,
            "y": 0x59,
            "z": 0x5A,
        }
        return vk_codes.get(key.lower())

    def _get_pynput_key(self, key_name: str):
        """Convert key name to pynput key object"""
        if key_name == "enter":
            return Key.enter
        elif key_name == "backspace":
            return Key.backspace
        elif key_name == "space":
            return Key.space
        elif key_name == "tab":
            return Key.tab
        else:
            # For letter keys, return as string
            return key_name

    def _press_key(self, key_name: str) -> bool:
        """Press a single key"""
        try:
            if self.current_os == "Windows" and WINDOWS_FALLBACK:
                # Use Windows native API for simple keys
                if key_name == "enter":
                    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
                    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up
                    return True

            if PYNPUT_AVAILABLE:
                pynput_key = self._get_pynput_key(key_name)
                keyboard_controller.press(pynput_key)
                keyboard_controller.release(pynput_key)
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Single key press failed: {e}")
            return False


class ButtonFactory:
    """Factory class to create and manage UI buttons from configuration"""

    def __init__(self, text_app_instance):
        self.app = text_app_instance
        self.config = ButtonConfig()
        self.key_simulator = KeySimulator()
        self._register_hooks()

    def _register_hooks(self):
        """Register hook functions for buttons that need them"""
        # Register copy hook
        self.key_simulator.register_hook("copy", self.app.copy_current_text)

        # Register clear hook
        self.key_simulator.register_hook("clear", self.app.clear_text)

        # Register copy_paste hook
        self.key_simulator.register_hook("copy_paste", self.app.copy_current_text)

        # Register copy_paste_enter hook
        self.key_simulator.register_hook("copy_paste_enter", self.app.copy_current_text)

    def create_button(self, button_config: Dict[str, Any]):
        """Create a UI button from configuration"""
        button_id = button_config.get("id")
        label = self.config.get_button_label(button_config)

        # Get classes from configuration, with fallback to default
        tailwind_classes = self.config.get_button_classes(button_config)

        # Create button with appropriate callback
        callback = self._get_button_callback(button_config)
        button = ui.button(label, on_click=callback, color=None).classes(
            tailwind_classes
        )

        logger.info(f"✅ Created button: {button_id} - {label}")
        return button

    def _get_button_callback(self, button_config: Dict[str, Any]):
        """Get the appropriate callback function for a button"""
        action = button_config.get("action")
        button_id = button_config.get("id")

        if action == "copy_text":
            return self.app.copy_current_text
        elif action == "clear_text":
            return self.app.clear_text
        elif action == "copy_and_paste":
            return lambda: self._handle_copy_and_paste(button_config)
        elif action == "copy_paste_and_enter":
            return lambda: self._handle_copy_paste_and_enter(button_config)
        elif action == "simulate_key_sequence":
            return lambda: self._handle_key_sequence(button_config)
        else:
            logger.warning(f"⚠️ Unknown action for button {button_id}: {action}")
            return lambda: self.app.show_status(
                f"Action not implemented: {action}", "error"
            )

    def _handle_key_sequence(self, button_config: Dict[str, Any]):
        """Handle key sequence simulation for a button"""
        button_id = button_config.get("id")
        key_sequence = self.config.get_key_sequence(button_config)

        if not key_sequence:
            logger.error(f"❌ No key sequence for button {button_id}")
            self.app.show_status(f"No key sequence for {button_id}", "error")
            return

        logger.info(f"🎹 Simulating key sequence for {button_id}")

        # Execute hooks before key simulation
        if not self.key_simulator.execute_hooks(button_id):
            logger.info(f"🔗 Hook prevented key simulation for {button_id}")
            return

        if self.key_simulator.simulate_key_sequence(key_sequence):
            self.app.show_status(f"{button_id} executed!", "success")
        else:
            self.app.show_status(f"Failed to execute {button_id}", "error")

    def _handle_copy_and_paste(self, button_config: Dict[str, Any]):
        """Handle copy and paste action"""
        button_id = button_config.get("id")

        # Execute hook (copy text)
        if not self.key_simulator.execute_hooks(button_id):
            return

        # Simulate paste key sequence
        key_sequence = self.config.get_key_sequence(button_config)
        if key_sequence and self.key_simulator.simulate_key_sequence(key_sequence):
            self.app.show_status("Text copied and pasted!", "success")
        else:
            self.app.show_status("Failed to copy and paste", "error")

    def _handle_copy_paste_and_enter(self, button_config: Dict[str, Any]):
        """Handle copy, paste and enter action"""
        button_id = button_config.get("id")

        # Execute hook (copy text)
        if not self.key_simulator.execute_hooks(button_id):
            return

        # Simulate paste and enter key sequence
        key_sequence = self.config.get_key_sequence(button_config)
        if key_sequence and self.key_simulator.simulate_key_sequence(key_sequence):
            self.app.show_status("Text copied, pasted and entered!", "success")
        else:
            self.app.show_status("Failed to copy, paste and enter", "error")

    def get_all_buttons(self) -> List:
        """Get all UI buttons from configuration"""
        buttons = []
        button_configs = self.config.get_all_buttons()

        for button_config in button_configs:
            buttons.append(self.create_button(button_config))

        return buttons


class TextInputApp:
    def __init__(self):
        self.max_history = 10
        self.storage_key = "shared_text"
        self.history_key = "shared_history"

        # Initialize voice processor
        self.voice_processor = VoiceProcessor() if WHISPER_AVAILABLE else None
        self.voice_enabled = WHISPER_AVAILABLE

        # Initialize application instance manager (for Cursor)
        self.instance_manager = create_application_instance_manager("Cursor")

        # Initialize button factory for configuration-driven UI
        self.button_factory = ButtonFactory(self)

        # Initialize voice recording state
        self.is_recording = False

        # Load history from storage once on startup
        self.text_history = app.storage.general.get(self.history_key, [])

        logger.info("📱 TextInputApp initialized")
        if self.voice_enabled:
            logger.info("🎤 Voice-to-text functionality enabled")
        else:
            logger.warning("⚠️ Voice-to-text functionality disabled")

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        try:
            pyperclip.copy(text)
            logger.info(
                f"📋 Text copied to clipboard: '{text[:50]}{'...' if len(text) > 50 else ''}'"
            )
            return True
        except Exception as e:
            logger.error(f"❌ Failed to copy to clipboard: {e}")
            return False

    def simulate_paste(self):
        """Simulate paste key combination (Cmd+V on macOS, Ctrl+V on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate paste")
            self.show_status("Keyboard simulation not available", "error")
            return False

        try:
            if IS_MACOS:
                # macOS: Use Cmd+V
                logger.info("🍎 Simulating Cmd+V paste on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press("v")
                        keyboard_controller.release("v")
                    logger.info("✅ Cmd+V paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for macOS paste simulation")
                    return False

            elif CURRENT_OS == "Windows":
                # Windows: Try native method first (more reliable)
                logger.info("🪟 Simulating Ctrl+V paste on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native keyboard simulation")
                    # Windows VK codes: Ctrl = 0x11, V = 0x56
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x56, 0, 0, 0)  # V down
                    user32.keybd_event(0x56, 0, 2, 0)  # V up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info(
                        "✅ Windows native Ctrl+V paste operation completed successfully"
                    )
                    return True

                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows paste simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press("v")
                        keyboard_controller.release("v")
                    logger.info(
                        "✅ pynput Ctrl+V paste operation completed successfully"
                    )
                    return True

            else:
                # Linux and other systems: Use Ctrl+V
                logger.info(f"🐧 Simulating Ctrl+V paste on {CURRENT_OS}")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press("v")
                        keyboard_controller.release("v")
                    logger.info("✅ Ctrl+V paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for paste simulation")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to simulate paste: {e}")
            return False

    def add_to_history(self, text):
        """Add text to history with timestamp"""
        if text.strip():
            # Check if this text is different from the most recent history entry
            if not self.text_history or text != self.text_history[0]["text"]:
                timestamp = datetime.now().strftime("%H:%M:%S")
                logger.info(
                    f"📝 Adding text to history: '{text[:30]}{'...' if len(text) > 30 else ''}' at {timestamp}"
                )
                self.text_history.insert(0, {"text": text, "timestamp": timestamp})
                # Keep only recent entries
                if len(self.text_history) > self.max_history:
                    self.text_history = self.text_history[: self.max_history]

                # Save updated history to storage
                app.storage.general[self.history_key] = self.text_history
            else:
                logger.debug("📝 Text already exists in history, skipping duplicate")

    def create_ui(self):
        """Create the main UI"""
        # Set page title and meta tags for mobile
        ui.page_title("Mobile Text Input")

        # Add mobile-friendly viewport meta tag
        ui.add_head_html(
            """
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <meta name="apple-mobile-web-app-capable" content="yes">
            <meta name="apple-mobile-web-app-status-bar-style" content="default">
            """
        )

        # Instance Management Tabs (macOS and Windows)
        if self.instance_manager.is_available():
            # Get application instances
            app_instances = self.instance_manager.list_instances()
            logger.info(f"🔍 DEBUG: Found {len(app_instances)} application instances")
            for i, instance in enumerate(app_instances):
                logger.info(f"🔍 DEBUG: Instance {i}: {instance}")

            # Create tabs for instances if any exist
            if app_instances:
                logger.info(
                    f"🔍 DEBUG: Creating tabs for {len(app_instances)} instances"
                )
                with ui.tabs().classes("w-full") as tabs:
                    self.instance_tabs = {}
                    for instance in app_instances:
                        workspace = instance.get("workspace", "Unknown")
                        logger.info(
                            f"🔍 DEBUG: Creating tab for workspace: {workspace}"
                        )
                        tab = ui.tab(workspace)
                        self.instance_tabs[workspace] = {
                            "tab": tab,
                            "instance": instance,
                        }

                logger.info(
                    f"🔍 DEBUG: Instance tabs created: {list(self.instance_tabs.keys())}"
                )

                # Handle tab selection with proper event binding
                def on_tab_change(e):
                    logger.info(f"🔍 DEBUG: Tab change event triggered")
                    logger.info(f"🔍 DEBUG: Event object: {e}")
                    logger.info(f"🔍 DEBUG: Event type: {type(e)}")
                    logger.info(f"🔍 DEBUG: Event dir: {dir(e)}")

                    # Try multiple ways to get the selected value
                    selected_workspace = None
                    if hasattr(e, "args"):
                        selected_workspace = e.args
                        logger.info(f"🔍 DEBUG: Found args: {selected_workspace}")
                    if hasattr(e, "value"):
                        selected_workspace = e.value
                        logger.info(f"🔍 DEBUG: Found value: {selected_workspace}")
                    if hasattr(e, "sender"):
                        logger.info(f"🔍 DEBUG: Event sender: {e.sender}")
                        if hasattr(e.sender, "value"):
                            selected_workspace = e.sender.value
                            logger.info(
                                f"🔍 DEBUG: Found sender value: {selected_workspace}"
                            )

                    logger.info(f"🎯 Tab clicked: {selected_workspace}")
                    logger.info(
                        f"🔍 DEBUG: Available tabs: {list(self.instance_tabs.keys())}"
                    )

                    if selected_workspace and selected_workspace in self.instance_tabs:
                        instance = self.instance_tabs[selected_workspace]["instance"]
                        instance_id = instance.get("id")
                        logger.info(f"🎯 Activating instance: {instance_id}")

                        # Use the application instance manager to focus the instance
                        self.instance_manager.focus_instance(instance_id)

                    else:
                        logger.warning(f"⚠️ Workspace not found: {selected_workspace}")

                # Try multiple event binding approaches
                tabs.on("update:model-value", on_tab_change)

                # Also try click events
                tabs.on(
                    "click", lambda e: logger.info(f"🔍 DEBUG: Tab click event: {e}")
                )

            else:
                logger.info("No application instances found - tabs not created")
        else:
            logger.info("Instance manager not available - tabs not created")

        # Main content container
        with ui.column().classes("w-full max-w-2xl mx-auto"):
            # Text input area with direct storage binding
            self.text_area = (
                ui.textarea(placeholder="Type your text here...")
                .props("clearable")
                .bind_value(app.storage.general, self.storage_key)
                .classes("w-full")
            )

            # Voice input section (separate from other buttons)
            if self.voice_enabled:
                with ui.row().classes("w-full"):
                    self.voice_button = ui.button(
                        "Start Recording", on_click=self.toggle_voice_recording
                    ).classes("flex-1 p-2 m-1 bg-primary")

            # All buttons from configuration (unified system)
            with ui.row().classes("w-full"):
                all_buttons = self.button_factory.get_all_buttons()
                for button in all_buttons:
                    # Buttons are already created by the factory
                    pass

            # Status section - group all status info together
            with ui.column().classes("w-full p-2 my-2"):
                ui.label("System Status").classes("mb-2")
                with ui.column():
                    # Voice status
                    if self.voice_enabled:
                        voice_info = self.voice_processor.get_model_info()
                        if "status" in voice_info:
                            ui.label(
                                f"🎤 Voice: {voice_info['status']} • Button turns red when recording"
                            )
                        else:
                            ui.label(
                                f"🎤 Voice: Whisper {voice_info['model']} ready • Button turns red when recording"
                            )
                    else:
                        ui.label("❌ Voice-to-text not available")
                        if not WHISPER_AVAILABLE:
                            ui.label("📦 Install: pip install openai-whisper")

                    # Keyboard simulation status
                    if WINDOWS_FALLBACK:
                        ui.label("✅ Windows native keyboard simulation")
                    elif PYNPUT_AVAILABLE:
                        ui.label("✅ pynput keyboard simulation")
                    else:
                        ui.label("⚠️ Keyboard simulation not available")
                        if not KEYBOARD_AVAILABLE:
                            ui.label("📦 Install pynput: pip install pynput")

                    # Storage synchronization status
                    ui.label("✅ Cross-device synchronization enabled")
                    ui.label("📱 Text syncs across all devices and browser tabs")

            # Add JavaScript for voice functionality if enabled
            if self.voice_enabled:
                ui.add_head_html(
                    """
                    <script>
                    let mediaRecorder;
                    let audioChunks = [];
                    let isRecording = false;
                    let microphonePermissionGranted = false;
                    let audioStream = null;
                                        
                    // Function to show status messages
                    function showStatus(message, type = 'info') {
                        // Create a temporary notification element
                        const notification = document.createElement('div');
                        notification.textContent = message;
                        notification.style.cssText = `
                            position: fixed;
                            bottom: 20px;
                            right: 20px;
                            background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
                            color: white;
                            padding: 12px 20px;
                            border-radius: 4px;
                            z-index: 9999;
                            font-size: 14px;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                        `;
                        document.body.appendChild(notification);
                        
                        // Remove after 3 seconds
                        setTimeout(() => {
                            if (notification.parentNode) {
                                notification.parentNode.removeChild(notification);
                            }
                        }, 3000);
                    }
                    
                    async function startRecording() {
                        if (isRecording) return;
                        
                        try {
                            // Request microphone permission and start recording
                            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                            microphonePermissionGranted = true;
                            
                            mediaRecorder = new MediaRecorder(audioStream);
                            audioChunks = [];
                            
                            mediaRecorder.ondataavailable = event => {
                                audioChunks.push(event.data);
                            };
                            
                            mediaRecorder.onstop = async () => {
                                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                                const audioData = await audioBlob.arrayBuffer();
                                
                                // Show processing status
                                showStatus('Processing recorded audio...', 'info');
                                
                                // Send audio data to backend
                                fetch('/process-audio', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/octet-stream',
                                    },
                                    body: audioData
                                })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        showStatus('Audio processed successfully', 'success');
                                    } else {
                                        showStatus(`Transcription failed: ${data.error}`, 'error');
                                    }
                                })
                                .catch(error => {
                                    console.error('Error processing audio:', error);
                                    showStatus('Error processing audio', 'error');
                                });
                                
                                // Stop all tracks
                                if (audioStream) {
                                    audioStream.getTracks().forEach(track => track.stop());
                                    audioStream = null;
                                }
                                isRecording = false;
                            };
                            
                            mediaRecorder.start();
                            isRecording = true;
                            
                        } catch (error) {
                            console.error('Error accessing microphone:', error);
                            microphonePermissionGranted = false;
                            
                            if (error.name === 'NotAllowedError') {
                                showStatus('Microphone access denied. Please allow microphone access and try again.', 'error');
                            } else if (error.name === 'NotFoundError') {
                                showStatus('No microphone found. Please connect a microphone and try again.', 'error');
                            } else {
                                showStatus('Error accessing microphone. Please check your browser settings.', 'error');
                            }
                        }
                    }
                    
                    function stopRecording() {
                        if (mediaRecorder && isRecording) {
                            mediaRecorder.stop();
                        }
                    };
                    
                    </script>
                """
                )

            # History section
            ui.separator()
            ui.label("Recent Text History:").classes("text-h6")
            self.history_container = ui.column().classes("w-full")

        # Footer
        with ui.column().classes("w-full p-2 mt-4"):
            ui.label(
                "Tap text area to start typing • Text syncs across all devices and tabs"
            )
            ui.label(
                "Use the buttons above to copy, paste, and send keyboard shortcuts to server"
            )

        # Text area is bound directly to storage, so changes are automatic
        # Update history display on startup
        self.update_history_display()

    def copy_current_text(self):
        """Copy current text to clipboard with user feedback"""
        # Get text from storage
        current_text = app.storage.general.get(self.storage_key, "")
        text = current_text.strip() if current_text else ""

        if not text:
            logger.warning("⚠️ Copy operation attempted with no text")
            self.show_status("No text to copy", "error")
            return

        logger.info(
            f"📋 Starting copy operation: '{text[:50]}{'...' if len(text) > 50 else ''}'"
        )

        if self.copy_to_clipboard(text):
            self.add_to_history(text)
            self.update_history_display()

            # Clear text area after successful copy
            logger.info("🗑️ Clearing text area after successful copy")
            app.storage.general[self.storage_key] = ""

            logger.info("✅ Copy operation completed successfully")
            self.show_status("Text copied to clipboard!", "success")
        else:
            logger.error("❌ Copy operation failed")
            self.show_status("Failed to copy text", "error")

    def paste_from_history(self, text):
        """Paste text from history by copying to clipboard then simulating paste"""
        if self.copy_to_clipboard(text):
            # Small delay to ensure clipboard is updated
            time.sleep(0.1)

            # Then simulate paste
            if self.simulate_paste():
                self.add_to_history(text)
                self.update_history_display()
                self.show_status("Text pasted from history!", "success")
            else:
                self.show_status("Failed to paste text", "error")
        else:
            self.show_status("Failed to copy text to clipboard", "error")

    def clear_text(self):
        """Clear the text area"""
        app.storage.general[self.storage_key] = ""

        logger.info("✅ Text cleared successfully")
        self.show_status("Text cleared", "success")

    def show_status(self, message, status_type="success"):
        """Show status notification to user"""
        if status_type == "success":
            ui.notify(message, type="positive", position="top")
            logger.info(f"✅ Status notification (success): {message}")
        elif status_type == "error":
            ui.notify(message, type="negative", position="top")
            logger.error(f"❌ Status notification (error): {message}")
        else:
            ui.notify(message, type="info", position="top")
            logger.info(f"ℹ️ Status notification (info): {message}")

    def copy_from_history(self, text):
        """Copy text from history"""
        if self.copy_to_clipboard(text):
            self.show_status("Text copied from history!", "success")
        else:
            self.show_status("Failed to copy text", "error")

    def update_history_display(self):
        """Update the history display"""
        self.history_container.clear()

        if not self.text_history:
            with self.history_container:
                ui.label("No recent text entries")
            return

        with self.history_container:
            for i, entry in enumerate(self.text_history):
                with ui.card().classes("w-full p-2 my-1"):
                    with ui.row().classes("w-full justify-between items-center"):
                        with ui.column().classes("flex-grow"):
                            # Show preview of text (first 50 chars)
                            preview = entry["text"][:50]
                            if len(entry["text"]) > 50:
                                preview += "..."
                            ui.label(preview)
                            ui.label(f"Added: {entry['timestamp']}")

                        with ui.row():
                            ui.button(
                                "Copy",
                                on_click=lambda e, text=entry[
                                    "text"
                                ]: self.copy_from_history(text),
                            ).classes("p-1 m-1 bg-positive")

                            ui.button(
                                "Paste",
                                on_click=lambda e, text=entry[
                                    "text"
                                ]: self.paste_from_history(text),
                            ).classes("p-1 m-1 bg-positive")

    async def process_audio_data(self, audio_data):
        """Process raw audio data without UI updates (for API calls)"""
        if not self.voice_enabled:
            return {"success": False, "error": "Voice-to-text is not available"}

        try:
            logger.info("🎤 Processing push-to-talk audio recording")

            # Save audio data temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name

            # Transcribe the audio
            result = await asyncio.to_thread(
                self.voice_processor.transcribe_audio, temp_file_path
            )

            # Clean up temp file
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

            if result["success"]:
                transcribed_text = result["text"]
                processing_time = result.get("processing_time", 0)
                language = result.get("language", "unknown")

                if transcribed_text:
                    # Directly update storage
                    current_text = app.storage.general.get(self.storage_key, "")
                    if current_text:
                        app.storage.general[self.storage_key] = (
                            current_text + "\n" + transcribed_text
                        )
                    else:
                        app.storage.general[self.storage_key] = transcribed_text

                    # Add to history
                    self.add_to_history(transcribed_text)

                    logger.info(
                        f"✅ Push-to-talk transcription successful: {len(transcribed_text)} characters"
                    )
                    return {
                        "success": True,
                        "text": transcribed_text,
                        "processing_time": processing_time,
                        "language": language,
                    }
                else:
                    logger.warning("⚠️ No speech detected in push-to-talk recording")
                    return {
                        "success": False,
                        "error": "No speech detected in recording",
                    }
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"❌ Push-to-talk transcription failed: {error_msg}")
                return {"success": False, "error": error_msg}

        except Exception as e:
            logger.error(f"❌ Push-to-talk audio processing error: {e}")
            return {"success": False, "error": str(e)}

    def toggle_voice_recording(self):
        """Toggle voice recording state and trigger JavaScript recording"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return

        if not self.is_recording:
            # Start recording
            logger.info("🎤 Starting voice recording from Python")
            self.is_recording = True

            # Update button appearance for recording state
            self.voice_button.set_text("🔴 Recording... (Click to Stop)")
            self.voice_button.classes(replace="flex-1 p-2 m-1 bg-negative")

            # Trigger JavaScript recording
            ui.run_javascript(
                "if (typeof startRecording === 'function') startRecording();"
            )

        else:
            # Stop recording
            logger.info("🛑 Stopping voice recording from Python")
            self.is_recording = False

            # Reset button appearance to normal state
            self.voice_button.set_text("🎤 Start Recording")
            self.voice_button.classes(replace="flex-1 p-2 m-1 bg-primary")

            # Trigger JavaScript stop
            ui.run_javascript(
                "if (typeof stopRecording === 'function') stopRecording();"
            )


def main():
    """Main function to run the application"""
    # Create the app instance
    text_app = TextInputApp()

    # Add API endpoint for processing recorded audio
    @app.post("/process-audio")
    async def process_audio(request: Request):
        """Handle recorded audio data from push-to-talk"""
        try:
            # Read the raw audio data
            audio_data = await request.body()

            if not audio_data:
                return {"success": False, "error": "No audio data received"}

            # Process the audio using the non-UI method
            result = await text_app.process_audio_data(audio_data)
            return result

        except Exception as e:
            logger.error(f"❌ API audio processing error: {e}")
            return {"success": False, "error": str(e)}

    # Create the UI
    text_app.create_ui()

    # Run the application
    ui.run(
        host="0.0.0.0",  # Accept connections from any IP
        port=8080,
        title="Mobile Text Input",
        reload=True,
        dark=True,
        show=False,  # Don't auto-open browser
        storage_secret="mobile-text-input-secret-key-2024",  # Enable cross-device storage
    )


if __name__ == "__main__" or __name__ == "__mp_main__":
    main()
