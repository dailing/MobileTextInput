# Web Key Simulator – Architecture

This document describes the frontend and backend of the Web Key Simulator only. The `legacy/` and `voice/` directories are out of scope.

## High-Level Architecture

- **Backend**: FastAPI server (port 8080). Manages profiles and buttons, stores them on disk, and runs key sequences on the host via pynput (or Windows API on Windows).
- **Frontend**: Vue 3 SPA (Vite). Two main views: Panel (run buttons of the active profile) and Editor (manage profiles and button key sequences). Build output goes to `backend/static/` and can be served by the same server.
- **Interaction**: Frontend calls backend REST API; side effects on the host are `POST /simulate` (keyboard simulation), `POST /paste-text` (clipboard + paste), and `POST /mouse/*` (mouse control).

---

## Data Structures

### Profile (backend storage and API)

- **File**: `~/.webinput_backups/profiles/{profile_id}.json`
- **Shape**:
  - `id`: string (slug from name, used as filename)
  - `name`: string (display name)
  - `buttons`: array of Button objects

### Button

- **Fields**: `id` (UUID), `name`, `classes` (CSS for Panel), `key_sequence`
- **key_sequence** (internal/API): array of steps. Each step is either:
  - **Object form** (frontend Editor): `{ key, action, _uiMode? }` where `_uiMode` is `'special'|'char'` and not sent to API
  - **Wire form** (API and key_simulator): list of pairs `[key, action]`, e.g. `[["ctrl", "down"], ["a", "press"], ["ctrl", "up"]]`

### Key step

- **key**: string – character (e.g. `"a"`) or special key name: `cmd`, `ctrl`, `shift`, `alt`, `option`, `enter`, `backspace`, `space`, `tab`, `escape`
- **action**: `"down"` | `"press"` | `"up"`

### Current profile

- **File**: `~/.webinput_backups/current_profile.json`  
- **Content**: `{ "profile_id": "<id>" }` or file missing/empty means no active profile.

### API request/response shapes (relevant)

- **GET /profiles** → `[{ id, name }, ...]`
- **GET /profiles/active** → `{ profile_id, profile }` (profile is full object or null)
- **GET /profiles/{id}** → full profile `{ id, name, buttons }`
- **PUT /profiles/{id}** body: `{ name, buttons }` with buttons having `id`, `name`, `classes`, `key_sequence` as array of `[key, action]`
- **GET /buttons** → `{ buttons }` with each button `{ id, name, classes, key_sequence: [[key, action], ...] }`
- **POST /simulate** body: `{ button_id }` or `{ key_sequence }` → `{ success }`
- **POST /paste-text** body: `{ text }` → `{ success }` (copies text to clipboard, simulates paste)
- **POST /mouse/move** body: `{ dx, dy }` → `{ success }` (move mouse by relative offset)
- **POST /mouse/click** body: `{ button }` → `{ success }` (simulate left/right/middle click)

---

## Backend

### Stack and entrypoint

- **Runtime**: Python (uv), FastAPI, uvicorn.
- **Entry**: `backend/main.py` – `main()` runs `uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)`.
- **Static**: If `backend/static/` exists (e.g. after `frontend` build), it is mounted at `/` with `html=True` (SPA fallback). API routes are registered first so they take precedence.

### Key modules

| Module | Role |
|--------|------|
| `main.py` | FastAPI app, CORS, all REST routes, static mount. |
| `profile_store.py` | Persistence: list/get/save/delete profiles, get/set current profile id, create button id. Uses `~/.webinput_backups/`. |
| `key_simulator.py` | Runs key sequences on the host: pynput (macOS/Linux) or Windows `user32.keybd_event`. |
| `os_detector.py` | Singleton OS detection (Windows/Mac/Linux), modifier key names, and per-OS delay between key actions. |

|| `mouse_controller.py` | Mouse simulation: relative movement and left/right/middle clicks via pynput. |
|| `window_lister.py` | Lists visible windows and activates windows by ID (macOS AppleScript / Linux wmctrl). |

### Key classes and functions (backend)

