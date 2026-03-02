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

        <div class="states-container">
          <h4>States</h4>
          <div class="state-tabs">
            <button
              v-for="stateName in Object.keys(btn.states || {})"
              :key="stateName"
              type="button"
              class="state-tab"
              :class="{ active: btn._editingState === stateName }"
              @click="btn._editingState = stateName"
            >
              {{ stateName }}
            </button>
            <button type="button" class="btn small" @click="addState(btn)">+ Add State</button>
          </div>

          <div v-if="btn._editingState && btn.states[btn._editingState]" class="state-editor">
            <div class="state-header">
              <h5>State: {{ btn._editingState }}</h5>
              <button
                v-if="btn._editingState !== 'initial'"
                type="button"
                class="btn small danger"
                @click="removeState(btn, btn._editingState)"
              >
                Remove State
              </button>
            </div>

            <div class="display-config">
              <h6>Display</h6>
              <div class="row">
                <label>Text</label>
                <input
                  v-model="btn.states[btn._editingState].display.text"
                  :placeholder="`Default: ${btn._editingState}`"
                  class="input"
                />
              </div>
              <div class="row">
                <label>Color</label>
                <input
                  v-model="btn.states[btn._editingState].display.color"
                  placeholder="e.g. #ff5555 or leave empty"
                  class="input"
                />
              </div>
            </div>

            <div class="events-config">
              <h6>Events & Actions</h6>
              <div v-for="eventType in ['click', 'dblclick']" :key="eventType" class="event-section">
                <div class="event-header">
                  <strong>{{ eventType === 'click' ? 'Click' : 'Double-click' }}</strong>
                  <button
                    v-if="!btn.states[btn._editingState].actions[eventType]"
                    type="button"
                    class="btn small"
                    @click="addEventAction(btn, btn._editingState, eventType)"
                  >
                    Add {{ eventType }} action
                  </button>
                  <button
                    v-else
                    type="button"
                    class="btn small danger"
                    @click="removeEventAction(btn, btn._editingState, eventType)"
                  >
                    Remove {{ eventType }} action
                  </button>
                </div>

                <div v-if="btn.states[btn._editingState].actions[eventType]" class="action-sequence">
                  <div
                    v-for="(action, ai) in btn.states[btn._editingState].actions[eventType].sequence"
                    :key="ai"
                    class="action-row"
                  >
                    <select v-model="action.type" class="input action-type-select" @change="onActionTypeChange(action)">
                      <option value="key">Key</option>
                      <option value="state_change">State Change</option>
                    </select>

                    <template v-if="action.type === 'key'">
                      <select
                        :value="action._uiMode || (SPECIAL_KEYS.includes((action.key||'').toLowerCase()) ? 'special' : 'char')"
                        class="input key-select"
                        @change="onKeyModeChange(action, $event)"
                      >
                        <option value="special">Special key</option>
                        <option value="char">Character</option>
                      </select>
                      <template v-if="(action._uiMode || (SPECIAL_KEYS.includes((action.key||'').toLowerCase()) ? 'special' : 'char')) === 'special'">
                        <select v-model="action.key" class="input key-select">
                          <option v-for="k in SPECIAL_KEYS" :key="k" :value="k">{{ k }}</option>
                        </select>
                      </template>
                      <input v-else v-model="action.key" class="input key-input" placeholder="e.g. a, 1" maxlength="1" />
                      <select v-model="action.action" class="input action-select">
                        <option value="">--</option>
                        <option v-for="a in KEY_ACTIONS" :key="a" :value="a">{{ a }}</option>
                      </select>
                    </template>

                    <template v-else-if="action.type === 'state_change'">
                      <label>Target State:</label>
                      <select v-model="action.target_state" class="input state-select">
                        <option value="">--Select State--</option>
                        <option v-for="stateName in Object.keys(btn.states || {})" :key="stateName" :value="stateName">
                          {{ stateName }}
                        </option>
                      </select>
                    </template>

                    <button type="button" class="btn small" @click="removeAction(btn, btn._editingState, eventType, ai)">
                      Remove
                    </button>
                  </div>
                  <button
                    type="button"
                    class="btn small"
                    @click="addAction(btn, btn._editingState, eventType)"
                  >
                    Add action
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <button type="button" class="btn" @click="addButton">Add button</button>
      <button type="button" class="btn primary" @click="saveProfile">Save profile</button>
    </section>

    <p v-if="msg" :class="msgType" class="message">{{ msg }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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

function ensureButtonStates(btn) {
  if (!btn.states) {
    btn.states = {
      initial: {
        display: { text: '', color: '' },
        actions: {}
      }
    }
  }
  if (!btn._editingState) {
    btn._editingState = 'initial'
  }
  Object.keys(btn.states).forEach(stateName => {
    const state = btn.states[stateName]
    if (!state.display) state.display = { text: '', color: '' }
    if (!state.actions) state.actions = {}
    Object.keys(state.actions).forEach(eventType => {
      const eventData = state.actions[eventType]
      if (!eventData.id) eventData.id = crypto.randomUUID?.() ?? `action-${Date.now()}-${Math.random()}`
      if (!eventData.sequence) eventData.sequence = []
      eventData.sequence.forEach(action => {
        if (action.type === 'key') {
          action._uiMode = action.key && SPECIAL_KEYS.includes((action.key || '').toLowerCase()) ? 'special' : 'char'
        }
      })
    })
  })
}

function addState(btn) {
  const stateName = prompt('Enter new state name:')
  if (!stateName || !stateName.trim()) return
  const trimmed = stateName.trim()
  if (btn.states[trimmed]) {
    alert('State already exists')
    return
  }
  btn.states[trimmed] = {
    display: { text: '', color: '' },
    actions: {}
  }
  btn._editingState = trimmed
}

function removeState(btn, stateName) {
  if (stateName === 'initial') {
    alert('Cannot remove initial state')
    return
  }
  if (!confirm(`Remove state "${stateName}"?`)) return
  delete btn.states[stateName]
  btn._editingState = 'initial'
}

function addEventAction(btn, stateName, eventType) {
  if (!btn.states[stateName].actions[eventType]) {
    btn.states[stateName].actions[eventType] = {
      id: crypto.randomUUID?.() ?? `action-${Date.now()}-${Math.random()}`,
      sequence: []
    }
  }
}

function removeEventAction(btn, stateName, eventType) {
  if (!confirm(`Remove ${eventType} action?`)) return
  delete btn.states[stateName].actions[eventType]
}

function addAction(btn, stateName, eventType) {
  const eventData = btn.states[stateName].actions[eventType]
  if (!eventData) return
  eventData.sequence.push({ type: 'key', key: '', action: 'press', _uiMode: 'char' })
}

function removeAction(btn, stateName, eventType, actionIndex) {
  const eventData = btn.states[stateName].actions[eventType]
  if (!eventData) return
  eventData.sequence.splice(actionIndex, 1)
}

function onActionTypeChange(action) {
  if (action.type === 'key') {
    action.key = ''
    action.action = 'press'
    action._uiMode = 'char'
    delete action.target_state
  } else if (action.type === 'state_change') {
    action.target_state = ''
    delete action.key
    delete action.action
    delete action._uiMode
  }
}

function onKeyModeChange(action, ev) {
  const mode = ev.target.value
  action._uiMode = mode
  if (mode === 'special') {
    action.key = action.key && SPECIAL_KEYS.includes((action.key || '').toLowerCase()) ? action.key : 'ctrl'
    action.action = action.action || ''
  } else {
    action.key = action.key && !SPECIAL_KEYS.includes((action.key || '').toLowerCase()) ? action.key : ''
    action.action = 'press'
  }
}

function addButton() {
  if (!currentProfile.value) return
  if (!currentProfile.value.buttons) currentProfile.value.buttons = []
  const btn = {
    id: crypto.randomUUID?.() ?? `b-${Date.now()}`,
    name: '',
    classes: '',
    states: {
      initial: {
        display: { text: '', color: '' },
        actions: {}
      }
    },
    _editingState: 'initial'
  }
  currentProfile.value.buttons.push(btn)
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
    currentProfile.value.buttons.forEach(ensureButtonStates)
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
    buttons: currentProfile.value.buttons.map((b) => {
      const cleaned = {
        id: b.id,
        name: b.name,
        classes: b.classes,
        states: {}
      }
      Object.keys(b.states).forEach(stateName => {
        const state = b.states[stateName]
        cleaned.states[stateName] = {
          display: {
            text: state.display?.text || '',
            color: state.display?.color || ''
          },
          actions: {}
        }
        Object.keys(state.actions || {}).forEach(eventType => {
          const eventData = state.actions[eventType]
          cleaned.states[stateName].actions[eventType] = {
              id: eventData.id || (crypto.randomUUID?.() ?? `action-${Date.now()}-${Math.random()}`),
            sequence: eventData.sequence.map(action => {
              if (action.type === 'state_change') {
                return { type: 'state_change', target_state: action.target_state }
              }
              return { type: 'key', key: action.key, action: action.action || 'press' }
            }).filter(a => {
              if (a.type === 'key') return a.key
              if (a.type === 'state_change') return a.target_state
              return false
            })
          }
        })
      })
      return cleaned
    }),
  }
  updateProfile(selectedId.value, payload).then(() => {
    msg.value = 'Saved'
    msgType.value = 'success'
  }).catch((e) => { msg.value = e.message; msgType.value = 'error' })
}

