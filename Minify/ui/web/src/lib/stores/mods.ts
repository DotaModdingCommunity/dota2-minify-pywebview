import { writable } from 'svelte/store'
import type { Mod } from '$lib/api'

export const modsStore = writable<Mod[]>([])
