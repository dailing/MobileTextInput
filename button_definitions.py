from typing import List, Tuple, Callable, NamedTuple, Optional
import pyperclip
import logging
from nicegui import app

# Configure logging
logger = logging.getLogger(__name__)

# Storage key for text input
storage_key = "shared_text"


class ButtonConfig(NamedTuple):
    """Configuration for a single button in the UI"""

    name: str  # Display name of the button
    classes: str  # Additional CSS classes for styling
    # Function to run before key press
    pre_action: Optional[Callable[[], bool]]
    key_sequence: List[Tuple[str, str]]  # List of (key, action) pairs


def copy_to_clipboard() -> bool:
    """Copy current text to clipboard and clear input

    Returns:
        bool: True if copy was successful, False otherwise
    """
    current_text = app.storage.general.get(storage_key, "")
    text = current_text.strip() if current_text else ""

    if not text:
        logger.info("No text to copy")
        return False

    try:
        pyperclip.copy(text)
        preview = text[:50] + ("..." if len(text) > 50 else "")
        logger.info(f"📋 Text copied to clipboard: '{preview}'")
        # Clear the input after successful copy
        app.storage.general[storage_key] = ""
        return True
    except Exception as e:
        logger.error(f"❌ Failed to copy to clipboard: {e}")
        return False


def clear_text() -> bool:
    """Clear the text area

    Returns:
        bool: Always returns True
    """
    app.storage.general[storage_key] = ""
    return True


def copy_button() -> ButtonConfig:
    """Configuration for the copy button"""
    return ButtonConfig(
        name="Copy",
        classes="",
        pre_action=copy_to_clipboard,  # Run copy function before key sequence
        key_sequence=[],  # No key sequence needed, just copy to clipboard
    )


def paste_button() -> ButtonConfig:
    """Configuration for the paste button"""
    return ButtonConfig(
        name="Paste",
        classes="",
        pre_action=None,  # No pre-action needed for paste
        key_sequence=[("ctrl", "down"), ("v", "press"), ("ctrl", "up")],
    )


def copy_paste_enter_button() -> ButtonConfig:
    """Configuration for the copy, paste and enter button"""
    return ButtonConfig(
        name="Copy, Paste & Enter",
        classes="",
        pre_action=copy_to_clipboard,  # Copy text before pasting
        key_sequence=[
            ("ctrl", "down"),
            ("v", "press"),
            ("ctrl", "up"),
            ("enter", "press"),
        ],
    )


def accept_button() -> ButtonConfig:
    """Configuration for the accept button"""
    return ButtonConfig(
        name="Accept",
        classes="",
        pre_action=None,
        key_sequence=[
            ("ctrl", "down"),
            ("enter", "press"),
            ("ctrl", "up"),
        ],
    )


def new_button() -> ButtonConfig:
    """Configuration for the new button"""
    return ButtonConfig(
        name="New",
        classes="",
        pre_action=None,
        key_sequence=[
            ("ctrl", "down"),
            ("n", "press"),
            ("ctrl", "up"),
        ],
    )


def stop_button() -> ButtonConfig:
    """Configuration for the stop button"""
    return ButtonConfig(
        name="Stop",
        classes="bg-red-500",
        pre_action=None,
        key_sequence=[
            ("ctrl", "down"),
            ("shift", "down"),
            ("backspace", "press"),
            ("shift", "up"),
            ("ctrl", "up"),
        ],
    )


def reject_button() -> ButtonConfig:
    """Configuration for the reject button"""
    return ButtonConfig(
        name="Reject",
        classes="bg-red-500",
        pre_action=None,
        key_sequence=[
            ("ctrl", "down"),
            ("backspace", "press"),
            ("ctrl", "up"),
        ],
    )


def clear_button() -> ButtonConfig:
    """Configuration for the clear button"""
    return ButtonConfig(
        name="Clear",
        classes="bg-red-500",
        pre_action=clear_text,
        key_sequence=[],  # No key sequence needed
    )


def copy_paste_button() -> ButtonConfig:
    """Configuration for the copy and paste button"""
    return ButtonConfig(
        name="Copy & Paste",
        classes="",
        pre_action=copy_to_clipboard,
        key_sequence=[
            ("ctrl", "down"),
            ("v", "press"),
            ("ctrl", "up"),
        ],
    )


def enter_button() -> ButtonConfig:
    """Configuration for the enter button"""
    return ButtonConfig(
        name="Enter",
        classes="",
        pre_action=None,
        key_sequence=[("enter", "press")],
    )


# List of all available buttons in desired order
AVAILABLE_BUTTONS = [
    copy_paste_enter_button,  # Combined action button first
    accept_button,
    new_button,
    stop_button,
    reject_button,
    clear_button,
    copy_button,
    paste_button,
    copy_paste_button,
    enter_button,
]
