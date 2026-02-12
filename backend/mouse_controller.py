#!/usr/bin/env python3
"""
Mouse Controller Module
Provides cross-platform mouse simulation functionality
"""

from typing import Literal
from os_detector import os_detector
from loguru import logger

try:
    from pynput.mouse import Button, Controller
    mouse_controller = Controller()
    PYNPUT_MOUSE_AVAILABLE = True
    logger.info("pynput mouse simulation library loaded")
except ImportError:
    PYNPUT_MOUSE_AVAILABLE = False
    mouse_controller = None
    logger.warning("pynput mouse not available - mouse simulation disabled")


class MouseController:
    """Mouse simulation handler for move and click operations"""

    def __init__(self):
        self.current_os = os_detector.current_os

    @staticmethod
    def is_available() -> bool:
        return PYNPUT_MOUSE_AVAILABLE

    def move_relative(self, dx: int, dy: int) -> bool:
        """Move mouse by relative offset (dx, dy)"""
        if not PYNPUT_MOUSE_AVAILABLE or not mouse_controller:
            logger.error("Mouse simulation not available")
            return False
        try:
            mouse_controller.move(dx, dy)
            return True
        except Exception as e:
            logger.error("Mouse move failed: %s", e)
            return False

    def click(self, button: Literal["left", "right", "middle"] = "left") -> bool:
        """Simulate mouse click"""
        if not PYNPUT_MOUSE_AVAILABLE or not mouse_controller:
            logger.error("Mouse simulation not available")
            return False
        try:
            btn = {"left": Button.left, "right": Button.right, "middle": Button.middle}.get(button, Button.left)
            mouse_controller.click(btn)
            return True
        except Exception as e:
            logger.error("Mouse click failed: %s", e)
            return False


def create_mouse_controller() -> MouseController:
    return MouseController()
