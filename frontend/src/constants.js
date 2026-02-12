export const SPECIAL_KEYS = [
  'cmd', 'ctrl', 'shift', 'alt', 'option',
  'enter', 'backspace', 'space', 'tab', 'escape',
]

export const KEY_ACTIONS = ['down', 'press', 'up']

export function isSpecialKey(key) {
  return SPECIAL_KEYS.includes((key || '').toLowerCase())
}

export function defaultActionForKey(key) {
  return isSpecialKey(key) ? '' : 'press'
}