- **main.py**
  - Pydantic: `KeyStep`, `ButtonIn`, `ButtonOut`, `ProfileCreate`, `ProfileUpdate`, `ProfileActive`, `SimulateBody`, `PasteTextBody`, `MouseMoveBody`, `MouseClickBody`, `WindowActivateBody`.
  - Routes: `list_profiles`, `create_profile`, `get_active`, `set_active`, `read_profile`, `update_profile`, `remove_profile`, `get_buttons`, `simulate`, `paste_text`, `mouse_move`, `mouse_click`, `get_windows`, `activate_window_route`.
  - Helper: `_button_to_out(b)` – normalizes a stored button to `{ id, name, classes, key_sequence: [[k,a],...] }`.
- **profile_store.py**
  - Paths: `PROFILES_DIR`, `CURRENT_FILE`.
  - Public: `list_profiles()`, `get_profile(id)`, `save_profile(id, name, buttons)`, `delete_profile(id)`, `get_current_profile_id()`, `set_current_profile_id(id)`, `create_button_id()`.
  - Internal: `_slug(name)` (profile id from name), `_ensure_dir()`.
- **key_simulator.py**
  - `KeySimulator`: `simulate_key_sequence(key_sequence: List[Tuple[str,str]]) -> bool`; internally `_simulate_key_action`, `_key_down`, `_key_up`, `_press_key`; key lookup `_get_pynput_key`, `_get_windows_vk_code`.
  - `create_key_simulator()` → singleton-style usage in main.
- **os_detector.py**
  - `OSDetector` singleton: `current_os`, `is_macos`, `is_windows`, `is_linux`, `modifier_key`, `paste_key_sequence`, `copy_key_sequence`, `select_all_key_sequence`, `get_os_specific_delay(action_type)`.
- **mouse_controller.py**
  - `MouseController`: `move_relative(dx, dy) -> bool`, `click(button) -> bool`, `is_available() -> bool`.
  - `create_mouse_controller()` → factory for main.py usage.

### API summary (backend)

| Method | Path | Purpose |
|--------|------|--------|
| GET | /profiles | List all profiles (id, name) |
| POST | /profiles | Create profile (body: `{ name }`) |
| GET | /profiles/active | Current profile id and full profile |
| POST | /profiles/active | Set current profile (body: `{ profile_id }`) |
| GET | /profiles/{id} | Get one profile |
| PUT | /profiles/{id} | Update profile (body: `{ name, buttons }`) |
| DELETE | /profiles/{id} | Delete profile |
| GET | /buttons | Buttons of active profile |
| POST | /simulate | Run key sequence by `button_id` or raw `key_sequence` |
| POST | /paste-text | Copy text to clipboard and simulate paste keystroke |
| GET | /windows | List visible windows (id, title, app) |
| POST | /windows/activate | Bring window to front (body: `{ window_id }`) |
| POST | /mouse/move | Move mouse by relative offset (body: `{ dx, dy }`) |
| POST | /mouse/click | Simulate mouse click (body: `{ button }`: left/right/middle) |

---

## Frontend

### Stack and entrypoint

- **Stack**: Vue 3 (Composition API), Vue Router, Vite.
- **Entry**: `frontend/src/main.js` – creates app, uses router, mounts `#app`.
- **Build**: `npm run build` / `vite build` → `outDir: '../backend/static'`; dev server port 5173 with proxy to backend 8080 for `/profiles`, `/buttons`, `/simulate`.

### Key files

| File | Role |
|------|------|
| `src/App.vue` | Shell: nav (Panel / Editor), `<router-view />`. |
| `src/router/index.js` | Routes: `/` → Panel, `/edit` → Editor. |
| `src/api.js` | All backend calls: `listProfiles`, `getProfile`, `createProfile`, `updateProfile`, `deleteProfile`, `getActive`, `setActive`, `getButtons`, `simulate(buttonId)`, `pasteText(text)`, `getWindows`, `activateWindow(windowId)`, `mouseMove(dx, dy)`, `mouseClick(button)`. Uses `fetch(base + path)` with JSON. |
| `src/constants.js` | `SPECIAL_KEYS`, `KEY_ACTIONS`, `isSpecialKey`, `defaultActionForKey`. |
| `src/views/Panel.vue` | Shows active profile buttons, text input for paste, touchpad for mouse control, and window list. Click button → `simulate(btn.id)`; text input → `pasteText(text)`; touchpad → `mouseMove(dx, dy)` + click buttons → `mouseClick(button)`; window list → `activateWindow(id)`. |
| `src/views/Editor.vue` | Profile list (activate, edit, remove), create profile, edit selected profile (name, buttons with key_sequence steps); save via `updateProfile`. |

