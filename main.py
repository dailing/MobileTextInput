#!/usr/bin/env python3
"""
Mobile Text Input Web Application
A web application that allows text input from mobile devices with automatic clipboard copying and keyboard simulation
"""

import socket
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
import subprocess
import json
from typing import Dict, List, Optional, Any

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
        from ctypes import wintypes

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
            self.config = {"buttons": [], "button_groups": {}}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {self.config_file}: {e}")
            self.config = {"buttons": [], "button_groups": {}}

    def get_buttons_by_group(self, group: str) -> List[Dict[str, Any]]:
        """Get all buttons for a specific group"""
        return [
            btn for btn in self.config.get("buttons", []) if btn.get("group") == group
        ]

    def get_button_label(self, button: Dict[str, Any]) -> str:
        """Get OS-appropriate label for a button"""
        label = button.get("label", "")
        if isinstance(label, dict):
            return label.get(self.current_os, label.get("linux", "Unknown"))
        return label

    def get_key_combination(self, button: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get OS-appropriate key combination for a button"""
        key_combo = button.get("key_combination")
        if not key_combo:
            return None

        # Handle simple key combinations (like enter only)
        if "keys" in key_combo:
            return {"keys": key_combo["keys"]}

        # Handle OS-specific combinations
        return key_combo.get(self.current_os, key_combo.get("linux"))


class KeySimulator:
    """Generic key simulation handler that works across all operating systems"""

    def __init__(self):
        self.current_os = platform.system()

    def simulate_key_combination(self, key_config: Dict[str, Any]) -> bool:
        """
        Simulate a key combination based on configuration

        Args:
            key_config: Dictionary containing key combination details

        Returns:
            bool: True if simulation was successful, False otherwise
        """
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available")
            return False

        try:
            # Handle simple single key presses
            if "keys" in key_config:
                return self._simulate_simple_keys(key_config["keys"])

            # Handle modifier + key combinations
            modifiers = key_config.get("modifiers", [])
            key = key_config.get("key")
            vk_codes = key_config.get("vk_codes", {})

            if not key:
                logger.error("❌ No key specified in key configuration")
                return False

            return self._simulate_modifier_combination(modifiers, key, vk_codes)

        except Exception as e:
            logger.error(f"❌ Key simulation failed: {e}")
            return False

    def _simulate_simple_keys(self, keys: List[str]) -> bool:
        """Simulate simple key presses without modifiers"""
        for key_name in keys:
            if not self._press_key(key_name):
                return False
        return True

    def _simulate_modifier_combination(
        self, modifiers: List[str], key: str, vk_codes: Dict[str, str]
    ) -> bool:
        """Simulate key combination with modifiers"""
        if self.current_os == "Windows" and WINDOWS_FALLBACK and vk_codes:
            return self._simulate_windows_native(modifiers, key, vk_codes)
        elif PYNPUT_AVAILABLE:
            return self._simulate_pynput(modifiers, key)
        else:
            logger.error("❌ No available key simulation method")
            return False

    def _simulate_windows_native(
        self, modifiers: List[str], key: str, vk_codes: Dict[str, str]
    ) -> bool:
        """Use Windows native API for key simulation"""
        try:
            # Press modifiers down
            for modifier in modifiers:
                vk_code = vk_codes.get(modifier)
                if vk_code:
                    user32.keybd_event(int(vk_code, 16), 0, 0, 0)

            # Press main key
            key_vk = vk_codes.get(key)
            if key_vk:
                user32.keybd_event(int(key_vk, 16), 0, 0, 0)  # Key down
                user32.keybd_event(int(key_vk, 16), 0, 2, 0)  # Key up

            # Release modifiers
            for modifier in reversed(modifiers):
                vk_code = vk_codes.get(modifier)
                if vk_code:
                    user32.keybd_event(int(vk_code, 16), 0, 2, 0)

            logger.info(
                f"✅ Windows native key simulation: {'+'.join(modifiers + [key])}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Windows native simulation failed: {e}")
            return False

    def _simulate_pynput(self, modifiers: List[str], key: str) -> bool:
        """Use pynput for key simulation"""
        try:
            # Convert key name to pynput key
            pynput_key = self._get_pynput_key(key)

            # Handle combinations with modifiers
            if modifiers:
                # Create nested context managers for modifiers
                if "cmd" in modifiers and "shift" in modifiers:
                    with keyboard_controller.pressed(Key.cmd):
                        with keyboard_controller.pressed(Key.shift):
                            keyboard_controller.press(pynput_key)
                            keyboard_controller.release(pynput_key)
                elif "ctrl" in modifiers and "shift" in modifiers:
                    with keyboard_controller.pressed(Key.ctrl):
                        with keyboard_controller.pressed(Key.shift):
                            keyboard_controller.press(pynput_key)
                            keyboard_controller.release(pynput_key)
                elif "cmd" in modifiers:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press(pynput_key)
                        keyboard_controller.release(pynput_key)
                elif "ctrl" in modifiers:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press(pynput_key)
                        keyboard_controller.release(pynput_key)
                elif "shift" in modifiers:
                    with keyboard_controller.pressed(Key.shift):
                        keyboard_controller.press(pynput_key)
                        keyboard_controller.release(pynput_key)
            else:
                # No modifiers, just press the key
                keyboard_controller.press(pynput_key)
                keyboard_controller.release(pynput_key)

            logger.info(f"✅ pynput key simulation: {'+'.join(modifiers + [key])}")
            return True

        except Exception as e:
            logger.error(f"❌ pynput simulation failed: {e}")
            return False

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

    def create_button(self, button_config: Dict[str, Any]):
        """Create a UI button from configuration"""
        button_id = button_config.get("id")
        label = self.config.get_button_label(button_config)
        style_class = button_config.get("style_class", "")

        # Use simple classes that work well with dark mode
        tailwind_classes = "flex-1 p-2 m-1"

        if "copy-button" in style_class:
            tailwind_classes += " bg-positive"
        elif "clear-button" in style_class:
            tailwind_classes += " bg-negative"
        elif "voice-button" in style_class:
            tailwind_classes += " bg-primary"
        elif "upload-button" in style_class:
            tailwind_classes += " bg-secondary"
        else:
            tailwind_classes += " bg-accent"

        # Create button with appropriate callback
        callback = self._get_button_callback(button_config)
        button = ui.button(label, on_click=callback).classes(tailwind_classes)

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
        elif action == "simulate_key":
            return lambda: self._handle_key_simulation(button_config)
        elif action == "toggle_voice_recording":
            return None  # Voice button has special handling
        else:
            logger.warning(f"⚠️ Unknown action for button {button_id}: {action}")
            return lambda: self.app.show_status(
                f"Action not implemented: {action}", "error"
            )

    def _handle_key_simulation(self, button_config: Dict[str, Any]):
        """Handle key simulation for a button"""
        button_id = button_config.get("id")
        key_config = self.config.get_key_combination(button_config)

        if not key_config:
            logger.error(f"❌ No key configuration for button {button_id}")
            self.app.show_status(f"No key configuration for {button_id}", "error")
            return

        logger.info(f"🎹 Simulating key combination for {button_id}")

        if self.key_simulator.simulate_key_combination(key_config):
            self.app.show_status(
                f"{button_config.get('description', button_id)} executed!", "success"
            )
        else:
            self.app.show_status(f"Failed to execute {button_id}", "error")

    def get_buttons_for_group(self, group: str) -> List:
        """Get all UI buttons for a specific group"""
        buttons = []
        button_configs = self.config.get_buttons_by_group(group)

        for button_config in button_configs:
            if button_config.get("unique_logic"):
                # Skip buttons with unique logic (like voice recording)
                continue
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

        # Initialize instance management
        self.cursor_instances = []

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

    def get_local_ip(self):
        """Get the local IP address of the server"""
        try:
            # Create a socket to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
            logger.info(f"🌐 Local IP address detected: {local_ip}")
            return local_ip
        except Exception as e:
            logger.error(f"❌ Failed to get local IP: {e}")
            return "localhost"

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

    def simulate_accept(self):
        """Simulate Accept key combination (Cmd+Enter on macOS, Ctrl+Enter on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error(
                "❌ Keyboard simulation not available - cannot simulate Accept"
            )
            return False

        try:
            if IS_MACOS:
                # macOS: Use Cmd+Enter
                logger.info("🍎 Simulating Cmd+Enter (Accept) on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press(Key.enter)
                        keyboard_controller.release(Key.enter)
                    logger.info(
                        "✅ Cmd+Enter (Accept) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for macOS Accept simulation")
                    return False

            elif CURRENT_OS == "Windows":
                # Windows: Try native method first
                logger.info("🪟 Simulating Ctrl+Enter (Accept) on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native Accept simulation")
                    # Windows VK codes: Ctrl = 0x11, Enter = 0x0D
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
                    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info(
                        "✅ Windows native Ctrl+Enter (Accept) operation completed successfully"
                    )
                    return True

                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows Accept simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press(Key.enter)
                        keyboard_controller.release(Key.enter)
                    logger.info(
                        "✅ pynput Ctrl+Enter (Accept) operation completed successfully"
                    )
                    return True

            else:
                # Linux and other systems: Use Ctrl+Enter
                logger.info(f"🐧 Simulating Ctrl+Enter (Accept) on {CURRENT_OS}")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press(Key.enter)
                        keyboard_controller.release(Key.enter)
                    logger.info(
                        "✅ Ctrl+Enter (Accept) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for Accept simulation")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to simulate Accept: {e}")
            return False

    def simulate_reject(self):
        """Simulate Reject key combination (Cmd+Backspace on macOS, Ctrl+Backspace on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error(
                "❌ Keyboard simulation not available - cannot simulate Reject"
            )
            return False

        try:
            if IS_MACOS:
                # macOS: Use Cmd+Backspace
                logger.info("🍎 Simulating Cmd+Backspace (Reject) on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press(Key.backspace)
                        keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ Cmd+Backspace (Reject) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for macOS Reject simulation")
                    return False

            elif CURRENT_OS == "Windows":
                # Windows: Try native method first
                logger.info("🪟 Simulating Ctrl+Backspace (Reject) on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native Reject simulation")
                    # Windows VK codes: Ctrl = 0x11, Backspace = 0x08
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x08, 0, 0, 0)  # Backspace down
                    user32.keybd_event(0x08, 0, 2, 0)  # Backspace up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info(
                        "✅ Windows native Ctrl+Backspace (Reject) operation completed successfully"
                    )
                    return True

                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows Reject simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press(Key.backspace)
                        keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ pynput Ctrl+Backspace (Reject) operation completed successfully"
                    )
                    return True

            else:
                # Linux and other systems: Use Ctrl+Backspace
                logger.info(f"🐧 Simulating Ctrl+Backspace (Reject) on {CURRENT_OS}")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press(Key.backspace)
                        keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ Ctrl+Backspace (Reject) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for Reject simulation")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to simulate Reject: {e}")
            return False

    def simulate_new(self):
        """Simulate New key combination (Cmd+N on macOS, Ctrl+N on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate New")
            return False

        try:
            if IS_MACOS:
                # macOS: Use Cmd+N
                logger.info("🍎 Simulating Cmd+N (New) on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        keyboard_controller.press("n")
                        keyboard_controller.release("n")
                    logger.info("✅ Cmd+N (New) operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for macOS New simulation")
                    return False

            elif CURRENT_OS == "Windows":
                # Windows: Try native method first
                logger.info("🪟 Simulating Ctrl+N (New) on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native New simulation")
                    # Windows VK codes: Ctrl = 0x11, N = 0x4E
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x4E, 0, 0, 0)  # N down
                    user32.keybd_event(0x4E, 0, 2, 0)  # N up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info(
                        "✅ Windows native Ctrl+N (New) operation completed successfully"
                    )
                    return True

                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows New simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press("n")
                        keyboard_controller.release("n")
                    logger.info(
                        "✅ pynput Ctrl+N (New) operation completed successfully"
                    )
                    return True

            else:
                # Linux and other systems: Use Ctrl+N
                logger.info(f"🐧 Simulating Ctrl+N (New) on {CURRENT_OS}")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        keyboard_controller.press("n")
                        keyboard_controller.release("n")
                    logger.info("✅ Ctrl+N (New) operation completed successfully")
                    return True
                else:
                    logger.error("❌ pynput not available for New simulation")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to simulate New: {e}")
            return False

    def simulate_stop(self):
        """Simulate Stop key combination (Cmd+Shift+Backspace on macOS, Ctrl+Shift+Backspace on Windows/Linux)"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate Stop")
            return False

        try:
            if IS_MACOS:
                # macOS: Use Cmd+Shift+Backspace
                logger.info("🍎 Simulating Cmd+Shift+Backspace (Stop) on macOS")
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.cmd):
                        with keyboard_controller.pressed(Key.shift):
                            keyboard_controller.press(Key.backspace)
                            keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ Cmd+Shift+Backspace (Stop) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for macOS Stop simulation")
                    return False

            elif CURRENT_OS == "Windows":
                # Windows: Try native method first
                logger.info("🪟 Simulating Ctrl+Shift+Backspace (Stop) on Windows")
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native Stop simulation")
                    # Windows VK codes: Ctrl = 0x11, Shift = 0x10, Backspace = 0x08
                    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                    user32.keybd_event(0x10, 0, 0, 0)  # Shift down
                    user32.keybd_event(0x08, 0, 0, 0)  # Backspace down
                    user32.keybd_event(0x08, 0, 2, 0)  # Backspace up
                    user32.keybd_event(0x10, 0, 2, 0)  # Shift up
                    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                    logger.info(
                        "✅ Windows native Ctrl+Shift+Backspace (Stop) operation completed successfully"
                    )
                    return True

                # Fallback to pynput
                elif PYNPUT_AVAILABLE:
                    logger.info("🔧 Using pynput for Windows Stop simulation")
                    with keyboard_controller.pressed(Key.ctrl):
                        with keyboard_controller.pressed(Key.shift):
                            keyboard_controller.press(Key.backspace)
                            keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ pynput Ctrl+Shift+Backspace (Stop) operation completed successfully"
                    )
                    return True

            else:
                # Linux and other systems: Use Ctrl+Shift+Backspace
                logger.info(
                    f"🐧 Simulating Ctrl+Shift+Backspace (Stop) on {CURRENT_OS}"
                )
                if PYNPUT_AVAILABLE:
                    with keyboard_controller.pressed(Key.ctrl):
                        with keyboard_controller.pressed(Key.shift):
                            keyboard_controller.press(Key.backspace)
                            keyboard_controller.release(Key.backspace)
                    logger.info(
                        "✅ Ctrl+Shift+Backspace (Stop) operation completed successfully"
                    )
                    return True
                else:
                    logger.error("❌ pynput not available for Stop simulation")
                    return False

        except Exception as e:
            logger.error(f"❌ Failed to simulate Stop: {e}")
            return False

    def auto_paste_text(self, text):
        """Auto-paste text by copying to clipboard then simulating paste"""
        if text.strip():
            logger.info(
                f"🚀 Starting auto-paste operation for text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
            )

            # First copy to clipboard
            if self.copy_to_clipboard(text):
                # Small delay to ensure clipboard is updated
                time.sleep(0.1)

                # Then simulate paste
                if self.simulate_paste():
                    # Add to history
                    self.add_to_history(text)
                    self.update_history_display()

                    # Press Enter if option is enabled
                    if (
                        hasattr(self, "press_enter_toggle")
                        and self.press_enter_toggle.value
                    ):
                        logger.info("⏎ Auto-Enter enabled - pressing Enter after paste")
                        time.sleep(0.1)  # Small delay between paste and enter
                        # Use the new key simulation system
                        key_config = {"keys": ["enter"]}
                        self.button_factory.key_simulator.simulate_key_combination(
                            key_config
                        )

                    logger.info("✅ Auto-paste operation completed successfully")
                    return True
                else:
                    logger.error("❌ Auto-paste failed at paste simulation step")
            else:
                logger.error("❌ Auto-paste failed at clipboard copy step")

        logger.warning("⚠️ Auto-paste operation failed or no text provided")
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
        if IS_MACOS or IS_WINDOWS:
            # Auto-refresh instances on page load
            self.refresh_cursor_instances()

            # Create tabs for instances if any exist
            if self.cursor_instances:
                with ui.tabs().classes("w-full") as tabs:
                    self.instance_tabs = {}
                    for instance in self.cursor_instances:
                        workspace = instance.get(
                            "Workspace", f"Window {instance.get('ID')}"
                        )
                        tab = ui.tab(workspace)
                        self.instance_tabs[workspace] = {
                            "tab": tab,
                            "instance": instance,
                        }

                # Tab panels (empty since tabs show the selection)
                with ui.tab_panels(tabs, value=None).classes("w-full") as panels:
                    for workspace in self.instance_tabs:
                        with ui.tab_panel(self.instance_tabs[workspace]["tab"]):
                            pass  # Empty panel - tabs show the selection

                # Handle tab selection with proper event binding
                def on_tab_change(e):
                    # Get the selected workspace from event args
                    selected_workspace = (
                        e.args if hasattr(e, "args") and e.args else None
                    )

                    logger.info(f"🎯 Tab clicked: {selected_workspace}")

                    if selected_workspace and selected_workspace in self.instance_tabs:
                        instance = self.instance_tabs[selected_workspace]["instance"]
                        logger.info(f"🎯 Activating instance: {instance}")

                        # Choose activation method based on OS
                        if IS_MACOS:
                            success = self.activate_cursor_instance_macos(instance)
                        elif IS_WINDOWS:
                            success = self.activate_cursor_instance_windows(instance)
                        else:
                            success = False

                        if success:
                            logger.info(
                                f"✅ Successfully activated workspace: {selected_workspace}"
                            )
                        else:
                            logger.error(
                                f"❌ Failed to activate workspace: {selected_workspace}"
                            )
                            self.show_status(
                                f"Failed to activate {selected_workspace}", "error"
                            )
                    else:
                        logger.warning(f"⚠️ Workspace not found: {selected_workspace}")

                # Try multiple event binding approaches
                tabs.on("update:model-value", on_tab_change)

                # Alternative: bind to panels value change (for redundancy)
                def on_panel_change(e):
                    # Get the selected workspace from event args
                    selected_workspace = (
                        e.args if hasattr(e, "args") and e.args else None
                    )

                    logger.info(f"🎯 Panel changed to: {selected_workspace}")

                    if selected_workspace and selected_workspace in self.instance_tabs:
                        instance = self.instance_tabs[selected_workspace]["instance"]
                        logger.info(f"🎯 Activating instance: {instance}")

                        # Choose activation method based on OS
                        if IS_MACOS:
                            success = self.activate_cursor_instance_macos(instance)
                        elif IS_WINDOWS:
                            success = self.activate_cursor_instance_windows(instance)
                        else:
                            success = False

                        if success:
                            logger.info(
                                f"✅ Successfully activated workspace: {selected_workspace}"
                            )
                        else:
                            logger.error(
                                f"❌ Failed to activate workspace: {selected_workspace}"
                            )
                            self.show_status(
                                f"Failed to activate {selected_workspace}", "error"
                            )
                    else:
                        logger.warning(f"⚠️ Workspace not found: {selected_workspace}")

                panels.on("update:model-value", on_panel_change)

        # Main content container
        with ui.column().classes("w-full max-w-2xl mx-auto"):
            # Text input area with direct storage binding
            self.text_area = (
                ui.textarea(placeholder="Type your text here...")
                .props("clearable")
                .bind_value(app.storage.general, self.storage_key)
            )

            # Voice input section (separate from other buttons)
            if self.voice_enabled:
                with ui.row().classes("w-full"):
                    self.voice_button = ui.button(
                        "Start Recording", on_click=self.toggle_voice_recording
                    ).classes("flex-1 p-2 m-1 bg-primary")

            # Main action buttons (from configuration)
            with ui.row().classes("w-full"):
                main_buttons = self.button_factory.get_buttons_for_group("main")
                for button in main_buttons:
                    # Buttons are already created by the factory
                    pass

            # Extended keyboard shortcuts row (from configuration)
            with ui.row().classes("w-full border"):
                extended_buttons = self.button_factory.get_buttons_for_group("extended")
                for button in extended_buttons:
                    # Buttons are already created by the factory
                    pass

            # Settings section - group toggles together
            with ui.column().classes("w-full border"):
                ui.label("Settings")
                with ui.column():
                    paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
                    self.auto_paste_toggle = ui.checkbox(
                        f"Auto-paste when copying to clipboard ({paste_key})",
                        value=True,
                    )

                    self.press_enter_toggle = ui.checkbox(
                        "Press Enter after pasting", value=True
                    )

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
                            top: 20px;
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
            paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
            ui.label(
                "Tap text area to start typing • Text syncs across all devices and tabs"
            )
            ui.label(f"Copy to clipboard • Auto-paste with {paste_key} on server")

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

            # Auto-paste if enabled
            if self.auto_paste_toggle.value:
                logger.info("🔄 Auto-paste enabled, initiating paste sequence")
                # Small delay to ensure clipboard is updated
                time.sleep(0.1)

                # Simulate paste
                if self.simulate_paste():
                    # Press Enter if option is enabled
                    if (
                        hasattr(self, "press_enter_toggle")
                        and self.press_enter_toggle.value
                    ):
                        logger.info("⏎ Auto-Enter enabled, pressing Enter after paste")
                        time.sleep(0.1)  # Small delay between paste and enter
                        # Use the new key simulation system
                        key_config = {"keys": ["enter"]}
                        self.button_factory.key_simulator.simulate_key_combination(
                            key_config
                        )

                    logger.info(
                        "✅ Copy and auto-paste operation completed successfully"
                    )
                    self.show_status("Text copied and pasted!", "success")
                else:
                    logger.error("❌ Copy succeeded but auto-paste failed")
                    self.show_status("Text copied, but paste failed", "error")
            else:
                logger.info("✅ Copy operation completed successfully")
                self.show_status("Text copied to clipboard!", "success")
        else:
            logger.error("❌ Copy operation failed")
            self.show_status("Failed to copy text", "error")

    def copy_to_clipboard_silent(self, text):
        """Copy text to clipboard without showing status"""
        if text and self.copy_to_clipboard(text):
            self.add_to_history(text)
            self.update_history_display()

    def paste_from_history(self, text):
        """Paste text from history using Ctrl+V simulation"""
        if self.auto_paste_text(text):
            self.show_status("Text pasted from history!", "success")
        else:
            self.show_status("Failed to paste text", "error")

    def clear_text(self):
        """Clear the text area"""
        logger.info("🗑️ Clearing text area")
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

    async def handle_audio_upload(self, event):
        """Handle audio file upload and transcription"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return

        if not event.content:
            self.show_status("No audio file selected", "error")
            return

        try:
            # Show processing status
            self.show_status("Processing audio file...", "info")
            logger.info(f"🎤 Processing uploaded audio file: {event.name}")

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(event.name).suffix
            ) as temp_file:
                # Fix: Read content from SpooledTemporaryFile properly
                if hasattr(event.content, "read"):
                    # If it's a file-like object, read its content
                    event.content.seek(0)  # Ensure we're at the beginning
                    audio_data = event.content.read()
                else:
                    # If it's already bytes
                    audio_data = event.content

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
                    # Add transcribed text to storage (UI will update automatically)
                    current_text = app.storage.general.get(self.storage_key, "")
                    if current_text:
                        app.storage.general[self.storage_key] = (
                            current_text + "\n" + transcribed_text
                        )
                    else:
                        app.storage.general[self.storage_key] = transcribed_text

                    # Add to history
                    self.add_to_history(transcribed_text)
                    self.update_history_display()

                    # Show success status
                    self.show_status(
                        f"Transcribed in {processing_time:.1f}s (Language: {language})",
                        "success",
                    )
                    logger.info(
                        f"✅ Audio transcription successful: {len(transcribed_text)} characters"
                    )
                else:
                    self.show_status("No speech detected in audio", "error")
                    logger.warning("⚠️ No speech detected in uploaded audio")
            else:
                error_msg = result.get("error", "Unknown error")
                self.show_status(f"Transcription failed: {error_msg}", "error")
                logger.error(f"❌ Audio transcription failed: {error_msg}")

        except Exception as e:
            self.show_status(f"Error processing audio: {str(e)}", "error")
            logger.error(f"❌ Audio processing error: {e}")

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

    async def handle_audio_data(self, audio_data):
        """Handle raw audio data from push-to-talk recording (with UI updates)"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return

        try:
            # Show processing status
            self.show_status("Processing recorded audio...", "info")

            # Process audio data
            result = await self.process_audio_data(audio_data)

            if result["success"]:
                transcribed_text = result["text"]
                processing_time = result.get("processing_time", 0)
                language = result.get("language", "unknown")

                # Add transcribed text to storage (UI will update automatically)
                current_text = app.storage.general.get(self.storage_key, "")
                if current_text:
                    app.storage.general[self.storage_key] = (
                        current_text + "\n" + transcribed_text
                    )
                else:
                    app.storage.general[self.storage_key] = transcribed_text

                # Add to history
                self.add_to_history(transcribed_text)
                self.update_history_display()

                # Show success status
                self.show_status(
                    f"Transcribed in {processing_time:.1f}s (Language: {language})",
                    "success",
                )
            else:
                error_msg = result.get("error", "Unknown error")
                self.show_status(f"Transcription failed: {error_msg}", "error")

        except Exception as e:
            self.show_status(f"Error processing recorded audio: {str(e)}", "error")
            logger.error(f"❌ Push-to-talk audio processing error: {e}")

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
            self.voice_button.classes("flex-1 p-2 m-1 bg-negative")

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
            self.voice_button.classes("flex-1 p-2 m-1 bg-primary")

            # Trigger JavaScript stop
            ui.run_javascript(
                "if (typeof stopRecording === 'function') stopRecording();"
            )

    def get_cursor_instances_windows(self):
        """Get all Cursor instances on Windows using Windows API"""
        if not WINDOWS_FALLBACK:
            logger.error("❌ Windows API not available")
            return []

        try:
            logger.info("🔍 Searching for Cursor windows on Windows...")

            # Callback function to enumerate windows
            def enum_windows_callback(hwnd, windows):
                if user32.IsWindowVisible(hwnd):
                    # Get window title
                    title_length = user32.GetWindowTextLengthW(hwnd)
                    if title_length > 0:
                        title_buffer = ctypes.create_unicode_buffer(title_length + 1)
                        user32.GetWindowTextW(hwnd, title_buffer, title_length + 1)
                        title = title_buffer.value

                        # Get process ID
                        process_id = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

                        # Get process name
                        try:
                            process_handle = kernel32.OpenProcess(
                                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                False,
                                process_id.value,
                            )
                            if process_handle:
                                process_name_buffer = ctypes.create_unicode_buffer(260)
                                if kernel32.QueryFullProcessImageNameW(
                                    process_handle,
                                    0,
                                    process_name_buffer,
                                    ctypes.byref(wintypes.DWORD(260)),
                                ):
                                    process_path = process_name_buffer.value
                                    process_name = os.path.basename(process_path)

                                    # Check if it's a Cursor process
                                    if process_name.lower() in ["cursor.exe", "cursor"]:
                                        windows.append(
                                            {
                                                "hwnd": hwnd,
                                                "title": title,
                                                "process_id": process_id.value,
                                                "process_name": process_name,
                                            }
                                        )

                                kernel32.CloseHandle(process_handle)
                        except Exception as e:
                            logger.debug(f"Error getting process info for window: {e}")

                return True

            # Define the callback function type
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, ctypes.POINTER(ctypes.py_object)
            )

            # Enumerate all windows
            windows = []
            enum_callback = WNDENUMPROC(enum_windows_callback)
            user32.EnumWindows(enum_callback, ctypes.py_object(windows))

            # Process the found windows
            instances = []
            for i, window in enumerate(windows):
                title = window["title"]

                # Extract workspace name from window title
                # Format: "filename — workspace" or "filename - workspace"
                workspace_name = "Unknown"
                if " — " in title:  # Using em dash
                    parts = title.split(" — ")
                    if len(parts) >= 2:
                        workspace_name = parts[1].strip()
                elif " - " in title:  # Fallback for regular dash
                    parts = title.split(" - ")
                    if len(parts) >= 2:
                        workspace_name = parts[1].strip()

                instance_info = {
                    "ID": str(i + 1),
                    "Title": title,
                    "Workspace": workspace_name,
                    "HWND": window["hwnd"],
                    "ProcessID": window["process_id"],
                }
                instances.append(instance_info)

            logger.info(f"🔍 Found {len(instances)} Cursor instances on Windows")
            return instances

        except Exception as e:
            logger.error(f"❌ Error enumerating Windows: {e}")
            return []

    def get_cursor_instances_macos(self):
        """Get all Cursor instances on macOS using AppleScript"""
        # First, let's try to just count windows to see if we can access them
        count_script = """
        tell application "System Events"
            set cursorProcesses to every application process whose name is "Cursor"
            set totalWindows to 0
            repeat with cursorProcess in cursorProcesses
                set windowList to every window of cursorProcess
                set totalWindows to totalWindows + (count of windowList)
            end repeat
            return totalWindows as string
        end tell
        """

        try:
            logger.info("🔍 First testing window count...")
            result = subprocess.run(
                ["osascript", "-e", count_script],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"📋 Window count result: '{result.stdout}'")

            if result.stdout.strip() == "0":
                logger.warning("⚠️ No Cursor windows found")
                return []

        except Exception as e:
            logger.error(f"❌ Window count test failed: {e}")
            return []

        # Now try to get window names with a different approach
        # Let's try building the result differently
        window_script = """
        tell application "System Events"
            set cursorProcesses to every application process whose name is "Cursor"
            set windowNames to {}
            
            repeat with cursorProcess in cursorProcesses
                set windowList to every window of cursorProcess
                repeat with currentWindow in windowList
                    try
                        set windowName to name of currentWindow
                        if windowName is not "" then
                            set end of windowNames to windowName
                        end if
                    end try
                end repeat
            end repeat
            
            -- Convert list to string manually
            set resultString to ""
            repeat with i from 1 to count of windowNames
                set resultString to resultString & item i of windowNames
                if i < count of windowNames then
                    set resultString to resultString & "|"
                end if
            end repeat
            
            return resultString
        end tell
        """

        try:
            logger.info("🔍 Running window names script...")
            result = subprocess.run(
                ["osascript", "-e", window_script],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                window_names = result.stdout.strip().split("|")
                logger.info(f"📋 Found window names: {window_names}")

                instances = []
                for i, window_name in enumerate(window_names):
                    if window_name.strip():
                        # Extract workspace name from window title
                        # Format: "filename — workspace"
                        workspace_name = "Unknown"
                        if " — " in window_name:  # Using em dash
                            parts = window_name.split(" — ")
                            if len(parts) >= 2:
                                workspace_name = parts[
                                    1
                                ].strip()  # Take the part after the em dash
                        elif " - " in window_name:  # Fallback for regular dash
                            parts = window_name.split(" - ")
                            if len(parts) >= 2:
                                workspace_name = parts[1].strip()

                        instance_info = {
                            "ID": str(i + 1),
                            "Title": window_name.strip(),
                            "Workspace": workspace_name,
                        }
                        instances.append(instance_info)

                logger.info(f"🔍 Found {len(instances)} Cursor instances")
                return instances
            else:
                logger.warning("⚠️ Window names script returned empty output")
                return []

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Window names script failed: {e}")
            logger.error(f"❌ Return code: {e.returncode}")
            logger.error(f"❌ Stdout: {e.stdout}")
            logger.error(f"❌ Stderr: {e.stderr}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return []

    def activate_cursor_instance_windows(self, instance_info):
        """Activate specific Cursor instance on Windows"""
        if not WINDOWS_FALLBACK:
            logger.error("❌ Windows API not available")
            return False

        hwnd = instance_info.get("HWND")
        workspace = instance_info.get("Workspace", "Unknown")
        title = instance_info.get("Title", "Unknown")

        logger.info("🎯 Attempting to activate Cursor instance on Windows:")
        logger.info(f"   - HWND: {hwnd}")
        logger.info(f"   - Workspace: {workspace}")
        logger.info(f"   - Title: {title}")

        try:
            # Check if window is minimized
            if user32.IsIconic(hwnd):
                logger.info("🔄 Window is minimized, restoring...")
                user32.ShowWindow(hwnd, SW_RESTORE)

            # Bring window to foreground
            logger.info("🔄 Bringing window to foreground...")
            user32.SetForegroundWindow(hwnd)

            # Additional method to ensure window is activated
            user32.BringWindowToTop(hwnd)

            # Check if successful
            foreground_hwnd = user32.GetForegroundWindow()
            if foreground_hwnd == hwnd:
                logger.info(f"✅ Successfully activated window: {title}")
                return True
            else:
                logger.warning(f"⚠️ Window activation may not have been successful")
                # Return True as some Windows versions may not update foreground immediately
                return True

        except Exception as e:
            logger.error(f"❌ Failed to activate window: {e}")
            return False

    def activate_cursor_instance_macos(self, instance_info):
        """Activate specific Cursor instance on macOS"""
        window_id = instance_info.get("ID", "1")
        workspace = instance_info.get("Workspace", "Unknown")
        title = instance_info.get("Title", "Unknown")

        logger.info("🎯 Attempting to activate Cursor instance:")
        logger.info(f"   - Window ID: {window_id}")
        logger.info(f"   - Workspace: {workspace}")
        logger.info(f"   - Title: {title}")

        # Try a more reliable approach: activate by window name instead of index
        escaped_title = title.replace('"', '\\"')  # Escape quotes in window title

        script = f"""
        tell application "System Events"
            tell application process "Cursor"
                set frontmost to true
                try
                    -- Get window count first
                    set windowCount to count of windows
                    log "Total windows: " & windowCount
                    
                    -- Try to find and activate the window by name
                    set targetWindow to first window whose name is "{escaped_title}"
                    
                    -- Bring the target window to front using different methods
                    try
                        -- Method 1: Set index to 1
                        set index of targetWindow to 1
                        log "Method 1 (set index) succeeded"
                    on error
                        try
                            -- Method 2: Perform action (click)
                            perform action "AXRaise" of targetWindow
                            log "Method 2 (AXRaise) succeeded"
                        on error
                            -- Method 3: Simple click
                            click targetWindow
                            log "Method 3 (click) succeeded"
                        end try
                    end try
                    
                    -- Verify the window is now frontmost
                    set frontWindow to window 1
                    set frontWindowName to name of frontWindow
                    log "Front window is now: " & frontWindowName
                    
                    return "success:" & frontWindowName
                on error errMsg
                    log "Error: " & errMsg
                    return "error:" & errMsg
                end try
            end tell
        end tell
        """

        try:
            logger.info("🍎 Executing AppleScript for window activation...")
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, check=True
            )

            output = result.stdout.strip()
            logger.info(f"🍎 AppleScript output: '{output}'")

            if "success:" in output:
                activated_window = output.split("success:")[1]
                logger.info(f"✅ Successfully activated window: '{activated_window}'")
                logger.info(f"✅ Target was: '{title}'")
                return True
            elif "error:" in output:
                error_msg = output.split("error:")[1]
                logger.error(f"❌ AppleScript error: {error_msg}")

                # Try simpler fallback approach - target Cursor app directly
                logger.info("🔄 Trying simpler fallback approach...")
                simple_script = f"""
                tell application "Cursor"
                    activate
                    try
                        -- Try to bring specific window to front
                        set targetWindow to first window whose name contains "{workspace}"
                        set index of targetWindow to 1
                        return "fallback_success"
                    on error
                        -- Just activate the app
                        return "app_activated"
                    end try
                end tell
                """

                try:
                    fallback_result = subprocess.run(
                        ["osascript", "-e", simple_script],
                        capture_output=True,
                        text=True,
                        check=True,
                    )

                    fallback_output = fallback_result.stdout.strip()
                    logger.info(f"🔄 Fallback result: '{fallback_output}'")

                    if "success" in fallback_output or "activated" in fallback_output:
                        logger.info(
                            f"✅ Fallback activation succeeded for workspace: {workspace}"
                        )
                        return True

                except Exception as fallback_error:
                    logger.error(f"❌ Fallback approach also failed: {fallback_error}")

                return False
            else:
                logger.error(f"❌ Unexpected AppleScript output: {output}")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to execute AppleScript: {e}")
            logger.error(f"❌ Return code: {e.returncode}")
            logger.error(f"❌ Stdout: {e.stdout}")
            logger.error(f"❌ Stderr: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during window activation: {e}")
            return False

    def test_applescript_debug(self):
        """Test AppleScript execution for debugging"""
        logger.info("🔧 DEBUG: Testing AppleScript execution...")
        logger.info(
            "🔧 DEBUG: Note - If this fails, you may need to grant Terminal/Python accessibility permissions"
        )
        logger.info(
            "🔧 DEBUG: Go to System Preferences > Security & Privacy > Privacy > Accessibility"
        )
        logger.info("🔧 DEBUG: Add Terminal or Python to the list of allowed apps")

        # Test 1: Very simple script
        test_script = """
        tell application "System Events"
            return "AppleScript is working"
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", test_script],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"🔧 DEBUG: Simple test result: '{result.stdout}'")
        except Exception as e:
            logger.error(f"🔧 DEBUG: Simple test failed: {e}")
            return

        # Test 2: Check if Cursor process exists
        cursor_test_script = """
        tell application "System Events"
            set appList to name of every application process
            return appList as string
        end tell
        """

        try:
            result = subprocess.run(
                ["osascript", "-e", cursor_test_script],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"🔧 DEBUG: Running apps: '{result.stdout}'")
            if "Cursor" in result.stdout:
                logger.info("🔧 DEBUG: ✅ Cursor process found in running apps")
            else:
                logger.warning("🔧 DEBUG: ⚠️ Cursor process NOT found in running apps")
        except Exception as e:
            logger.error(f"🔧 DEBUG: App list test failed: {e}")

        # Test 3: Try to get Cursor windows
        logger.info("🔧 DEBUG: Testing Cursor window detection...")
        instances = self.get_cursor_instances_macos()
        logger.info(f"🔧 DEBUG: Final result: {len(instances)} instances found")
        for instance in instances:
            logger.info(f"🔧 DEBUG: Instance: {instance}")

    def refresh_cursor_instances(self):
        """Refresh the list of Cursor instances"""
        logger.info("🔄 Refreshing Cursor instances...")

        if IS_MACOS:
            self.cursor_instances = self.get_cursor_instances_macos()
            logger.info(
                f"🔄 Refresh complete: {len(self.cursor_instances)} instances found"
            )

            # Log each instance
            for i, instance in enumerate(self.cursor_instances):
                logger.info(f"🔄 Instance {i+1}: {instance}")
        elif IS_WINDOWS:
            self.cursor_instances = self.get_cursor_instances_windows()
            logger.info(
                f"🔄 Refresh complete: {len(self.cursor_instances)} instances found"
            )

            # Log each instance
            for i, instance in enumerate(self.cursor_instances):
                logger.info(f"🔄 Instance {i+1}: {instance}")
        else:
            logger.warning(
                "⚠️ Instance management only available on macOS and Windows currently"
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

    # Get local IP for display
    local_ip = text_app.get_local_ip()

    print("Starting Mobile Text Input Server...")
    print("✅ Cross-device synchronization enabled")
    print("Local access: http://localhost:8080")
    print(f"Network access: http://{local_ip}:8080")
    print(
        f"Mobile access: Connect your mobile device to the same network and visit http://{local_ip}:8080"
    )
    print("📱 Text syncs across all devices and browser tabs")
    print("Press Ctrl+C to stop the server")

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
