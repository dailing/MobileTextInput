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

        if WHISPER_AVAILABLE:
            self.load_model()
        else:
            logger.error("❌ Whisper not available - voice processing disabled")

    def load_model(self):
        """Load the Whisper model with GPU support if available"""
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
        if not self.model_loaded:
            return {"success": False, "error": "Whisper model not loaded"}

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
        if not self.model_loaded:
            return "❌ No model loaded"

        return {
            "model": "medium",
            "size": "~769MB",
            "accuracy": "Better accuracy for most languages",
            "speed": "Moderate processing speed",
            "languages": "99 languages supported",
            "device": self.device,
            "cuda_available": CUDA_AVAILABLE,
        }


class TextInputApp:
    def __init__(self):
        self.current_text = ""
        self.text_history = []
        self.max_history = 10
        self.storage_key = "shared_text"
        self.history_key = "shared_history"

        # Initialize voice processor
        self.voice_processor = VoiceProcessor() if WHISPER_AVAILABLE else None
        self.voice_enabled = WHISPER_AVAILABLE and self.voice_processor.model_loaded

        # Initialize instance management
        self.cursor_instances = []

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

    def simulate_enter(self):
        """Simulate Enter key press"""
        if not KEYBOARD_AVAILABLE:
            logger.error("❌ Keyboard simulation not available - cannot simulate Enter")
            return False

        try:
            logger.info("⏎ Simulating Enter key press")

            if CURRENT_OS == "Windows":
                # Try Windows native method first
                if WINDOWS_FALLBACK:
                    logger.info("🔧 Using Windows native Enter key simulation")
                    # Windows VK code: Enter = 0x0D
                    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
                    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up
                    logger.info(
                        "✅ Windows native Enter key operation completed successfully"
                    )
                    return True

            # Fallback to pynput for all systems
            if PYNPUT_AVAILABLE:
                logger.info("🔧 Using pynput for Enter key simulation")
                keyboard_controller.press(Key.enter)
                keyboard_controller.release(Key.enter)
                logger.info("✅ pynput Enter key operation completed successfully")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to simulate Enter key: {e}")
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
                        self.simulate_enter()

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

                # Sync to storage for cross-device synchronization
                self.sync_to_storage()
            else:
                logger.debug("📝 Text already exists in history, skipping duplicate")

    def sync_to_storage(self):
        """Sync current text and history to shared storage"""
        try:
            app.storage.general[self.storage_key] = self.current_text
            app.storage.general[self.history_key] = self.text_history
            logger.debug("💾 Successfully synced data to storage")
        except Exception as e:
            logger.error(f"❌ Failed to sync to storage: {e}")

    def sync_from_storage(self):
        """Sync text and history from shared storage"""
        try:
            # Load text from storage
            stored_text = app.storage.general.get(self.storage_key, "")
            if stored_text != self.current_text:
                logger.debug(
                    f"🔄 Syncing text from storage: '{stored_text[:30]}{'...' if len(stored_text) > 30 else ''}'"
                )
                self.current_text = stored_text
                if hasattr(self, "text_area"):
                    self.text_area.set_value(stored_text)

            # Load history from storage
            stored_history = app.storage.general.get(self.history_key, [])
            if stored_history != self.text_history:
                logger.debug(
                    f"🔄 Syncing history from storage: {len(stored_history)} entries"
                )
                self.text_history = stored_history
                if hasattr(self, "history_container"):
                    self.update_history_display()
        except Exception as e:
            logger.error(f"❌ Failed to sync from storage: {e}")

    def start_storage_sync(self):
        """Start periodic sync with storage"""
        logger.info("🔄 Starting periodic storage synchronization")

        def sync_timer():
            try:
                self.sync_from_storage()
            except Exception as e:
                logger.error(f"❌ Storage sync error: {e}")

        # Use NiceGUI timer for periodic sync
        ui.timer(1.0, sync_timer)  # Check every second

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
            <style>
                .text-input-container {
                    width: 100%;
                    max-width: 600px;
                    margin: 0 auto;
                }
                .mobile-textarea {
                    width: 100% !important;
                    min-height: 200px !important;
                    font-size: 16px !important;
                    padding: 15px !important;
                    border-radius: 8px !important;
                    border: 2px solid #ddd !important;
                    resize: vertical !important;
                }
                .mobile-textarea:focus {
                    border-color: #4CAF50 !important;
                    outline: none !important;
                }
                .action-button {
                    flex: 1 !important;
                    padding: 15px !important;
                    font-size: 16px !important;
                    margin: 5px !important;
                    border-radius: 8px !important;
                    min-width: 0 !important;
                }
                .copy-button {
                    background-color: #4CAF50 !important;
                    color: white !important;
                }
                .clear-button {
                    background-color: #f44336 !important;
                    color: white !important;
                }
                .history-item {
                    background-color: #f5f5f5 !important;
                    padding: 10px !important;
                    margin: 5px 0 !important;
                    border-radius: 5px !important;
                    border-left: 4px solid #4CAF50 !important;
                }
                .header {
                    text-align: center !important;
                    padding: 20px 0 !important;
                    background-color: #f8f9fa !important;
                    margin-bottom: 20px !important;
                }
                .footer {
                    text-align: center !important;
                    padding: 20px 0 !important;
                    color: #666 !important;
                    font-size: 14px !important;
                }
                .voice-button {
                    background-color: #2196F3 !important;
                    color: white !important;
                }
                .upload-button {
                    background-color: #FF9800 !important;
                    color: white !important;
                    border: 2px dashed #FF9800 !important;
                }
                .voice-info {
                    background-color: #E8F5E8 !important;
                    padding: 10px !important;
                    border-radius: 5px !important;
                    margin: 10px 0 !important;
                }
                
                /* Responsive button layout */
                @media (max-width: 480px) {
                    .action-button {
                        font-size: 14px !important;
                        padding: 12px 8px !important;
                        margin: 3px !important;
                    }
                }
                
                /* Ensure buttons wrap on very small screens */
                @media (max-width: 360px) {
                    .action-button {
                        flex-basis: 48% !important;
                        margin: 2px !important;
                    }
                }
                
                /* UI Grouping styles */
                .settings-section {
                    background-color: #f8f9fa !important;
                    border-radius: 8px !important;
                    padding: 15px !important;
                    margin: 10px 0 !important;
                    border-left: 4px solid #4CAF50 !important;
                }
                
                .status-section {
                    background-color: #f0f8ff !important;
                    border-radius: 8px !important;
                    padding: 15px !important;
                    margin: 10px 0 !important;
                    border-left: 4px solid #2196F3 !important;
                }
                
                .section-title {
                    margin-bottom: 12px !important;
                    font-weight: 600 !important;
                    color: #333 !important;
                }
                
                .instance-tab-selected {
                    background-color: #4CAF50 !important;
                    color: white !important;
                    border: 2px solid #4CAF50 !important;
                    font-weight: bold !important;
                }
                
                .instance-tab {
                    background-color: #f5f5f5 !important;
                    color: #333 !important;
                    border: 1px solid #ddd !important;
                }
                
                .instance-section {
                    background-color: #f0f8ff !important;
                    border-radius: 8px !important;
                    padding: 15px !important;
                    margin: 10px 0 !important;
                    border-left: 4px solid #2196F3 !important;
                }
                
                /* Recording animation */
                @keyframes pulse-red {
                    0% {
                        transform: scale(1);
                        box-shadow: 0 0 15px rgba(211, 47, 47, 0.5);
                    }
                    50% {
                        transform: scale(1.05);
                        box-shadow: 0 0 25px rgba(211, 47, 47, 0.8);
                    }
                    100% {
                        transform: scale(1);
                        box-shadow: 0 0 15px rgba(211, 47, 47, 0.5);
                    }
                }
            </style>
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
        with ui.column().classes("text-input-container"):
            # Text input area
            self.text_area = ui.textarea(
                placeholder="Type your text here...", value=""
            ).classes("mobile-textarea")

            # Action buttons (including voice if available)
            with ui.row().classes("w-full"):
                self.copy_button = ui.button(
                    "Copy", on_click=self.copy_current_text
                ).classes("action-button copy-button")

                self.enter_button = ui.button(
                    "Enter", on_click=self.press_enter_key
                ).classes("action-button copy-button")

                # Add voice button if available
                if self.voice_enabled:
                    self.voice_button = ui.button(
                        "Start Recording", on_click=None
                    ).classes("action-button voice-button")

                self.clear_button = ui.button(
                    "Clear", on_click=self.clear_text
                ).classes("action-button clear-button")

            # Extended keyboard shortcuts row
            with ui.row().classes("w-full"):
                cmd_key = "Cmd" if IS_MACOS else "Ctrl"

                self.accept_button = ui.button(
                    f"Accept ({cmd_key}+↵)", on_click=self.press_accept_key
                ).classes("action-button copy-button")

                self.reject_button = ui.button(
                    f"Reject ({cmd_key}+⌫)", on_click=self.press_reject_key
                ).classes("action-button clear-button")

                self.new_button = ui.button(
                    f"New ({cmd_key}+N)", on_click=self.press_new_key
                ).classes("action-button copy-button")

                self.stop_button = ui.button(
                    f"Stop ({cmd_key}+⇧+⌫)", on_click=self.press_stop_key
                ).classes("action-button clear-button")

            # Settings section - group toggles together
            with ui.column().classes("w-full settings-section"):
                ui.label("Settings").classes("section-title")
                with ui.column().style("gap: 8px;"):
                    paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
                    self.auto_paste_toggle = ui.checkbox(
                        f"Auto-paste when copying to clipboard ({paste_key})",
                        value=True,
                    )

                    self.press_enter_toggle = ui.checkbox(
                        "Press Enter after pasting", value=True
                    )

            # Status section - group all status info together
            with ui.column().classes("w-full status-section"):
                ui.label("System Status").classes("section-title")
                with ui.column().style("gap: 4px;"):
                    # Voice status
                    if self.voice_enabled:
                        voice_info = self.voice_processor.get_model_info()
                        ui.label(
                            f"🎤 Voice: Whisper {voice_info['model']} ready • Button turns red when recording"
                        ).classes("text-caption text-green")
                    else:
                        ui.label("❌ Voice-to-text not available").classes(
                            "text-caption text-red"
                        )
                        if not WHISPER_AVAILABLE:
                            ui.label("📦 Install: pip install openai-whisper").classes(
                                "text-caption text-red"
                            )

                    # Keyboard simulation status
                    if WINDOWS_FALLBACK:
                        ui.label("✅ Windows native keyboard simulation").classes(
                            "text-caption text-green"
                        )
                    elif PYNPUT_AVAILABLE:
                        ui.label("✅ pynput keyboard simulation").classes(
                            "text-caption text-green"
                        )
                    else:
                        ui.label("⚠️ Keyboard simulation not available").classes(
                            "text-caption text-orange"
                        )
                        if not KEYBOARD_AVAILABLE:
                            ui.label("📦 Install pynput: pip install pynput").classes(
                                "text-caption text-red"
                            )

                    # Storage synchronization status
                    ui.label("✅ Cross-device synchronization enabled").classes(
                        "text-caption text-blue"
                    )
                    ui.label(
                        "📱 Text syncs across all devices and browser tabs"
                    ).classes("text-caption text-blue")

            # Add JavaScript for voice functionality if enabled
            if self.voice_enabled:
                ui.add_head_html(
                    """
                    <script>
                    let mediaRecorder;
                    let audioChunks = [];
                    let isRecording = false;
                    let pollInterval;
                    let microphonePermissionGranted = false;
                    let audioStream = null;
                    
                    // Function to request microphone permissions upfront
                    async function requestMicrophonePermission() {
                        try {
                            // Request microphone access
                            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                            microphonePermissionGranted = true;
                            
                            // Update button state to ready for recording
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.disabled = false;
                                button.textContent = 'Start Recording';
                                button.style.opacity = '1';
                                button.style.backgroundColor = '#2196F3';
                                button.style.color = 'white';
                                button.style.border = 'none';
                                button.style.boxShadow = 'none';
                                button.style.fontWeight = 'normal';
                                button.style.animation = 'none';
                            }
                            
                            // Show success message
                            showStatus('Microphone access granted! Ready to record.', 'success');
                            
                            // Stop the stream for now - we'll create a new one when recording
                            audioStream.getTracks().forEach(track => track.stop());
                            audioStream = null;
                            
                        } catch (error) {
                            console.error('Error requesting microphone permission:', error);
                            microphonePermissionGranted = false;
                            
                            // Update button state
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.disabled = true;
                                button.textContent = 'Microphone Access Denied';
                                button.style.opacity = '0.5';
                                button.style.backgroundColor = '#757575';
                            }
                            
                            // Show error message
                            showStatus('Microphone access denied. Please enable microphone permissions in your browser settings.', 'error');
                        }
                    }
                    
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
                    
                    // Function to update text area
                    function updateTextArea(newText) {
                        const textarea = document.querySelector('.mobile-textarea textarea');
                        if (textarea) {
                            const currentText = textarea.value || '';
                            const updatedText = currentText ? currentText + '\\n' + newText : newText;
                            textarea.value = updatedText;
                            
                            // Trigger input event to sync with backend
                            const event = new Event('input', { bubbles: true });
                            textarea.dispatchEvent(event);
                        }
                    }
                    
                    // Function to poll for voice results
                    function pollForResults() {
                        fetch('/check-voice-result')
                            .then(response => response.json())
                            .then(data => {
                                if (data.success && data.result) {
                                    const result = data.result;
                                    updateTextArea(result.text);
                                    showStatus(
                                        `Transcribed in ${result.processing_time.toFixed(1)}s (Language: ${result.language})`,
                                        'success'
                                    );
                                    
                                    // Stop polling
                                    if (pollInterval) {
                                        clearInterval(pollInterval);
                                        pollInterval = null;
                                    }
                                }
                            })
                            .catch(error => {
                                console.error('Error polling for results:', error);
                            });
                    }
                    
                    async function startRecording() {
                        if (isRecording) return;
                        
                        // Check if microphone permission was granted
                        if (!microphonePermissionGranted) {
                            showStatus('Microphone access not granted. Please allow microphone access and refresh the page.', 'error');
                            return;
                        }
                        
                        try {
                            // Request fresh stream for recording
                            audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
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
                                        // Start polling for results
                                        pollInterval = setInterval(pollForResults, 100);
                                        // Also check immediately
                                        pollForResults();
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
                            
                            // Update button text and style for recording state
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.textContent = '🔴 Recording... (Click to Stop)';
                                button.style.backgroundColor = '#d32f2f';
                                button.style.color = 'white';
                                button.style.border = '2px solid #b71c1c';
                                button.style.boxShadow = '0 0 15px rgba(211, 47, 47, 0.5)';
                                button.style.fontWeight = 'bold';
                                // Add pulsing animation
                                button.style.animation = 'pulse-red 1.5s infinite';
                            }
                            
                        } catch (error) {
                            console.error('Error accessing microphone:', error);
                            showStatus('Error accessing microphone. Please check permissions.', 'error');
                        }
                    }
                    
                    function stopRecording() {
                        if (mediaRecorder && isRecording) {
                            mediaRecorder.stop();
                            
                            // Reset button text and style to normal state
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                button.textContent = 'Start Recording';
                                button.style.backgroundColor = '#2196F3';
                                button.style.color = 'white';
                                button.style.border = 'none';
                                button.style.boxShadow = 'none';
                                button.style.fontWeight = 'normal';
                                button.style.animation = 'none';
                            }
                        }
                    }
                    
                    // Toggle recording function
                    function toggleRecording() {
                        if (isRecording) {
                            stopRecording();
                        } else {
                            startRecording();
                        }
                    }
                    
                    // Add event listeners when page loads
                    document.addEventListener('DOMContentLoaded', function() {
                        setTimeout(() => {
                            const button = document.querySelector('.voice-button');
                            if (button) {
                                // Initialize button as disabled until permission is granted
                                button.disabled = true;
                                button.textContent = 'Requesting Microphone...';
                                button.style.opacity = '0.5';
                                
                                // Single click event for both desktop and mobile
                                button.addEventListener('click', (e) => {
                                    e.preventDefault();
                                    toggleRecording();
                                });
                                
                                // Prevent context menu on long press (mobile)
                                button.addEventListener('contextmenu', (e) => {
                                    e.preventDefault();
                                });
                                
                                // Request microphone permission
                                requestMicrophonePermission();
                            }
                        }, 100);
                    });
                    </script>
                """
                )

            # History section
            ui.separator()
            ui.label("Recent Text History:").classes("text-h6")
            self.history_container = ui.column().classes("w-full")

        # Footer
        with ui.column().classes("footer"):
            paste_key = "Cmd+V" if IS_MACOS else "Ctrl+V"
            ui.label(
                "Tap text area to start typing • Text syncs across all devices and tabs"
            )
            ui.label(f"Copy to clipboard • Auto-paste with {paste_key} on server")

        # Set up event handlers
        self.text_area.on("input", self.on_text_change)

        # Initialize from storage and start sync
        self.sync_from_storage()
        self.start_storage_sync()
        self.update_history_display()

    def on_text_change(self, event):
        """Handle text change events"""
        text = event.value if event.value else ""
        self.current_text = text  # Keep internal state synchronized

        # Sync to storage for cross-device synchronization
        self.sync_to_storage()

    def copy_current_text(self):
        """Copy current text to clipboard with user feedback"""
        # Get text directly from the text area widget to ensure we have the current value
        text = self.text_area.value.strip() if self.text_area.value else ""

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
            self.text_area.set_value("")
            self.current_text = ""
            self.sync_to_storage()

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
                        self.simulate_enter()

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

    def press_enter_key(self):
        """Press Enter key on the server"""
        logger.info("⏎ Enter key button pressed")

        if self.simulate_enter():
            logger.info("✅ Enter key simulation completed successfully")
            self.show_status("Enter key pressed!", "success")
        else:
            logger.error("❌ Enter key simulation failed")
            self.show_status("Failed to press Enter key", "error")

    def press_accept_key(self):
        """Press Accept key combination on the server"""
        cmd_key = "Cmd" if IS_MACOS else "Ctrl"
        logger.info(f"✅ Accept ({cmd_key}+Enter) button pressed")

        if self.simulate_accept():
            logger.info(
                f"✅ Accept ({cmd_key}+Enter) simulation completed successfully"
            )
            self.show_status(f"Accept ({cmd_key}+Enter) pressed!", "success")
        else:
            logger.error(f"❌ Accept ({cmd_key}+Enter) simulation failed")
            self.show_status(f"Failed to press Accept ({cmd_key}+Enter)", "error")

    def press_reject_key(self):
        """Press Reject key combination on the server"""
        cmd_key = "Cmd" if IS_MACOS else "Ctrl"
        logger.info(f"🚫 Reject ({cmd_key}+Backspace) button pressed")

        if self.simulate_reject():
            logger.info(
                f"✅ Reject ({cmd_key}+Backspace) simulation completed successfully"
            )
            self.show_status(f"Reject ({cmd_key}+Backspace) pressed!", "success")
        else:
            logger.error(f"❌ Reject ({cmd_key}+Backspace) simulation failed")
            self.show_status(f"Failed to press Reject ({cmd_key}+Backspace)", "error")

    def press_new_key(self):
        """Press New key combination on the server"""
        cmd_key = "Cmd" if IS_MACOS else "Ctrl"
        logger.info(f"📄 New ({cmd_key}+N) button pressed")

        if self.simulate_new():
            logger.info(f"✅ New ({cmd_key}+N) simulation completed successfully")
            self.show_status(f"New ({cmd_key}+N) pressed!", "success")
        else:
            logger.error(f"❌ New ({cmd_key}+N) simulation failed")
            self.show_status(f"Failed to press New ({cmd_key}+N)", "error")

    def press_stop_key(self):
        """Press Stop key combination on the server"""
        cmd_key = "Cmd" if IS_MACOS else "Ctrl"
        logger.info(f"🛑 Stop ({cmd_key}+Shift+Backspace) button pressed")

        if self.simulate_stop():
            logger.info(
                f"✅ Stop ({cmd_key}+Shift+Backspace) simulation completed successfully"
            )
            self.show_status(f"Stop ({cmd_key}+Shift+Backspace) pressed!", "success")
        else:
            logger.error(f"❌ Stop ({cmd_key}+Shift+Backspace) simulation failed")
            self.show_status(
                f"Failed to press Stop ({cmd_key}+Shift+Backspace)", "error"
            )

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
        logger.info("🗑️ Clearing text area and syncing across devices")
        self.text_area.set_value("")
        self.current_text = ""

        # Clear storage for cross-device synchronization
        self.sync_to_storage()

        logger.info("✅ Text cleared successfully on all devices")
        self.show_status("Text cleared on all devices", "success")

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
                ui.label("No recent text entries").classes("text-caption text-center")
            return

        with self.history_container:
            for i, entry in enumerate(self.text_history):
                with ui.card().classes("history-item w-full"):
                    with ui.row().classes("w-full justify-between items-center"):
                        with ui.column().classes("flex-grow"):
                            # Show preview of text (first 50 chars)
                            preview = entry["text"][:50]
                            if len(entry["text"]) > 50:
                                preview += "..."
                            ui.label(preview).classes("text-body2")
                            ui.label(f"Added: {entry['timestamp']}").classes(
                                "text-caption"
                            )

                        with ui.row():
                            ui.button(
                                "Copy",
                                on_click=lambda e, text=entry[
                                    "text"
                                ]: self.copy_from_history(text),
                            ).classes("copy-button")

                            ui.button(
                                "Paste",
                                on_click=lambda e, text=entry[
                                    "text"
                                ]: self.paste_from_history(text),
                            ).classes("copy-button")

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
                    # Add transcribed text to the text area
                    current_text = self.text_area.value or ""
                    if current_text:
                        new_text = current_text + "\n" + transcribed_text
                    else:
                        new_text = transcribed_text

                    self.text_area.set_value(new_text)
                    self.current_text = new_text
                    self.sync_to_storage()

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
                    # Store result in app storage for UI to pick up
                    app.storage.user["voice_result"] = {
                        "text": transcribed_text,
                        "processing_time": processing_time,
                        "language": language,
                        "timestamp": time.time(),
                    }

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

                # Add transcribed text to the text area
                current_text = self.text_area.value or ""
                if current_text:
                    new_text = current_text + "\n" + transcribed_text
                else:
                    new_text = transcribed_text

                self.text_area.set_value(new_text)
                self.current_text = new_text
                self.sync_to_storage()

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

    def start_voice_recording(self):
        """Start voice recording (placeholder for future implementation)"""
        if not self.voice_enabled:
            self.show_status("Voice-to-text is not available", "error")
            return

        # This would be implemented with WebRTC MediaRecorder API in the future
        self.show_status(
            "Voice recording not yet implemented. Please use file upload.", "info"
        )
        logger.info("🎤 Voice recording requested (not yet implemented)")

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

    @app.get("/check-voice-result")
    async def check_voice_result():
        """Check for new voice transcription results"""
        try:
            if "voice_result" in app.storage.user:
                result = app.storage.user["voice_result"]
                # Clear the result after reading
                del app.storage.user["voice_result"]
                return {"success": True, "result": result}
            else:
                return {"success": False, "message": "No new results"}
        except Exception as e:
            logger.error(f"❌ Error checking voice result: {e}")
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
        show=False,  # Don't auto-open browser
        storage_secret="mobile-text-input-secret-key-2024",  # Enable cross-device storage
    )


if __name__ == "__main__" or __name__ == "__mp_main__":
    main()