onMounted(loadProfiles)
</script>

<style scoped>
  .editor { max-width: 800px; margin: 0 auto; }
  .section { margin-bottom: 2rem; }
  h2 { margin: 0 0 0.75rem; font-size: 1.1rem; }
  h3 { margin: 1rem 0 0.5rem; font-size: 1rem; }
  h4 { margin: 0.75rem 0 0.5rem; font-size: 0.95rem; }
  h5 { margin: 0; font-size: 0.9rem; }
  h6 { margin: 0.5rem 0 0.35rem; font-size: 0.85rem; color: #aaa; }
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
  .states-container { margin-top: 0.75rem; }
  .state-tabs { display: flex; gap: 0.35rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
  .state-tab { padding: 0.35rem 0.6rem; border: 1px solid #444; border-radius: 4px; background: #2a2a2a; color: #ccc; cursor: pointer; font-size: 0.85rem; }
  .state-tab.active { background: #36a; border-color: #36a; color: #fff; }
  .state-tab:hover { background: #333; }
  .state-editor { border: 1px solid #444; border-radius: 6px; padding: 0.75rem; background: #1a1a1a; }
  .state-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
  .display-config { margin-bottom: 0.75rem; }
  .events-config { }
  .event-section { margin-bottom: 0.75rem; border: 1px solid #333; border-radius: 4px; padding: 0.5rem; background: #252525; }
  .event-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
  .action-sequence { }
  .action-row { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.35rem; flex-wrap: wrap; }
  .action-type-select { width: 120px; }
  .key-select, .action-select { width: 100px; }
  .state-select { width: 140px; }
  .key-input { width: 3rem; text-align: center; }
  .message { margin-top: 1rem; font-size: 0.9rem; }
  .message.success { color: #6c6; }
  .message.error { color: #c66; }
</style>
