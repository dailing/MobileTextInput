#!/usr/bin/env python3
"""
FastAPI backend for web key simulator.
Profiles and buttons; POST /simulate runs key_sequence on host.
Serves frontend build from backend/static when present.
"""

import logging
from pathlib import Path
from typing import List, Optional

import pyperclip
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from key_simulator import create_key_simulator
from os_detector import os_detector
from profile_store import (
    create_button_id,
    delete_profile as store_delete_profile,
    get_current_profile_id,
    get_profile,
    list_profiles as store_list_profiles,
    save_profile as store_save_profile,
    set_current_profile_id,
    _slug,
)
from window_lister import activate_window as lister_activate_window, list_windows
from mouse_controller import create_mouse_controller

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Web Key Simulator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

key_simulator = create_key_simulator()
mouse_ctrl = create_mouse_controller()


class KeyStep(BaseModel):
    key: str
    action: str


class ButtonIn(BaseModel):
    name: str
    classes: str = ""
    key_sequence: List[KeyStep]


class ButtonOut(BaseModel):
    id: str
    name: str
    classes: str
    key_sequence: List[List[str]]


class ProfileCreate(BaseModel):
    name: str


class ProfileUpdate(BaseModel):
    name: str
    buttons: List[dict]


class ProfileActive(BaseModel):
    profile_id: Optional[str] = None


class SimulateBody(BaseModel):
    button_id: Optional[str] = None
    key_sequence: Optional[List[List[str]]] = None


class WindowActivateBody(BaseModel):
    window_id: str


class PasteTextBody(BaseModel):
    text: str


class MouseMoveBody(BaseModel):
    dx: int
    dy: int


class MouseClickBody(BaseModel):
    button: str = "left"


def _button_to_out(b: dict) -> dict:
    kq = b.get("key_sequence") or []
    return {
        "id": b.get("id", ""),
        "name": b.get("name", ""),
        "classes": b.get("classes", ""),
        "key_sequence": [[s[0], s[1]] for s in kq] if kq else [],
    }


@app.get("/profiles")
def list_profiles():
    """List all profiles (id, name)."""
    return store_list_profiles()


@app.post("/profiles")
def create_profile(body: ProfileCreate):
    """Create a new profile with no buttons."""
    pid = _slug(body.name) or "profile"
    existing = get_profile(pid)
    if existing:
        raise HTTPException(status_code=400, detail="Profile id already exists")
    store_save_profile(pid, body.name, [])
    return {"id": pid, "name": body.name}


@app.get("/profiles/active")
def get_active():
    """Return current profile id and full profile if set."""
    pid = get_current_profile_id()
    if not pid:
        return {"profile_id": None, "profile": None}
    profile = get_profile(pid)
    if not profile:
        return {"profile_id": None, "profile": None}
    return {"profile_id": pid, "profile": profile}


@app.post("/profiles/active")
def set_active(body: ProfileActive):
    """Set the active profile (or clear if profile_id is null)."""
    set_current_profile_id(body.profile_id)
    return {"profile_id": body.profile_id}


@app.get("/profiles/{profile_id}")
def read_profile(profile_id: str):
    """Get one profile by id."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.put("/profiles/{profile_id}")
def update_profile(profile_id: str, body: ProfileUpdate):
    """Update profile name and buttons."""
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    buttons = []
    for b in body.buttons:
        bid = b.get("id") or create_button_id()
        kq = b.get("key_sequence") or []
        if not kq:
            keys_list = []
        elif isinstance(kq[0], (list, tuple)):
            keys_list = [[s[0], s[1]] for s in kq]
        else:
            keys_list = kq
        buttons.append({
            "id": bid,
            "name": b.get("name", ""),
            "classes": b.get("classes", ""),
            "key_sequence": keys_list,
        })
    store_save_profile(profile_id, body.name, buttons)
    return get_profile(profile_id)


@app.delete("/profiles/{profile_id}")
def remove_profile(profile_id: str):
    """Delete a profile."""
    if not get_profile(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    store_delete_profile(profile_id)
    return {"ok": True}


@app.get("/buttons")
def get_buttons():
    """Return buttons of the active profile."""
    pid = get_current_profile_id()
    if not pid:
        return {"buttons": []}
    profile = get_profile(pid)
    if not profile:
        return {"buttons": []}
    return {"buttons": [_button_to_out(b) for b in profile.get("buttons", [])]}


@app.get("/windows")
def get_windows():
    """List all visible windows (id, title, app)."""
    return {"windows": list_windows()}


@app.post("/windows/activate")
def activate_window_route(body: WindowActivateBody):
    """Bring the given window to front."""
    ok = lister_activate_window(body.window_id)
    return {"success": ok}


@app.post("/simulate")
def simulate(body: SimulateBody):
    """Run key sequence: by button_id from active profile, or raw key_sequence."""
    if body.button_id:
        pid = get_current_profile_id()
        if not pid:
            raise HTTPException(status_code=400, detail="No active profile")
        profile = get_profile(pid)
        if not profile:
            raise HTTPException(status_code=400, detail="Active profile not found")
        buttons = profile.get("buttons", [])
        btn = next((b for b in buttons if b.get("id") == body.button_id), None)
        if not btn:
            raise HTTPException(status_code=404, detail="Button not found")
        key_sequence = btn.get("key_sequence") or []
    elif body.key_sequence:
        key_sequence = body.key_sequence
    else:
        raise HTTPException(status_code=400, detail="Provide button_id or key_sequence")
    if not key_sequence:
        return {"success": True}
    seq = [(s[0], s[1]) for s in key_sequence]
    success = key_simulator.simulate_key_sequence(seq)
    return {"success": success}


@app.post("/paste-text")
def paste_text(body: PasteTextBody):
    """Copy text to clipboard and simulate paste keystroke."""
    if not body.text:
        return {"success": True}
    try:
        pyperclip.copy(body.text)
        paste_seq = os_detector.paste_key_sequence
        success = key_simulator.simulate_key_sequence(paste_seq)
        return {"success": success}
    except Exception as e:
        logger.error("paste-text failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mouse/move")
def mouse_move(body: MouseMoveBody):
    """Move mouse by relative offset."""
    success = mouse_ctrl.move_relative(body.dx, body.dy)
    return {"success": success}


@app.post("/mouse/click")
def mouse_click(body: MouseClickBody):
    """Simulate mouse click (left, right, or middle)."""
    if body.button not in ("left", "right", "middle"):
        raise HTTPException(status_code=400, detail="Invalid button")
    success = mouse_ctrl.click(body.button)
    return {"success": success}


_static_dir = Path(__file__).parent / "static"
if _static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")


def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)


if __name__ == "__main__":
    main()