### Key flows (frontend)

- **Panel**: On mount (and when activeId changes), `getActive()` then `getButtons()` and `getWindows()`; render buttons, touchpad, and window list. Button click → `simulate(btn.id)`; text input "Send & Paste" → `pasteText(text)`; touchpad drag → `mouseMove(dx, dy)`; touchpad buttons (Left/Middle/Right) → `mouseClick(button)`; window item click → `activateWindow(id)`.
- **Editor**: On mount, `listProfiles()` and `getActive()`; select profile → `getProfile(id)`, normalize steps to `{ key, action, _uiMode }`; activate → `setActive(id)`; save → build payload with `key_sequence` as `[[key, action], ...]` (strip `_uiMode`), then `updateProfile(id, payload)`.

---

## How Backend and Frontend Interact

1. **Panel**
   - Load: GET /profiles/active, GET /buttons, GET /windows.
   - Button action: POST /simulate with `{ button_id }`. Backend resolves button from active profile and runs `key_simulator.simulate_key_sequence(...)`.
   - Touchpad: POST /mouse/move with `{ dx, dy }` on drag; POST /mouse/click with `{ button }` on button press. Backend runs `mouse_controller.move_relative(...)` or `mouse_controller.click(...)`.
   - Window: POST /windows/activate with `{ window_id }`. Backend brings window to front via `window_lister.activate_window(...)`.
2. **Editor**
   - List/activate: GET /profiles, GET /profiles/active, POST /profiles/active, GET /profiles/{id}.
   - CRUD: POST /profiles, PUT /profiles/{id}, DELETE /profiles/{id}. PUT sends `key_sequence` as array of `[key, action]`; backend stores and returns same shape.
3. **Key simulation path**: Frontend never sends raw key_sequence for the Panel (only button_id). Backend loads active profile → finds button → gets key_sequence → KeySimulator runs down/press/up with OS-specific delays.
4. **Text paste path**: Frontend sends text via POST /paste-text. Backend copies text to system clipboard (pyperclip), then simulates OS-specific paste keystroke (Cmd+V on macOS, Ctrl+V on Windows/Linux) via KeySimulator.
5. **Mouse control path**: Frontend touchpad tracks touch/mouse drag and sends relative deltas via POST /mouse/move. Click buttons send POST /mouse/click. Backend uses pynput mouse controller.
6. **Window activation path**: Frontend lists windows via GET /windows, user clicks one, POST /windows/activate brings it to front.

---

## Directory Layout (relevant)

```
backend/
  main.py           # FastAPI app, routes, static mount
  profile_store.py  # Profile and current-profile persistence
  key_simulator.py  # Host key simulation (pynput / Windows)
  os_detector.py    # OS detection and delays
  static/           # Frontend build output (gitignored)

frontend/
  src/
    main.js
    App.vue
    api.js          # Backend API wrappers
    constants.js    # SPECIAL_KEYS, KEY_ACTIONS
    router/index.js
    views/Panel.vue
    views/Editor.vue
  index.html
  vite.config.js   # outDir ../backend/static, dev proxy to 8080
```

---

## Quick Reference for Changes

- **Add an API endpoint**: Add route in `backend/main.py`; add corresponding function in `frontend/src/api.js`; use in a view.
- **Change profile/button shape**: Update `profile_store` read/write and `main.py` Pydantic models and `_button_to_out`; update Editor payload and any Panel display.
- **Add a special key**: Add to `frontend/src/constants.js` `SPECIAL_KEYS`; add mapping in `backend/key_simulator.py` (`_get_pynput_key` and, if needed, `_get_windows_vk_code`).
- **Change key actions**: Adjust `KEY_ACTIONS` in constants and backend `KeySimulator._simulate_key_action` if new actions are added.
