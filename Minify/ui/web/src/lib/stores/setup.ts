import { writable } from 'svelte/store'

export interface SetupState {
  step: number
  data: {
    lang: string
    game_lang: string
    steam_ids: string[]
  }
}

export const setupStore = writable<SetupState | null>(null)
