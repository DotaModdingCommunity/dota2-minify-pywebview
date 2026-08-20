import type { Action } from 'svelte/action'
import { settingsStore } from '$lib/stores/settings'

const EASE = 0.12
const FAST_SCROLL_MULTIPLIER = 4

export const smoothscroll: Action = (node) => {
  let goal = 0
  let raf = 0
  let active = false

  // Neutralise the global `scroll-behavior: smooth` while the JS loop owns the
  // scroll position. Without this the browser also animates every programmatic
  // scrollTop write, compounding the motion and leaving scrollTop stuck a
  // fraction of a pixel away from its goal (visible as a cropped top edge).
  const prevBehavior = node.style.scrollBehavior
  const setInstant = () => { node.style.scrollBehavior = 'auto' }
  const restoreBehavior = () => { node.style.scrollBehavior = prevBehavior }

  const step = () => {
    const max = Math.max(0, node.scrollHeight - node.clientHeight)
    const target = Math.max(0, Math.min(max, goal))
    const cur = node.scrollTop
    const delta = target - cur
    // Chromium reports an integer `scrollTop`, so writing a fractional easing
    // step a few pixels from the target writes 956.48 but reads back 956. The
    // `next === cur` check never fires and `delta` never drops below the snap
    // threshold, leaving the scroll stuck (and a RAF spinning forever) a few
    // pixels short of the true top/bottom. Snap whenever we're within 1px and
    // force at least 1px of visible progress per frame otherwise.
    if (Math.abs(delta) <= 1) {
      node.scrollTop = target
      active = false
      restoreBehavior()
      return
    }
    let next = cur + delta * EASE
    if (Math.abs(next - cur) < 1) next = cur + (delta > 0 ? 1 : -1)
    node.scrollTop = next
    active = true
    raf = requestAnimationFrame(step)
  }

  const onWheel = (e: WheelEvent) => {
    if (e.ctrlKey) return
    if (e.deltaY === 0 && e.deltaX === 0) return
    e.preventDefault()
    let raw: number
    if (e.shiftKey) {
      // Shift+wheel = fast scroll. Chromium remaps the vertical gesture to
      // deltaX, so fall back to deltaY for platforms that don't.
      const d = e.deltaX !== 0 ? e.deltaX : e.deltaY
      raw = d * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? node.clientHeight : 1)
      raw *= FAST_SCROLL_MULTIPLIER
    } else {
      if (e.deltaY === 0) return
      raw = e.deltaY * (e.deltaMode === 1 ? 12 : e.deltaMode === 2 ? node.clientHeight * 0.75 : 0.75)
    }
    // Re-anchor to the live position at the start of a fresh gesture so a
    // previous gesture's stale goal can't prevent reaching the real top.
    if (!active) goal = node.scrollTop
    goal = Math.max(0, Math.min(node.scrollHeight - node.clientHeight, goal + raw))
    if (!active) {
      setInstant()
      active = true
      raf = requestAnimationFrame(step)
    }
  }

  const apply = (on: boolean) => {
    if (on) {
      node.addEventListener('wheel', onWheel, { passive: false })
    } else {
      node.removeEventListener('wheel', onWheel)
      if (active) {
        cancelAnimationFrame(raf)
        active = false
        goal = node.scrollTop
        restoreBehavior()
      }
    }
  }

  const unsubscribe = settingsStore.subscribe((s) => {
    apply(Boolean(s?.values?.global?.smooth_scroll))
  })

  return {
    destroy() {
      unsubscribe()
      apply(false)
    },
  }
}
