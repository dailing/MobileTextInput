<template>
  <div class="panel">
    <p v-if="!activeId" class="hint">No profile active. Go to Editor to choose a profile.</p>
    <p v-else class="profile-name">Profile: {{ profileName }}</p>
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="grid">
      <button
        v-for="btn in buttons"
        :key="btn.id"
        type="button"
        class="hotkey-btn"
        :class="btn.classes"
        :style="getButtonStyle(btn)"
        @click="onClick(btn, $event)"
        @dblclick="onDblClick(btn, $event)"
      >
        {{ getButtonText(btn) }}
      </button>
    </div>
    <section class="text-input-section">
      <textarea
        v-model="textToSend"
        class="text-input"
        placeholder="Type text to paste on server..."
        rows="3"
      ></textarea>
      <button type="button" class="send-btn" :disabled="!textToSend.trim() || sending" @click="onSendText">
        {{ sending ? 'Sending...' : 'Send & Paste' }}
      </button>
    </section>
    <section class="touchpad-section">
      <h3 class="touchpad-heading">Touchpad</h3>
      <div
        ref="touchpadRef"
        class="touchpad-area"
        @touchstart="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
        @mousedown="onMouseDown"
      ></div>
      <div class="touchpad-buttons">
        <button type="button" class="mouse-btn left" @click="onClickBtn('left')">Left</button>
        <button type="button" class="mouse-btn middle" @click="onClickBtn('middle')">Middle</button>
        <button type="button" class="mouse-btn right" @click="onClickBtn('right')">Right</button>
      </div>
    </section>
    <section class="windows-section">
      <div class="windows-header">
        <h3 class="windows-heading">Windows <span v-if="loadingWindows" class="windows-loading">(loading...)</span></h3>
        <button type="button" class="refresh-btn" :disabled="loadingWindows" @click="loadWindowsAsync">Refresh</button>
      </div>
      <div v-if="windows.length" class="windows-list">
        <button
          v-for="w in windows"
          :key="w.id"
          type="button"
          class="window-item"
          :title="w.app ? `${w.app}: ${w.title}` : w.title"
          @click="onActivateWindow(w)"
        >
          {{ w.app ? `${w.app} – ${w.title}` : w.title }}
        </button>
      </div>
      <p v-else-if="!loadingWindows" class="no-windows">No windows found</p>
    </section>
    <p v-if="message" :class="messageType" class="message">{{ message }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { getActive, getButtons, simulate, getWindows, activateWindow, pasteText, mouseMove, mouseClick, getSettings } from '../api'

const buttons = ref([])
const windows = ref([])
const activeId = ref(null)
const profileName = ref('')
const loading = ref(true)
const loadingWindows = ref(false)
const message = ref('')
const messageType = ref('success')
const textToSend = ref('')
const sending = ref(false)

const buttonStates = ref(new Map())

const touchpadRef = ref(null)
const lastPos = ref(null)
const sensitivity = ref(1.5)

const clickTimers = ref(new Map())
const DOUBLE_CLICK_DELAY = 300

async function load(skipWindows = false) {
  loading.value = true
  try {
    const [active, buttonsData, settings] = await Promise.all([getActive(), getButtons(), getSettings()])
    activeId.value = active.profile_id
    profileName.value = active.profile?.name ?? ''
    buttons.value = buttonsData.buttons || []
    sensitivity.value = settings.touchpad_sensitivity ?? 1.5
    initButtonStates()
  } catch (e) {
    buttons.value = []
    message.value = e.message
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
  if (!skipWindows) loadWindowsAsync()
}

function initButtonStates() {
  buttonStates.value.clear()
  buttons.value.forEach(btn => {
    if (btn.states) {
      buttonStates.value.set(btn.id, 'initial')
    }
  })
}

function getCurrentState(btn) {
  return buttonStates.value.get(btn.id) || 'initial'
}

function getButtonText(btn) {
  if (!btn.states) return btn.name
  const currentState = getCurrentState(btn)
  const state = btn.states[currentState]
  if (!state) return btn.name
  return state.display?.text || currentState || btn.name
}

function getButtonStyle(btn) {
  if (!btn.states) return {}
  const currentState = getCurrentState(btn)
  const state = btn.states[currentState]
  if (!state || !state.display?.color) return {}
  return { backgroundColor: state.display.color }
}

function handleButtonEvent(btn, eventType) {
  if (!btn.states) {
    simulate(btn.id, false).then((res) => {
      message.value = res.success ? 'Done' : 'Failed'
      messageType.value = res.success ? 'success' : 'error'
    }).catch((e) => {
      message.value = e.message
      messageType.value = 'error'
    })
    return
  }

  const currentState = getCurrentState(btn)
  const state = btn.states[currentState]
  if (!state || !state.actions || !state.actions[eventType]) {
    message.value = `No ${eventType} action for state ${currentState}`
    messageType.value = 'error'
    return
  }

  const eventData = state.actions[eventType]
  const actionSeqId = eventData.id

  simulate(actionSeqId, true).then((res) => {
    if (res.success) {
      const sequence = eventData.sequence || []
      sequence.forEach(action => {
        if (action.type === 'state_change' && action.target_state) {
          if (btn.states[action.target_state]) {
            buttonStates.value.set(btn.id, action.target_state)
          } else {
            console.warn(`State ${action.target_state} not found for button ${btn.id}`)
          }
        }
      })
      message.value = 'Done'
      messageType.value = 'success'
    } else {
      message.value = 'Failed'
      messageType.value = 'error'
    }
  }).catch((e) => {
    message.value = e.message
    messageType.value = 'error'
  })
}

function onClick(btn, event) {
  message.value = ''
  
  const timerId = clickTimers.value.get(btn.id)
  if (timerId) {
    clearTimeout(timerId)
    clickTimers.value.delete(btn.id)
    return
  }

  const timer = setTimeout(() => {
    clickTimers.value.delete(btn.id)
    handleButtonEvent(btn, 'click')
  }, DOUBLE_CLICK_DELAY)
  
  clickTimers.value.set(btn.id, timer)
}

function onDblClick(btn, event) {
  message.value = ''
  const timerId = clickTimers.value.get(btn.id)
  if (timerId) {
    clearTimeout(timerId)
    clickTimers.value.delete(btn.id)
  }
  handleButtonEvent(btn, 'dblclick')
}

async function loadWindowsAsync() {
  loadingWindows.value = true
  try {
    const data = await getWindows()
    windows.value = data.windows || []
  } catch {
    windows.value = []
  } finally {
    loadingWindows.value = false
  }
}

async function onActivateWindow(w) {
  message.value = ''
  try {
    const res = await activateWindow(w.id)
    message.value = res.success ? 'Window activated' : 'Failed to activate'
    messageType.value = res.success ? 'success' : 'error'
  } catch (e) {
    message.value = e.message
    messageType.value = 'error'
  }
}

async function onSendText() {
  if (!textToSend.value.trim()) return
  message.value = ''
  sending.value = true
  try {
    const res = await pasteText(textToSend.value)
    message.value = res.success ? 'Text pasted' : 'Failed to paste'
    messageType.value = res.success ? 'success' : 'error'
    if (res.success) textToSend.value = ''
  } catch (e) {
    message.value = e.message
    messageType.value = 'error'
  } finally {
    sending.value = false
  }
}

function onTouchStart(e) {
  if (e.touches.length === 1) {
    const t = e.touches[0]
    lastPos.value = { x: t.clientX, y: t.clientY }
  }
}

function onTouchMove(e) {
  if (e.touches.length !== 1 || !lastPos.value) return
  e.preventDefault()
  const t = e.touches[0]
  const dx = Math.round((t.clientX - lastPos.value.x) * sensitivity.value)
  const dy = Math.round((t.clientY - lastPos.value.y) * sensitivity.value)
  lastPos.value = { x: t.clientX, y: t.clientY }
  if (dx !== 0 || dy !== 0) mouseMove(dx, dy).catch(() => {})
}

function onTouchEnd() {
  lastPos.value = null
}

function onMouseDown(e) {
  lastPos.value = { x: e.clientX, y: e.clientY }
  const onMove = (ev) => {
    if (!lastPos.value) return
    const dx = Math.round((ev.clientX - lastPos.value.x) * sensitivity.value)
    const dy = Math.round((ev.clientY - lastPos.value.y) * sensitivity.value)
    lastPos.value = { x: ev.clientX, y: ev.clientY }
    if (dx !== 0 || dy !== 0) mouseMove(dx, dy).catch(() => {})
  }
  const onUp = () => {
    lastPos.value = null
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

async function onClickBtn(btn) {
  message.value = ''
  try {
    const res = await mouseClick(btn)
    message.value = res.success ? 'Clicked' : 'Click failed'
    messageType.value = res.success ? 'success' : 'error'
  } catch (e) {
    message.value = e.message
    messageType.value = 'error'
  }
}

onMounted(load)
watch(activeId, (newVal, oldVal) => {
  if (oldVal !== undefined && newVal !== oldVal) load(true)
})
</script>

<style scoped>
  .panel { max-width: 80%; margin: 0 auto; }
  .hint, .profile-name { margin: 0 0 1rem; color: #888; font-size: 0.9rem; }
  .loading { color: #888; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.5rem; }
  .hotkey-btn { padding: 1rem; border: 1px solid #444; border-radius: 8px; background: #2a2a2a; color: #e0e0e0; font-size: 1rem; cursor: pointer; }
  .hotkey-btn:hover { background: #333; }
  .hotkey-btn.bg-red-500 { background: #b33; }
  .hotkey-btn.bg-blue-500 { background: #36a; }
  .message { margin-top: 1rem; font-size: 0.9rem; }
  .message.success { color: #6c6; }
  .message.error { color: #c66; }
  .text-input-section { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #333; display: flex; flex-direction: column; gap: 0.5rem; }
  .text-input { width: 100%; padding: 0.6rem; border: 1px solid #444; border-radius: 6px; background: #252525; color: #e0e0e0; font-size: 0.95rem; resize: vertical; box-sizing: border-box; }
  .text-input::placeholder { color: #666; }
  .send-btn { padding: 0.6rem 1rem; border: none; border-radius: 6px; background: #36a; color: #fff; font-size: 0.95rem; cursor: pointer; }
  .send-btn:hover:not(:disabled) { background: #47b; }
  .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .touchpad-section { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #333; }
  .touchpad-heading { margin: 0 0 0.5rem; font-size: 0.95rem; color: #888; }
  .touchpad-area { width: 100%; height: 280px; background: #1e1e1e; border: 1px solid #444; border-radius: 8px; touch-action: none; cursor: crosshair; }
  .touchpad-buttons { display: flex; gap: 0.5rem; margin-top: 0.5rem; }
  .mouse-btn { flex: 1; padding: 0.7rem; border: 1px solid #444; border-radius: 6px; background: #2a2a2a; color: #e0e0e0; font-size: 0.9rem; cursor: pointer; }
  .mouse-btn:hover { background: #333; }
  .mouse-btn.left { background: #2a4a2a; }
  .mouse-btn.left:hover { background: #3a5a3a; }
  .mouse-btn.right { background: #4a2a2a; }
  .mouse-btn.right:hover { background: #5a3a3a; }
  .mouse-btn.middle { background: #3a3a4a; }
  .mouse-btn.middle:hover { background: #4a4a5a; }
  .windows-section { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #333; }
  .windows-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
  .windows-heading { margin: 0; font-size: 0.95rem; color: #888; }
  .windows-loading { font-size: 0.8rem; color: #666; }
  .refresh-btn { padding: 0.3rem 0.6rem; border: 1px solid #444; border-radius: 4px; background: #2a2a2a; color: #e0e0e0; font-size: 0.8rem; cursor: pointer; }
  .refresh-btn:hover:not(:disabled) { background: #333; }
  .refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .windows-list { display: flex; flex-direction: column; gap: 0.35rem; }
  .window-item { padding: 0.4rem 0.6rem; text-align: left; border: 1px solid #444; border-radius: 4px; background: #252525; color: #e0e0e0; font-size: 0.85rem; cursor: pointer; }
  .window-item:hover { background: #333; }
  .no-windows { margin: 0; font-size: 0.85rem; color: #666; }
</style>
