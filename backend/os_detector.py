#!/usr/bin/env python3
"""
Operating System Detection Module
Centralized OS detection using enumeration to eliminate redundant detection across modules
"""

import platform
import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class OperatingSystem(Enum):
    """Enumeration for supported operating systems"""
    WINDOWS = "Windows"
    MACOS = "Darwin"
    LINUX = "Linux"
    UNKNOWN = "Unknown"


class OSDetector:
    """Centralized operating system detection and management"""

    _instance: Optional['OSDetector'] = None
    _detected_os: Optional[OperatingSystem] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detect_os()
        return cls._instance

    def _detect_os(self) -> None:
        if self._detected_os is None:
            system_name = platform.system()
            try:
                self._detected_os = OperatingSystem(system_name)
                logger.info("Detected operating system: %s", self._detected_os.value)
                if self._detected_os == OperatingSystem.MACOS:
                    logger.info("macOS detected - will use Cmd+V for paste operations")
                elif self._detected_os == OperatingSystem.WINDOWS:
                    logger.info("Windows detected - will use Ctrl+V for paste operations")
                elif self._detected_os == OperatingSystem.LINUX:
                    logger.info("Linux detected - will use Ctrl+V for paste operations")
                else:
                    logger.warning("Unsupported OS: %s - using Linux defaults", system_name)
            except ValueError:
                logger.warning("Unknown OS: %s - using Linux defaults", system_name)
                self._detected_os = OperatingSystem.LINUX

    @property
    def current_os(self) -> OperatingSystem:
        if self._detected_os is None:
            self._detect_os()
        return self._detected_os or OperatingSystem.LINUX

    @property
    def is_macos(self) -> bool:
        return self._detected_os == OperatingSystem.MACOS

    @property
    def is_windows(self) -> bool:
        return self._detected_os == OperatingSystem.WINDOWS

    @property
    def is_linux(self) -> bool:
        return self._detected_os == OperatingSystem.LINUX

    @property
    def modifier_key(self) -> str:
        return "cmd" if self.is_macos else "ctrl"

    @property
    def paste_key_sequence(self) -> list:
        if self.is_macos:
            return [("cmd", "down"), ("v", "press"), ("cmd", "up")]
        return [("ctrl", "down"), ("v", "press"), ("ctrl", "up")]

    @property
    def copy_key_sequence(self) -> list:
        if self.is_macos:
            return [("cmd", "down"), ("c", "press"), ("cmd", "up")]
        return [("ctrl", "down"), ("c", "press"), ("ctrl", "up")]

    @property
    def select_all_key_sequence(self) -> list:
        if self.is_macos:
            return [("cmd", "down"), ("a", "press"), ("cmd", "up")]
        return [("ctrl", "down"), ("a", "press"), ("ctrl", "up")]

    def get_os_specific_delay(self, action_type: str = "default") -> float:
        if self.is_macos:
            return 0.05 if action_type in ["down", "up"] else 0.03
        return 0.01


os_detector = OSDetector()
