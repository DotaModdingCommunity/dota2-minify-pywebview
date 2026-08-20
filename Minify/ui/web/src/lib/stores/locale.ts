import { writable } from 'svelte/store'

export interface LocaleState {
  t: Record<string, string>
}

export const localeStore = writable<LocaleState>({
  t: {},
})
