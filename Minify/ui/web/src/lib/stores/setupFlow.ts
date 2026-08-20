import { writable } from 'svelte/store'

export interface SetupFlowItem {
  name: string
  message: string
}

export interface SetupFlowData {
  pending: SetupFlowItem[]
  waiterId: string
}

function createSetupFlowStore() {
  const { subscribe, set } = writable<SetupFlowData | null>(null)
  return { subscribe, set }
}

export const setupFlowStore = createSetupFlowStore()
