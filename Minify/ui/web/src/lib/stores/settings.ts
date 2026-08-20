import { writable } from 'svelte/store'
import type { SettingsPayload } from '$lib/api'

export const settingsStore = writable<SettingsPayload | null>(null)
export const settingsOpen = writable<boolean>(false)
