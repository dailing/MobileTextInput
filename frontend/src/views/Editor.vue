<template>
  <div class="editor">
    <section class="section">
      <h2>Profiles</h2>
      <div class="profile-list">
        <div v-for="p in profiles" :key="p.id" class="profile-row">
          <span class="profile-name">{{ p.name }}</span>
          <button type="button" class="btn small" :class="{ active: activeId === p.id }" @click="activate(p.id)">Activate</button>
          <button type="button" class="btn small" :class="{ selected: selectedId === p.id }" @click="select(p.id)">Edit</button>
          <button type="button" class="btn small danger" @click="removeProfile(p.id)">Remove</button>
        </div>
      </div>
      <div class="row">
        <input v-model="newProfileName" placeholder="New profile name" class="input" />
        <button type="button" class="btn" @click="addProfile">Add profile</button>
      </div>
    </section>

    <section v-if="selectedId" class="section">
      <h2>Edit: {{ currentProfile?.name ?? selectedId }}</h2>
      <div class="row">
        <label>Profile name</label>
        <input v-model="currentProfile.name" class="input" />
      </div>
      <h3>Buttons</h3>
      <div v-for="(btn, idx) in currentProfile.buttons" :key="btn.id" class="button-card">
        <div class="row">
          <button type="button" class="btn small" :disabled="idx === 0" title="Move up" @click="moveButton(idx, -1)">Up</button>
          <button type="button" class="btn small" :disabled="idx === currentProfile.buttons.length - 1" title="Move down" @click="moveButton(idx, 1)">Down</button>
          <input v-model="btn.name" placeholder="Button name" class="input" />
          <input v-model="btn.classes" placeholder="CSS classes e.g. bg-blue-500" class="input" />
          <button type="button" class="btn small danger" @click="removeButton(idx)">Remove</button>
        </div>
        <div class="key-sequence">
          <div v-for="(step, si) in btn.key_sequence" :key="si" class="step-row">
            <select :value="step._uiMode || (SPECIAL_KEYS.includes((step.key||'').toLowerCase()) ? 'special' : 'char')" class="input key-select" @change="onKeyModeChange(btn, si, $event)">
              <option value="special">Special key</option>
              <option value="char">Character</option>
            </select>
            <template v-if="(step._uiMode || (SPECIAL_KEYS.includes((step.key||'').toLowerCase()) ? 'special' : 'char')) === 'special'">
              <select v-model="step.key" class="input key-select">
                <option v-for="k in SPECIAL_KEYS" :key="k" :value="k">{{ k }}</option>
              </select>
            </template>
            <input v-else v-model="step.key" class="input key-input" placeholder="e.g. a, 1" maxlength="1" />
            <select v-model="step.action" class="input action-select">
              <option value="">--</option>
              <option v-for="a in KEY_ACTIONS" :key="a" :value="a">{{ a }}</option>
            </select>
            <button type="button" class="btn small" @click="removeStep(btn, si)">Remove step</button>
          </div>
          <button type="button" class="btn small" @click="addStep(btn)">Add step</button>
        </div>
      </div>
      <button type="button" class="btn" @click="addButton">Add button</button>
      <button type="button" class="btn primary" @click="saveProfile">Save profile</button>
    </section>

    <p v-if="msg" :class="msgType" class="message">{{ msg }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import {
  listProfiles,
  getProfile,
  getActive,
  createProfile,
  updateProfile,
  deleteProfile,
  setActive,
} from '../api'
import { SPECIAL_KEYS, KEY_ACTIONS } from '../constants'

const profiles = ref([])
const activeId = ref(null)
const selectedId = ref(null)
const currentProfile = ref(null)
const newProfileName = ref('')
const msg = ref('')
const msgType = ref('success')

function onKeyModeChange(btn, si, ev) {
  const step = btn.key_sequence[si]
  if (!step) return
  const mode = ev.target.value
  step._uiMode = mode
  if (mode === 'special') {
    step.key = step.key && SPECIAL_KEYS.includes((step.key || '').toLowerCase()) ? step.key : 'ctrl'
    step.action = step.action || ''
  } else {
    step.key = step.key && !SPECIAL_KEYS.includes((step.key || '').toLowerCase()) ? step.key : ''
    step.action = 'press'
  }
}

function addStep(btn) {
  if (!btn.key_sequence) btn.key_sequence = []
  btn.key_sequence.push({ key: '', action: 'press', _uiMode: 'char' })
}

function removeStep(btn, si) {
  btn.key_sequence.splice(si, 1)
}

function addButton() {
  if (!currentProfile.value) return
  if (!currentProfile.value.buttons) currentProfile.value.buttons = []
  currentProfile.value.buttons.push({
    id: crypto.randomUUID?.() ?? `b-${Date.now()}`,
    name: '',
    classes: '',
    key_sequence: [],
  })
}

function removeButton(idx) {
  currentProfile.value?.buttons?.splice(idx, 1)
}

function moveButton(idx, delta) {
  const btns = currentProfile.value?.buttons
  if (!btns || idx + delta < 0 || idx + delta >= btns.length) return
  const other = idx + delta
  ;[btns[idx], btns[other]] = [btns[other], btns[idx]]
}

function removeProfile(id) {
  if (!confirm('Remove this profile?')) return
  deleteProfile(id).then(() => {
    loadProfiles()
    if (selectedId.value === id) { selectedId.value = null; currentProfile.value = null }
    if (activeId.value === id) activeId.value = null
    msg.value = 'Profile removed'
    msgType.value = 'success'
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

async function loadProfiles() {
  profiles.value = await listProfiles()
  const active = await getActive()
  activeId.value = active.profile_id
}

function select(id) {
  selectedId.value = id
  getProfile(id).then((p) => {
    currentProfile.value = JSON.parse(JSON.stringify(p))
    if (!currentProfile.value.buttons) currentProfile.value.buttons = []
    currentProfile.value.buttons.forEach((b) => {
      if (!Array.isArray(b.key_sequence)) return
      b.key_sequence = b.key_sequence.map((s) => {
        const step = Array.isArray(s) ? { key: s[0], action: s[1] } : { ...s }
        step._uiMode = step.key && SPECIAL_KEYS.includes((step.key || '').toLowerCase()) ? 'special' : 'char'
        return step
      })
    })
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

function activate(id) {
  setActive(id).then(() => {
    activeId.value = id
    msg.value = 'Profile activated'
    msgType.value = 'success'
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

function addProfile() {
  const name = newProfileName.value.trim()
  if (!name) return
  createProfile(name).then(() => {
    newProfileName.value = ''
    loadProfiles()
    msg.value = 'Profile created'
    msgType.value = 'success'
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

function saveProfile() {
  if (!selectedId.value || !currentProfile.value) return
  const payload = {
    name: currentProfile.value.name,
    buttons: currentProfile.value.buttons.map((b) => ({
      id: b.id,
      name: b.name,
      classes: b.classes,
      key_sequence: (b.key_sequence || []).map((s) => [s.key, s.action || 'press']).filter(([k]) => k),
    })),
  }
  updateProfile(selectedId.value, payload).then(() => {
    msg.value = 'Saved'
    msgType.value = 'success'
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

onMounted(loadProfiles)
</script>

<style scoped>
  .editor { max-width: 640px; margin: 0 auto; }
  .section { margin-bottom: 2rem; }
  h2 { margin: 0 0 0.75rem; font-size: 1.1rem; }
  h3 { margin: 1rem 0 0.5rem; font-size: 1rem; }
  .profile-list { margin-bottom: 0.75rem; }
  .profile-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; flex-wrap: wrap; }
  .profile-name { min-width: 120px; }
  .row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .input { padding: 0.4rem 0.6rem; border: 1px solid #444; border-radius: 4px; background: #252525; color: #e0e0e0; }
  .btn { padding: 0.5rem 0.75rem; border: 1px solid #444; border-radius: 4px; background: #333; color: #e0e0e0; cursor: pointer; }
  .btn:hover { background: #444; }
  .btn.small { padding: 0.25rem 0.5rem; font-size: 0.85rem; }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.primary { background: #36a; border-color: #36a; }
  .btn.danger { background: #622; border-color: #833; }
  .btn.active { background: #264; }
  .btn.selected { background: #363; }
  .button-card { border: 1px solid #333; border-radius: 6px; padding: 0.75rem; margin-bottom: 0.75rem; background: #222; }
  .key-sequence { margin-top: 0.5rem; }
  .step-row { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.35rem; flex-wrap: wrap; }
  .key-select, .action-select { width: 100px; }
  .key-input { width: 3rem; text-align: center; }
  .message { margin-top: 1rem; font-size: 0.9rem; }
  .message.success { color: #6c6; }
  .message.error { color: #c66; }
</style>
