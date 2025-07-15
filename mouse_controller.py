#!/usr/bin/env python3
"""
Mouse Controller Module
Provides cross-platform mouse movement simulation with touchpad-style control
"""

import platform
import logging
import threading
from typing import Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Import mouse simulation library
try:
    from pynput.mouse import Controller as MouseController

    mouse_controller = MouseController()
    PYNPUT_AVAILABLE = True
    logger.info("✅ pynput mouse controller loaded")
except ImportError:
    PYNPUT_AVAILABLE = False
    mouse_controller = None
    logger.warning("⚠️ pynput not available - mouse control disabled")

# OS detection
CURRENT_OS = platform.system()
IS_MACOS = CURRENT_OS == "Darwin"
IS_WINDOWS = CURRENT_OS == "Windows"
IS_LINUX = CURRENT_OS == "Linux"


class MouseControllerManager:
    """
    Touchpad-style mouse controller with direct position mapping
    """

    def __init__(self):
        self.current_os = platform.system()
        self._last_position = (0, 0)
        self._sensitivity = (
            100  # Pixels to move when joystick is at max (reduced from 500)
        )
        self._movement_lock = threading.Lock()

    def is_available(self) -> bool:
        """Check if mouse control is available"""
        return PYNPUT_AVAILABLE

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        if not self.is_available():
            return (0, 0)
        return mouse_controller.position

    def move_mouse(self, x: float, y: float) -> bool:
        """
        Move mouse using touchpad-style direct position mapping

        Args:
            x: Joystick x position (-1.0 to 1.0)
            y: Joystick y position (-1.0 to 1.0)

        Returns:
            bool: True if command accepted, False otherwise
        """
        if not self.is_available():
            logger.error("❌ Mouse control not available")
            return False

        # Small deadzone to prevent tiny movements
        if abs(x) < 0.05 and abs(y) < 0.05:
            return True

        with self._movement_lock:
            # Get current position
            current_x, current_y = mouse_controller.position

            # Calculate delta based on joystick position
            # Invert x-axis (joystick left should move mouse right)
            delta_x = int(-x * self._sensitivity)
            # Invert y-axis (joystick up should move mouse up)
            delta_y = int(-y * self._sensitivity)

            # Apply movement directly
            try:
                new_x = current_x + delta_x
                new_y = current_y + delta_y

                # Log the movement
                pos_from = f"{current_x},{current_y}"
                pos_to = f"{new_x},{new_y}"
                logger.info(f"Mouse: {pos_from} to {pos_to}")

                # Move the mouse
                mouse_controller.position = (new_x, new_y)
                return True
            except Exception as e:
                logger.error(f"❌ Mouse movement error: {e}")
                return False

    def stop_movement(self) -> bool:
        """
        Stop mouse movement - not needed for touchpad mode
        but kept for API compatibility

        Returns:
            bool: Always True
        """
        return True


def create_mouse_controller() -> MouseControllerManager:
    """Factory function to create a MouseControllerManager instance"""
    return MouseControllerManager()
