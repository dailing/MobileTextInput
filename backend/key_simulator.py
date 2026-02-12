#!/usr/bin/env python3
"""
Key Simulator Module
Provides cross-platform keyboard simulation functionality
"""

import time
from typing import List, Tuple, Optional
from os_detector import os_detector
from loguru import logger

try:
    from pynput.keyboard import Key, Controller
    keyboard_controller = Controller()
    PYNPUT_AVAILABLE = True
    logger.info("pynput keyboard simulation library loaded")
    if os_detector.is_macos:
        logger.info(
            "macOS: if simulated keys do not appear in other apps, grant "
            "Accessibility permission to Terminal (or your IDE) in "
            "System Settings > Privacy & Security > Accessibility"
        )
except ImportError:
    PYNPUT_AVAILABLE = False
    keyboard_controller = None
    logger.warning("pynput not available - keyboard simulation disabled")

if os_detector.is_windows:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        WINDOWS_API_AVAILABLE = True
        logger.info("Windows native keyboard simulation available")
    except (ImportError, AttributeError):
        WINDOWS_API_AVAILABLE = False
        user32 = None
        logger.warning("Windows native APIs not available")
else:
    WINDOWS_API_AVAILABLE = False
    user32 = None


class KeySimulator:
    """Sequence-based key simulation handler"""

    def __init__(self):
        self.current_os = os_detector.current_os

    def simulate_key_sequence(self, key_sequence: List[Tuple[str, str]]) -> bool:
        if not self.is_keyboard_available():
            logger.error("Keyboard simulation not available")
            return False
        try:
            for i, (key, action) in enumerate(key_sequence):
                logger.debug("Step %s: %s %s", i + 1, key, action)
                success = self._simulate_key_action(key, action)
                if not success:
                    logger.error("Failed at step %s: %s %s", i + 1, key, action)
                    return False
                delay = os_detector.get_os_specific_delay(action)
                time.sleep(delay)
            logger.info("Key sequence completed successfully")
            return True
        except Exception as e:
            logger.error("Key sequence simulation failed: %s", e)
            return False

    def _simulate_key_action(self, key: str, action: str) -> bool:
        try:
            if action == "press":
                return self._press_key(key)
            if action == "down":
                return self._key_down(key)
            if action == "up":
                return self._key_up(key)
            logger.error("Invalid key action: %s", action)
            return False
        except Exception as e:
            logger.error("Key action simulation failed: %s", e)
            return False

    def _key_down(self, key: str) -> bool:
        try:
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 0, 0)
                    return True
            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.press(pynput_key)
                return True
            return False
        except Exception as e:
            logger.error("Key down failed: %s", e)
            return False

    def _key_up(self, key: str) -> bool:
        try:
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                vk_code = self._get_windows_vk_code(key)
                if vk_code:
                    user32.keybd_event(vk_code, 0, 2, 0)
                    return True
            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key)
                keyboard_controller.release(pynput_key)
                return True
            return False
        except Exception as e:
            logger.error("Key up failed: %s", e)
            return False

    def _press_key(self, key_name: str) -> bool:
        try:
            if self.current_os == "Windows" and WINDOWS_API_AVAILABLE and user32:
                if key_name == "enter":
                    user32.keybd_event(0x0D, 0, 0, 0)
                    user32.keybd_event(0x0D, 0, 2, 0)
                    return True
            if PYNPUT_AVAILABLE and keyboard_controller:
                pynput_key = self._get_pynput_key(key_name)
                keyboard_controller.press(pynput_key)
                keyboard_controller.release(pynput_key)
                return True
            return False
        except Exception as e:
            logger.error("Single key press failed: %s", e)
            return False

    @staticmethod
    def _get_windows_vk_code(key: str) -> Optional[int]:
        vk_codes = {
            "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "option": 0x12, "cmd": 0x5B,
            "enter": 0x0D, "backspace": 0x08, "space": 0x20, "tab": 0x09,
            "escape": 0x1B, "esc": 0x1B,
            "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46,
            "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C,
            "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52,
            "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
            "y": 0x59, "z": 0x5A,
        }
        return vk_codes.get(key.lower())

    @staticmethod
    def _get_pynput_key(key_name: str):
        special_keys = {
            "enter": Key.enter, "backspace": Key.backspace, "space": Key.space,
            "tab": Key.tab, "escape": Key.esc, "esc": Key.esc,
            "ctrl": Key.ctrl, "shift": Key.shift, "alt": Key.alt, "option": Key.alt, "cmd": Key.cmd,
        }
        return special_keys.get(key_name, key_name)

    @staticmethod
    def is_keyboard_available() -> bool:
        return PYNPUT_AVAILABLE or WINDOWS_API_AVAILABLE


def create_key_simulator() -> KeySimulator:
    return KeySimulator()
