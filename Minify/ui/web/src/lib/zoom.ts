const ZOOM_PRESETS = [1.0, 1.25, 1.5, 1.75, 2.0]
const ZOOM_MIN = 1.0
const ZOOM_MAX = 2.0
export const ZOOM_STEP = 0.05

function currentZoom(): number {
  const z = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--zoom"))
  return Number.isFinite(z) && z > 0 ? z : 1
}

function clampZoom(value: number): number {
  return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value))
}

export function setZoomCss(value: number): number {
  const next = clampZoom(value)
  document.documentElement.style.zoom = String(next)
  document.documentElement.style.setProperty("--zoom", String(next))
  return next
}

export function applyZoom(value: number): number {
  const next = setZoomCss(value)
  window.pywebview?.api?.set_ui_zoom(next).catch(() => {})
  return next
}

export function zoomBy(delta: number): number {
  return applyZoom(currentZoom() + delta)
}

export function cycleZoom(dir: 1 | -1): number {
  const cur = currentZoom()
  const next =
    dir > 0
      ? ZOOM_PRESETS.find((p) => p > cur + 1e-9) ?? ZOOM_PRESETS[ZOOM_PRESETS.length - 1]
      : ZOOM_PRESETS.slice().reverse().find((p) => p < cur - 1e-9) ?? ZOOM_PRESETS[0]
  return applyZoom(next)
}