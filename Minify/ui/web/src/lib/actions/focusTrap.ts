import type { Action } from 'svelte/action'
import { isKeyboardFocus } from './focusMode'

/**
 * Traps keyboard focus inside an overlay so Tab / Shift+Tab can never reach
 * the underlying UI. On mount it moves focus into the container; on destroy it
 * restores focus to the element that had it before the overlay opened.
 *
 * Multiple traps may be mounted at once (e.g. a settings panel with a modal on
 * top). Each trap only intercepts Tab while the active element lives inside
 * it — the topmost overlay always wins, and the traps underneath defer.
 *
 * Optional `initial` selector picks the element that receives focus on open
 * (defaults to the first focusable in the container).
 */
export const focusTrap: Action<HTMLElement, { initial?: string } | undefined> = (node, options) => {
  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

  const getFocusable = (): HTMLElement[] =>
    Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      el => el.getClientRects().length > 0 || el === document.activeElement
    )

  const previous = document.activeElement as HTMLElement | null
  if (!node.hasAttribute('tabindex')) node.setAttribute('tabindex', '-1')
  node.setAttribute('data-focus-trap', '')

  const onKeydown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab') return
    const active = document.activeElement as HTMLElement | null
    // A higher overlay owns focus right now — leave the cycle to it.
    if (active) {
      const trap = active.closest('[data-focus-trap]') as HTMLElement | null
      if (trap && trap !== node) return
    }
    const focusables = getFocusable()
    if (focusables.length === 0) {
      e.preventDefault()
      return
    }
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    if (e.shiftKey) {
      if (active === first || !node.contains(active)) {
        e.preventDefault()
        last.focus()
      }
    } else if (active === last || !node.contains(active)) {
      e.preventDefault()
      first.focus()
    }
  }

  const focusInitial = () => {
    // Only steal focus on open when it was opened via keyboard. Mouse-open
    // overlays leave focus alone; the first Tab press still enters the trap.
    if (!isKeyboardFocus()) return
    if (options?.initial) {
      const el = node.querySelector<HTMLElement>(options.initial)
      if (el) {
        el.focus()
        return
      }
    }
    const first = getFocusable()[0]
    if (first) first.focus()
    else node.focus()
  }

  // Wait a frame so Svelte has mounted the container before stealing focus.
  requestAnimationFrame(focusInitial)
  window.addEventListener('keydown', onKeydown, true)

  return {
    destroy() {
      window.removeEventListener('keydown', onKeydown, true)
      if (previous && previous.isConnected) previous.focus({ preventScroll: true })
    },
  }
}