<script lang="ts">
  import { onMount } from 'svelte'
  import type { Mod, ModPreset, SettingSchema } from '$lib/api'
  import { modalStore } from '$lib/stores/modal'
  import { localeStore } from '$lib/stores/locale'
  import SettingsForm from '$lib/components/SettingsForm.svelte'
  import FilePreview from '$lib/components/FilePreview.svelte'
  import ModDetails from '$lib/components/ModDetails.svelte'
  import Panel from './Panel.svelte'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { mod, onClose }: { mod: Mod; onClose: () => void } = $props()

  let loading = $state(true)
  let error = $state(false)
  let schema = $state<SettingSchema[]>([])
  let values = $state<Record<string, unknown>>({})
  let presets = $state<ModPreset[]>([])
  let previewFile = $state<string | null>(null)
  let previewToken = $state(0)
  let showDetails = $state(false)

  let initialSnapshot = $state('')
  let closing = $state(false)
  let saved = $state(false)

  const hasDetails = $derived(mod.hasNotes || mod.hasPreview)

  function snapshot(v: Record<string, unknown>): string {
    return JSON.stringify(Object.fromEntries(schema.map(s => [s.key, v[s.key]])))
  }

  const dirty = $derived(!saved && snapshot(values) !== initialSnapshot)

  function requestClose() {
    if (closing) return
    if (dirty) {
      modalStore.set({
        title: _('unsaved_changes', 'Unsaved Changes'),
        messages: [_('unsaved_changes_msg', 'You have unsaved changes. Discard them?')],
        buttons: [_('cancel', 'Cancel'), _('discard', 'Discard')],
        onrespond: (btn: string) => {
          if (btn === _('discard', 'Discard')) {
            closing = true
            onClose()
          }
        },
      })
      return
    }
    closing = true
    onClose()
  }

  onMount(async () => {
    try {
      const res = await window.pywebview.api.get_mod_settings(mod.raw_name)
      if (res.ok) {
        schema = res.data.schema
        values = { ...Object.fromEntries(schema.map(s => [s.key, s.default])), ...res.data.values }
        presets = res.data.presets ?? []
        previewFile = res.data.preview_file ?? null
        initialSnapshot = snapshot(values)
      } else {
        error = true
      }
    } catch {
      error = true
    }
    loading = false
  })

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation()
      if (showDetails) {
        showDetails = false
        return
      }
      requestClose()
    }
  }

  function confirmAction(fn: string, label: string) {
    const confirmLabel = _('confirm', 'Confirm')
    const msgTpl = _('confirm_fetch_msg', 'Are you sure you want to {label}?')
    modalStore.set({
      title: _('confirm', 'Confirm'),
      messages: [msgTpl.replace('{label}', label.toLowerCase())],
      buttons: [_('cancel', 'Cancel'), confirmLabel],
      onrespond: (btn: string) => {
        if (btn === confirmLabel) {
          window.pywebview.api.run_mod_utility(mod.raw_name, fn)
            .then(res => {
              if (!res.ok) {
                modalStore.set({ title: 'Error', messages: [res.error], buttons: ['OK'] })
              } else {
                previewToken++
                const msgs = (res.data?.length > 0)
                  ? res.data.map((m: any) => m.text)
                  : [_('utility_completed', 'Completed')]
                modalStore.set({ title: label, messages: msgs, buttons: ['OK'] })
              }
            })
            .catch((e: unknown) => {
              modalStore.set({ title: 'Error', messages: [`Failed to run utility: ${e}`], buttons: ['OK'] })
            })
        }
      },
    })
  }

  async function resetSettings() {
    const confirmLabel = _('confirm', 'Confirm')
    const msgTpl = _('reset_mod_settings_msg', 'Reset all settings for {mod} to defaults? This will prompt setup again on next patch.')
    modalStore.set({
      title: _('confirm', 'Confirm'),
      messages: [msgTpl.replace('{mod}', mod.name)],
      buttons: [_('cancel', 'Cancel'), confirmLabel],
      onrespond: (btn: string) => {
        if (btn === confirmLabel) {
          window.pywebview.api.reset_mod_settings(mod.raw_name)
            .then(res => {
              if (res.ok) {
                values = res.data
                initialSnapshot = snapshot(values)
              } else {
                modalStore.set({ title: 'Error', messages: [res.error], buttons: ['OK'] })
              }
            })
            .catch((e: unknown) => {
              modalStore.set({ title: 'Error', messages: [`Failed to reset settings: ${e}`], buttons: ['OK'] })
            })
        }
      },
    })
  }

  async function save() {
    try {
      const res = await window.pywebview.api.save_mod_settings(mod.raw_name, values)
      if (!res.ok) {
        modalStore.set({ title: 'Error', messages: [res.error], buttons: ['OK'] })
      } else {
        saved = true
        onClose()
      }
    } catch (e) {
      modalStore.set({ title: 'Error', messages: [`Failed to save settings: ${e}`], buttons: ['OK'] })
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<Panel
  title={mod.name}
  onClose={requestClose}
  style="--panel-max-width:520px;--panel-max-height:calc(70vh / var(--zoom));--panel-width:90%"
>
  {#snippet headerExtra()}
    {#if hasDetails}
      <button class="info-btn" onclick={() => showDetails = true} title={_('view_details', 'View details')}>i</button>
    {/if}
  {/snippet}

      {#if loading}
        <div class="loading">{_('loading', 'Loading\u2026')}</div>
      {:else if error}
        <p class="error">{_('mod_settings_error', 'Failed to load settings.')}</p>
      {:else if schema.length === 0}
        <p class="empty">{_('no_settings', 'No settings available.')}</p>
      {:else}
        {#if previewFile}
          <FilePreview mod={mod.raw_name} fileBase={previewFile} refreshToken={previewToken} />
        {/if}
        <SettingsForm
          {schema}
          {values}
          {presets}
          applyPreset={v => values = v}
          onaction={key => confirmAction(key, schema.find(s => s.key === key)?.text ?? key)}
        />
      {/if}

  {#snippet footer()}
    <button class="btn-ghost" onclick={requestClose} disabled={loading || error}>{_('cancel', 'Cancel')}</button>
    <button class="btn-ghost" onclick={resetSettings} disabled={loading || error}>{_('reset', 'Reset')}</button>
    <button class="btn-primary" onclick={save} disabled={loading || error}>{_('save', 'Save')}</button>
  {/snippet}
</Panel>

{#if showDetails}
  <ModDetails mod={mod} zIndex={450} onClose={() => showDetails = false} />
{/if}

<style>
  .loading { color: var(--text-dim); padding: 16px; text-align: center; }
  .error { color: var(--red); font-size: 12px; text-align: center; padding: 16px; }
  .empty { color: var(--text-dim); font-size: 12px; text-align: center; padding: 16px; }

  .info-btn {
    width: 26px;
    height: 26px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--bg-surface);
    color: var(--text-dim);
    font-size: 15px;
    font-weight: 700;
    line-height: 1;
    padding: 0;
    cursor: pointer;
    transition: color 0.3s, border-color 0.3s, background 0.3s;
  }

  .info-btn:hover { color: var(--accent); border-color: var(--accent); background: var(--bg-hover); }

  .btn-ghost:hover:not(:disabled) {
    color: var(--red);
    border-color: var(--red);
  }
</style>