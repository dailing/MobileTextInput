#!/usr/bin/env python3
"""
Mouse Controller Module
Provides cross-platform mouse movement simulation with touchpad-style control
"""

import logging
import threading
from typing import Tuple, Optional
from os_detector import os_detector

# Configure logging
logger = logging.getLogger(__name__)

# Import mouse simulation library
try:
    from pynput.mouse import Controller as MouseController, Button

    mouse_controller = MouseController()
    PYNPUT_AVAILABLE = True
    logger.info("✅ pynput mouse controller loaded")
except ImportError:
    PYNPUT_AVAILABLE = False
    mouse_controller = None
    logger.warning("⚠️ pynput not available - mouse control disabled")

# OS detection is now handled by os_detector module


class MouseControllerManager:
    """
    Touchpad-style mouse controller with event-based control system
    """

    def __init__(self):
        self.current_os = os_detector.current_os
        self._initial_position: Optional[Tuple[int, int]] = None
        self._sensitivity = 400  # Pixels to move when joystick is at max
        self._movement_lock = threading.Lock()

    def is_available(self) -> bool:
        """Check if mouse control is available"""
        return PYNPUT_AVAILABLE

    def get_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        if not self.is_available():
            return (0, 0)
        return mouse_controller.position

    def click_left_button(self) -> bool:
        """
        Simulate left mouse button click
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("❌ Mouse control not available")
            return False

        try:
            mouse_controller.click(Button.left)
            logger.info("Left mouse button clicked")
            return True
        except Exception as e:
            logger.error(f"❌ Error clicking left mouse button: {e}")
            return False

    def click_right_button(self) -> bool:
        """
        Simulate right mouse button click
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("❌ Mouse control not available")
            return False

        try:
            mouse_controller.click(Button.right)
            logger.info("Right mouse button clicked")
            return True
        except Exception as e:
            logger.error(f"❌ Error clicking right mouse button: {e}")
            return False

    def on_start(self) -> bool:
        """
        Handle joystick start event - record initial mouse position
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("❌ Mouse control not available")
            return False

        with self._movement_lock:
            try:
                self._initial_position = mouse_controller.position
                logger.info(f"Mouse control started - initial position: {self._initial_position}")
                return True
            except Exception as e:
                logger.error(f"❌ Error recording initial mouse position: {e}")
                return False

    def on_move(self, x: float, y: float) -> bool:
        """
        Handle joystick move event - update mouse position relative to initial position

        Args:
            x: Joystick x position (-1.0 to 1.0)
            y: Joystick y position (-1.0 to 1.0)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("❌ Mouse control not available")
            return False

        if self._initial_position is None:
            logger.warning("⚠️ Mouse control not started - call on_start() first")
            return False

        # Small deadzone to prevent tiny movements
        if abs(x) < 0.05 and abs(y) < 0.05:
            return True

        with self._movement_lock:
            try:
                # Calculate new position relative to initial position
                delta_x = int(x * self._sensitivity)
                delta_y = int(-y * self._sensitivity)  # Invert y-axis
                
                new_x = self._initial_position[0] + delta_x
                new_y = self._initial_position[1] + delta_y

                # Log the movement
                pos_from = f"{mouse_controller.position[0]},{mouse_controller.position[1]}"
                pos_to = f"{new_x},{new_y}"
                logger.info(f"Mouse: {pos_from} to {pos_to} (joystick: {x:.3f}, {y:.3f})")

                # Move the mouse
                mouse_controller.position = (new_x, new_y)
                return True
            except Exception as e:
                logger.error(f"❌ Mouse movement error: {e}")
                return False

    def on_end(self) -> bool:
        """
        Handle joystick end event - clear initial position
        
        Returns:
            bool: True if successful, False otherwise
        """
        with self._movement_lock:
            self._initial_position = None
            logger.info("Mouse control ended - initial position cleared")
            return True

    def move_mouse(self, x: float, y: float) -> bool:
        """
        Legacy method for backward compatibility
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
    """Factory function to create a MouseControllerManager instance
    
    Note: OS detection is now handled centrally by os_detector module
    """
    return MouseControllerManager()
