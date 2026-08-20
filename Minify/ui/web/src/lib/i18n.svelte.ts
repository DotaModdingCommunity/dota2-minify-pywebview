import { localeStore } from '$lib/stores/locale'

let _loadSeq = 0

export async function loadLocale(lang: string): Promise<void> {
  const seq = ++_loadSeq
  const res = await window.pywebview.api.get_localization(lang)
  if (seq === _loadSeq && res.ok) {
    localeStore.set({ t: res.data })
  }
}
