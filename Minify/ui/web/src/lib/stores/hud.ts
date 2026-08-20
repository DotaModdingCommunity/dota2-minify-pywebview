import { writable } from 'svelte/store'

export interface HudData {
  messages: string[]
  value: number
  status: string
  args?: unknown[]
  visible: boolean
}

export const hudStore = writable<HudData | null>(null)
