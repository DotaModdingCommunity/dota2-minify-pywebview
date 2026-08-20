import { writable } from 'svelte/store'
export const scrollPositions = writable<Record<string, number>>({})
