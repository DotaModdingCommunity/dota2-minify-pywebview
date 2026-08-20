<script lang="ts">
  import { modsStore } from '$lib/stores/mods'
  import { d2pfxMods } from '$lib/stores/d2pfx'
  import { lock, depsDownloading } from '$lib/stores/lock'
  import { modalStore } from '$lib/stores/modal'
  import { settingsOpen } from '$lib/stores/settings'
  import { localeStore } from '$lib/stores/locale'
  import { patchRunning } from '$lib/stores/patchProgress'
  import Settings from '$lib/components/Settings.svelte'

  let _t = $derived($localeStore.t)

  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let hasEnabledMods = $derived(
    $modsStore.some(m => !m.always && m.enabled) ||
    Object.values($d2pfxMods).some(catMods => catMods.some(m => m.enabled))
  )

  async function handlePatch() {
    patchRunning.set(true)
    lock.set(true)
    try {
      const res = await window.pywebview.api.patch()
      if (!res.ok) {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
        patchRunning.set(false)
        lock.set(false)
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [String(e)], buttons: ["OK"] })
      patchRunning.set(false)
      lock.set(false)
    }
  }

  async function handleUninstall() {
    const res = await window.pywebview.api.uninstall()
    if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
  }
</script>

<div class="action-buttons" class:locked={$lock}>
  <button onclick={handlePatch} disabled={$lock || $depsDownloading || !hasEnabledMods} class="btn-accent">
    <span class="shortcut">P</span> {_("button_patch", "Patch")}
  </button>
  <button onclick={() => settingsOpen.set(true)} disabled={$lock}>
    <span class="shortcut">S</span> {_("settings", "Settings")}
  </button>
  <button onclick={handleUninstall} disabled={$lock} class="btn-danger">
    <span class="shortcut">U</span> {_("button_uninstall", "Uninstall")}
  </button>
</div>

{#if $settingsOpen}
  <Settings />
{/if}

<style>
  .action-buttons {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
    min-width: 0;
  }

  .action-buttons button {
    text-align: left;
    height: 28px;
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-surface);
    transition:
      color 0.12s,
      border-color 0.12s,
      background 0.12s,
      box-shadow 0.12s;
  }

  .action-buttons.locked {
    opacity: 0.6;
    pointer-events: none;
  }

  .btn-accent {
    font-weight: 600;
  }

  .btn-accent:hover:not(:disabled) {
    background: rgba(0, 230, 230, 0.06);
    color: var(--accent);
    border-color: var(--accent);
    box-shadow: var(--shadow-glow);
  }

  .btn-accent .shortcut {
    background: rgba(0, 230, 230, 0.1);
    border-color: var(--accent-dim);
    color: var(--accent);
  }

  .btn-danger:hover:not(:disabled) {
    background: rgba(255, 68, 68, 0.08);
    color: var(--red);
    border-color: var(--red);
    box-shadow: 0 0 10px rgba(255, 68, 68, 0.1);
  }

  .btn-danger:focus-visible,
  :global(html.keyboard-focus) .btn-danger:focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }

  .btn-danger .shortcut {
    border-color: rgba(255, 68, 68, 0.3);
    color: var(--red-dim);
  }

  .btn-danger:hover:not(:disabled) .shortcut {
    border-color: var(--red);
    color: var(--red);
    background: rgba(255, 68, 68, 0.1);
  }

  .shortcut {
    display: inline-block;
    min-width: 14px;
    text-align: center;
    padding: 0 4px;
    color: var(--accent);
    border: 1px solid var(--accent-dim);
    font-size: 10px;
    font-weight: 600;
    line-height: 1.4;
    border-radius: var(--radius-sm);
    transition: background 0.12s, border-color 0.12s, color 0.12s;
  }
</style>
