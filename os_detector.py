#!/usr/bin/env python3
"""
Operating System Detection Module
Centralized OS detection using enumeration to eliminate redundant detection across modules
"""

import platform
import logging
from enum import Enum
from typing import Optional

# Configure logging
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
        """Singleton pattern to ensure OS is detected only once"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detect_os()
        return cls._instance
    
    def _detect_os(self) -> None:
        """Detect the current operating system once"""
        if self._detected_os is None:
            system_name = platform.system()
            
            try:
                self._detected_os = OperatingSystem(system_name)
                logger.info(f"🖥️ Detected operating system: {self._detected_os.value}")
                
                # Log OS-specific information
                if self._detected_os == OperatingSystem.MACOS:
                    logger.info("🍎 macOS detected - will use Cmd+V for paste operations")
                elif self._detected_os == OperatingSystem.WINDOWS:
                    logger.info("🪟 Windows detected - will use Ctrl+V for paste operations")
                elif self._detected_os == OperatingSystem.LINUX:
                    logger.info("🐧 Linux detected - will use Ctrl+V for paste operations")
                else:
                    logger.warning(f"⚠️ Unsupported OS: {system_name} - using Linux defaults")
                    
            except ValueError:
                logger.warning(f"⚠️ Unknown OS: {system_name} - using Linux defaults")
                self._detected_os = OperatingSystem.LINUX
    
    @property
    def current_os(self) -> OperatingSystem:
        """Get the detected operating system"""
        if self._detected_os is None:
            self._detect_os()
        return self._detected_os or OperatingSystem.LINUX
    
    @property
    def is_macos(self) -> bool:
        """Check if current OS is macOS"""
        return self._detected_os == OperatingSystem.MACOS
    
    @property
    def is_windows(self) -> bool:
        """Check if current OS is Windows"""
        return self._detected_os == OperatingSystem.WINDOWS
    
    @property
    def is_linux(self) -> bool:
        """Check if current OS is Linux"""
        return self._detected_os == OperatingSystem.LINUX
    
    @property
    def modifier_key(self) -> str:
        """Get the appropriate modifier key for the current OS"""
        return "cmd" if self.is_macos else "ctrl"
    
    @property
    def paste_key_sequence(self) -> list:
        """Get the appropriate paste key sequence for the current OS"""
        if self.is_macos:
            return [("cmd", "down"), ("v", "press"), ("cmd", "up")]
        else:
            return [("ctrl", "down"), ("v", "press"), ("ctrl", "up")]
    
    @property
    def copy_key_sequence(self) -> list:
        """Get the appropriate copy key sequence for the current OS"""
        if self.is_macos:
            return [("cmd", "down"), ("c", "press"), ("cmd", "up")]
        else:
            return [("ctrl", "down"), ("c", "press"), ("ctrl", "up")]
    
    @property
    def select_all_key_sequence(self) -> list:
        """Get the appropriate select all key sequence for the current OS"""
        if self.is_macos:
            return [("cmd", "down"), ("a", "press"), ("cmd", "up")]
        else:
            return [("ctrl", "down"), ("a", "press"), ("ctrl", "up")]
    
    def get_os_specific_delay(self, action_type: str = "default") -> float:
        """Get OS-specific timing delays for reliable key simulation"""
        if self.is_macos:
            # macOS needs longer delays for reliable key simulation
            if action_type in ["down", "up"]:
                return 0.05  # 50ms for modifier keys
            else:
                return 0.03  # 30ms for regular keys
        else:
            # Windows/Linux can use shorter delays
            return 0.01  # 10ms


# Global instance for easy access
os_detector = OSDetector() 