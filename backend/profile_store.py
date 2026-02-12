"""
Profile storage: one JSON file per profile in a directory.
Profiles hold named buttons with key_sequence; current profile is stored separately.
"""

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

PROFILES_DIR = Path.home() / ".webinput_backups" / "profiles"
CURRENT_FILE = Path.home() / ".webinput_backups" / "current_profile.json"


def _slug(s: str) -> str:
    """Safe filename slug from profile name."""
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[-\s]+", "_", s).strip("_").lower() or "profile"


def _ensure_dir() -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.parent.mkdir(parents=True, exist_ok=True)


def list_profiles() -> List[dict]:
    """List all profiles (id and name) by scanning JSON files in PROFILES_DIR."""
    _ensure_dir()
    out = []
    for p in PROFILES_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": data.get("id", p.stem), "name": data.get("name", p.stem)})
        except Exception as e:
            logger.warning("Skip invalid profile %s: %s", p.name, e)
    return out


def get_profile(profile_id: str) -> Optional[dict]:
    """Load one profile by id (filename without .json)."""
    _ensure_dir()
    path = PROFILES_DIR / f"{profile_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error("Failed to load profile %s: %s", profile_id, e)
        return None


def save_profile(profile_id: str, name: str, buttons: List[dict]) -> bool:
    """Create or update a profile. Buttons must have id, name, classes, key_sequence."""
    _ensure_dir()
    path = PROFILES_DIR / f"{profile_id}.json"
    data = {"id": profile_id, "name": name, "buttons": buttons}
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("Failed to save profile %s: %s", profile_id, e)
        return False


def delete_profile(profile_id: str) -> bool:
    """Remove a profile file. Does not clear current_profile if it was active."""
    _ensure_dir()
    path = PROFILES_DIR / f"{profile_id}.json"
    try:
        if path.exists():
            path.unlink()
            return True
        return False
    except Exception as e:
        logger.error("Failed to delete profile %s: %s", profile_id, e)
        return False


def get_current_profile_id() -> Optional[str]:
    """Return the currently active profile id, or None."""
    if not CURRENT_FILE.exists():
        return None
    try:
        data = json.loads(CURRENT_FILE.read_text(encoding="utf-8"))
        return data.get("profile_id")
    except Exception:
        return None


def set_current_profile_id(profile_id: Optional[str]) -> bool:
    """Set the active profile (None to clear)."""
    _ensure_dir()
    try:
        if profile_id is None:
            if CURRENT_FILE.exists():
                CURRENT_FILE.unlink()
            return True
        CURRENT_FILE.write_text(json.dumps({"profile_id": profile_id}), encoding="utf-8")
        return True
    except Exception as e:
        logger.error("Failed to set current profile: %s", e)
        return False


def create_button_id() -> str:
    """Generate a new unique button id."""
    return str(uuid.uuid4())
