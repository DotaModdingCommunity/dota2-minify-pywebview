import { writable } from 'svelte/store'

export interface ModalData {
  title: string
  messages: string[]
  buttons: string[]
  social?: { discord: string; telegram: string; github_io: string }
  onrespond?: (label: string) => void
}

function createModalStore() {
  const { subscribe, set } = writable<ModalData | null>(null)
  let queue: ModalData[] = []

  function push(data: ModalData) {
    let current: ModalData | null = null
    const unsub = subscribe(v => { current = v })
    unsub()
    if (current !== null) {
      queue.push(data)
    } else {
      set(data)
    }
  }

  function dismiss() {
    if (queue.length > 0) {
      set(queue.shift()!)
    } else {
      set(null)
    }
  }

  return { subscribe, set, push, dismiss }
}

export const modalStore = createModalStore()
