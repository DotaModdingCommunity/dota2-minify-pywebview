const NAV_KEYS = new Set([
  'Tab',
  'ArrowUp',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'Enter',
  ' ',
  'Home',
  'End',
  'PageUp',
  'PageDown',
])

let keyboard = false

function setKeyboard(value: boolean) {
  if (keyboard === value) return
  keyboard = value
  document.documentElement.classList.toggle('keyboard-focus', value)
}

window.addEventListener('keydown', (e) => {
  if (NAV_KEYS.has(e.key)) setKeyboard(true)
})

window.addEventListener('pointerdown', () => setKeyboard(false))

export function isKeyboardFocus(): boolean {
  return keyboard
}