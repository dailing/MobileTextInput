"""
Settings storage: single JSON file for global application settings.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path.home() / ".webinput_backups" / "settings.json"

DEFAULT_SETTINGS = {
    "touchpad_sensitivity": 1.5
}


def _ensure_dir() -> None:
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> dict:
    """Load settings from disk, or return defaults if file doesn't exist."""
    _ensure_dir()
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        result = DEFAULT_SETTINGS.copy()
        result.update(data)
        return result
    except Exception as e:
        logger.error("Failed to load settings: %s", e)
        return DEFAULT_SETTINGS.copy()


def update_settings(settings: dict) -> bool:
    """Update settings (partial update supported). Merges with existing settings."""
    _ensure_dir()
    current = get_settings()
    current.update(settings)
    try:
        SETTINGS_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("Failed to save settings: %s", e)
        return False
