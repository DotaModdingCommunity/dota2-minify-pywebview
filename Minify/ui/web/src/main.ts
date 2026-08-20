import { mount } from 'svelte'
import App from './App.svelte'
import { setZoomCss } from '$lib/zoom'

const zoomParam = new URLSearchParams(location.search).get('zoom')
if (zoomParam) {
  const z = parseFloat(zoomParam)
  if (Number.isFinite(z)) setZoomCss(z)
}

document.addEventListener('click', (e) => {
  if (e.defaultPrevented || e.button !== 0) return
  const anchor = (e.target as Element | null)?.closest?.('a[href]')
  if (!anchor) return
  const href = anchor.getAttribute('href')
  if (!href || href.startsWith('#')) return
  e.preventDefault()
  e.stopPropagation()
  window.pywebview?.api?.open_url(href)
}, true)

window.addEventListener("unhandledrejection", (e) => {
  console.error("Unhandled rejection:", e.reason)
  const el = document.createElement("div")
  el.style.cssText =
    "position:fixed;bottom:0;left:0;right:0;padding:6px 12px;background:var(--red);color:#fff;font-size:11px;z-index:999"
  el.textContent = `Unhandled error: ${e.reason}`
  document.body.appendChild(el)
  setTimeout(() => el.remove(), 8000)
})

const app = mount(App, { target: document.getElementById('app')! })
export default app
