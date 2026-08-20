import { writable } from 'svelte/store'

export interface TermLine {
  raw: string
  args: unknown[]
  type: string | null
}

export function resolveText(raw: string, args: unknown[] = [], t: Record<string, string>): string {
  let s = raw
  if (s.startsWith('&')) s = t[s.slice(1)] ?? s
  if (args?.length) {
    let i = 0
    // Supports both sequential `{}` and numbered `{0}` / `{1}` placeholders.
    s = s.replace(/\{\d*\}/g, (m) => {
      const idx = m === '{}' ? i++ : Number(m.slice(1, -1))
      return String(args[idx] ?? '')
    })
  }
  return s.trimStart()
}

export function resolveLine(line: TermLine, t: Record<string, string>): string {
  const s = resolveText(line.raw, line.args, t)
  return line.type === 'detail' ? '   ' + s : s
}

function createTerminalStore() {
  const { subscribe, update } = writable<TermLine[]>([])

  return {
    subscribe,
    pushLine(raw: string, args: unknown[] = [], type: string | null = null) {
      update(lines => {
        const next = [...lines, { raw, args, type }]
        return next.length > 1000 ? next.slice(-1000) : next
      })
    },
    pushSeparator() {
      update(lines => {
        const next = [...lines, { raw: '', args: [], type: '__sep__' }]
        return next.length > 1000 ? next.slice(-1000) : next
      })
    },
    clear() {
      update(() => [])
    },
  }
}

export const terminalStore = createTerminalStore()