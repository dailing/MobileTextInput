const base = ''

async function request(path, options = {}) {
  const res = await fetch(base + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.message || String(err))
  }
  return res.json().catch(() => ({}))
}

export async function listProfiles() {
  return request('/profiles')
}

export async function getProfile(id) {
  return request(`/profiles/${id}`)
}

export async function createProfile(name) {
  return request('/profiles', { method: 'POST', body: JSON.stringify({ name }) })
}

export async function updateProfile(id, data) {
  return request(`/profiles/${id}`, { method: 'PUT', body: JSON.stringify(data) })
}

export async function deleteProfile(id) {
  return request(`/profiles/${id}`, { method: 'DELETE' })
}

export async function getActive() {
  return request('/profiles/active')
}

export async function setActive(profileId) {
  return request('/profiles/active', { method: 'POST', body: JSON.stringify({ profile_id: profileId }) })
}

export async function getButtons() {
  return request('/buttons')
}

export async function simulate(buttonId) {
  return request('/simulate', { method: 'POST', body: JSON.stringify({ button_id: buttonId }) })
}

export async function getWindows() {
  return request('/windows')
}

export async function activateWindow(windowId) {
  return request('/windows/activate', { method: 'POST', body: JSON.stringify({ window_id: windowId }) })
}

export async function pasteText(text) {
  return request('/paste-text', { method: 'POST', body: JSON.stringify({ text }) })
}

export async function mouseMove(dx, dy) {
  return request('/mouse/move', { method: 'POST', body: JSON.stringify({ dx, dy }) })
}

export async function mouseClick(button = 'left') {
  return request('/mouse/click', { method: 'POST', body: JSON.stringify({ button }) })
}
