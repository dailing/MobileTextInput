#!/usr/bin/env python3
"""
Key Simulator Module
Provides cross-platform keyboard simulation functionality
"""

import time
import logging
from typing import List, Tuple, Optional
from os_detector import os_detector

# Configure logging
logger = logging.getLogger(__name__)

# Import keyboard simulation library
try:
    from pynput.keyboard import Key, Controller

    keyboard_controller = Controller()
    PYNPUT_AVAILABLE = True
    logger.info("✅ pynput keyboard simulation library loaded")
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard_controller = None
    logger.warning("⚠️ pynput not available - keyboard simulation disabled")

# Windows-specific setup
if os_detector.is_windows:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        WINDOWS_API_AVAILABLE = True
        logger.info("✅ Windows native keyboard simulation available")
    except (ImportError, AttributeError):
        WINDOWS_API_AVAILABLE = False
        user32 = None
        logger.warning("⚠️ Windows native APIs not available")
else:
    WINDOWS_API_AVAILABLE = False
    user32 = None

# OS detection is now handled by os_detector module


class KeySimulator:
    """Sequence-based key simulation handler"""

    def __init__(self):
        self.current_os = os_detector.current_os

    def simulate_key_sequence(self, key_sequence: List[Tuple[str, str]]) -> bool:
        """
        Simulate a sequence of key actions

        Args:
            key_sequence: List of (key, action) tuples like
                [("ctrl", "down"), ...]

        Returns:
            bool: True if simulation was successful, False otherwise
        """
        if not self.is_keyboard_available():
            logger.error("❌ Keyboard simulation not available")
            return False

        logger.info(f"🎹 Simulating key sequence: {key_sequence}")
        
        try:
            for i, (key, action) in enumerate(key_sequence):
                logger.debug(f"🎹 Step {i+1}: {key} {action}")
                success = self._simulate_key_action(key, action)
                if not success:
                    logger.error(f"❌ Failed at step {i+1}: {key} {action}")
                    return False
                
                # OS-specific timing for reliability
                delay = os_detector.get_os_specific_delay(action)
                if os_detector.is_macos:
                    logger.debug(f"🍎 macOS delay: {delay}s")
                else:
                    logger.debug(f"🪟 Windows/Linux delay: {delay}s")
                
                time.sleep(delay)
                    
            logger.info("✅ Key sequence completed successfully")
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
            logger.debug(f"🔽 Key down: {key}")
            
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 0, 0)  # Key down
                    logger.debug(f"🪟 Windows key down: {key} (VK: {vk_code})")
                    return True

            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.press(pynput_key)
                logger.debug(f"🎹 pynput key down: {key} -> {pynput_key}")
                return True

            logger.error(f"❌ No available method for key down: {key}")
            return False
        except Exception as e:
            logger.error(f"❌ Key down failed: {e}")
            return False

    def _key_up(self, key: str) -> bool:
        """Release a key"""
        try:
            logger.debug(f"🔼 Key up: {key}")
            
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 2, 0)  # Key up
                    logger.debug(f"🪟 Windows key up: {key} (VK: {vk_code})")
                    return True

            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.release(pynput_key)
                logger.debug(f"🎹 pynput key up: {key} -> {pynput_key}")
                return True

            logger.error(f"❌ No available method for key up: {key}")
            return False
        except Exception as e:
            logger.error(f"❌ Key up failed: {e}")
            return False

    def _press_key(self, key_name: str) -> bool:
        """Press a single key"""
        try:
            logger.debug(f"🔘 Press key: {key_name}")
            
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                # Use Windows native API for simple keys
                if key_name == "enter":
                    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
                    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up
                    logger.debug(f"🪟 Windows press: {key_name}")
                    return True

            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key_name)
                keyboard_controller.press(pynput_key)
                keyboard_controller.release(pynput_key)
                logger.debug(f"🎹 pynput press: {key_name} -> {pynput_key}")
                return True

            logger.error(f"❌ No available method for press: {key_name}")
            return False

        except Exception as e:
            logger.error(f"❌ Single key press failed: {e}")
            return False

    @staticmethod
    def _get_windows_vk_code(key: str) -> Optional[int]:
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

    @staticmethod
    def _get_pynput_key(key_name: str):
        """Convert key name to pynput key object"""
        special_keys = {
            "enter": Key.enter,
            "backspace": Key.backspace,
            "space": Key.space,
            "tab": Key.tab,
            "ctrl": Key.ctrl,
            "shift": Key.shift,
            "alt": Key.alt,
            "cmd": Key.cmd,
        }
        return special_keys.get(key_name, key_name)

    @staticmethod
    def is_keyboard_available() -> bool:
        """Check if keyboard simulation is available"""
        return PYNPUT_AVAILABLE or WINDOWS_API_AVAILABLE


def create_key_simulator() -> KeySimulator:
    """Factory function to create a KeySimulator instance
    
    Note: OS detection is now handled centrally by os_detector module
    """
    return KeySimulator()
