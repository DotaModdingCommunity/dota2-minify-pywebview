import { writable } from 'svelte/store'

export const lock = writable<boolean>(false)
export const depsDownloading = writable<boolean>(false)
