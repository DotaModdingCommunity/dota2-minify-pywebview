import { derived, writable } from 'svelte/store'
import type { D2pfxCategory, D2pfxMod } from '$lib/api'

export const d2pfxCategories = writable<D2pfxCategory[]>([])
export const d2pfxMods = writable<Record<string, D2pfxMod[]>>({})
export const selectedCategory = writable<string | null>(null)
export const d2pfxLoading = writable(false)
export const d2pfxEnabledCount = derived(d2pfxMods, ($mods) =>
  Object.values($mods).flat().filter(m => m.enabled).length
)
export const d2pfxEnabledCountFromApi = writable(0)
export const d2pfxTotalCount = writable(0)
