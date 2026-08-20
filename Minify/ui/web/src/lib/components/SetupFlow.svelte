<script lang="ts">
  import { fade, fly } from 'svelte/transition'
  import { setupFlowStore } from '$lib/stores/setupFlow'
  import { modsStore } from '$lib/stores/mods'
  import { modalStore } from '$lib/stores/modal'
  import SettingsForm from '$lib/components/SettingsForm.svelte'
  import FilePreview from '$lib/components/FilePreview.svelte'
  import ModDetails from '$lib/components/ModDetails.svelte'
  import Toggle from '$lib/components/Toggle.svelte'
  import type { SettingSchema, Mod, ModPreset } from '$lib/api'
  import { smoothscroll } from '$lib/actions/smoothscroll'
  import { focusTrap } from '$lib/actions/focusTrap'

  let pending = $derived($setupFlowStore?.pending ?? [])
  let waiterId = $derived($setupFlowStore?.waiterId ?? '')
  let step = $state(0)
  let total = $derived(pending.length)

  let loading = $state(true)
  let schema = $state<SettingSchema[]>([])
  let values = $state<Record<string, unknown>>({})
  let presets = $state<ModPreset[]>([])
  let previewFile = $state<string | null>(null)
  let previewToken = $state(0)
  let saveLaterMap = $state<Record<number, boolean>>({})

  let currentMod = $derived(pending[step])
  let bodyEl = $state<HTMLDivElement | null>(null)
  let showDetails = $state(false)
  let detailsMod = $derived<Mod | null>($modsStore.find(m => m.raw_name === currentMod?.name) ?? null)
  let hasDetails = $derived(!!detailsMod && (detailsMod.hasNotes || detailsMod.hasPreview))

  async function loadStep() {
    loading = true
    schema = []
    values = {}
    presets = []
    try {
      const res = await window.pywebview.api.get_mod_settings(currentMod.name)
      if (res.ok) {
        schema = res.data.schema
        values = { ...Object.fromEntries(schema.map(s => [s.key, s.default])), ...res.data.values }
        presets = res.data.presets ?? []
        previewFile = res.data.preview_file ?? null
      }
    } catch {
      schema = []
    }
    loading = false
    if (bodyEl) bodyEl.scrollTop = 0
  }

  $effect(() => {
    if (currentMod) loadStep()
  })

  // The .body is shared across steps. When the step changes, reset the scroll so
  // a stale offset from a taller step can never overshoot the new, shorter content.
  $effect(() => {
    step
    if (bodyEl) bodyEl.scrollTop = 0
  })

  async function runUtility(fn: string) {
    await window.pywebview.api.run_mod_utility(currentMod.name, fn)
    previewToken++
  }

  function resetSettings() {
    modalStore.set({
      title: "Confirm",
      messages: [`Reset all settings for ${currentMod.name} to defaults? This will prompt setup again on next patch.`],
      buttons: ["Cancel", "Confirm"],
      onrespond: (btn: string) => {
        if (btn === "Confirm") {
          window.pywebview.api.reset_mod_settings(currentMod.name)
            .then(res => {
              if (res.ok) {
                values = res.data
              } else {
                modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
              }
            })
            .catch((e: unknown) => {
              modalStore.set({ title: "Error", messages: [`Failed to reset settings: ${e}`], buttons: ["OK"] })
            })
        }
      },
    })
  }

  async function skip() {
    if (saveLaterMap[step] ?? false) {
      await window.pywebview.api.save_mod_settings(currentMod.name, values)
    }
    if (step < total - 1) {
      step++
    } else {
      done('continue')
    }
  }

  function back() {
    if (step > 0) step--
  }

  function cancel() {
    done('cancel')
  }

  function done(result: string) {
    window.pywebview.api.setup_flow_done(waiterId, result)
    setupFlowStore.set(null)
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') return
    if ($modalStore) return
    if (showDetails) return
    const target = e.target as HTMLElement | null
    if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
    if (e.key === 'Enter' && !loading) {
      skip()
    }
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="backdrop" in:fade={{ duration: 160 }} out:fade={{ duration: 110 }}>
  <div class="modal" in:fly={{ y: 8, duration: 160 }} out:fly={{ y: -8, duration: 110 }} use:focusTrap>
    <div class="header">
      <div class="header-left">
        <div class="name-row">
          <h2 class="mod-name">{currentMod?.name}</h2>
          {#if hasDetails}
            <button class="info-btn" onclick={() => showDetails = true} title="View details">i</button>
          {/if}
        </div>
        <span class="step-label">Mod Setup {step + 1} of {total}</span>
      </div>
      {#if schema.length > 0}
        <button class="reset-btn" onclick={resetSettings} title="Reset settings to defaults">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
        </button>
      {/if}
    </div>

    <div class="body" bind:this={bodyEl} data-scrollable use:smoothscroll>
      {#if loading}
        <div class="loading">Loading&hellip;</div>
      {:else if schema.length === 0}
        <p class="empty">{currentMod?.message || "No settings available."}</p>
      {:else}
        {#if previewFile}
          <FilePreview mod={currentMod.name} fileBase={previewFile} refreshToken={previewToken} />
        {/if}
        <SettingsForm
          {schema}
          {values}
          {presets}
          applyPreset={v => values = v}
          onaction={runUtility}
        />
      {/if}
    </div>

    <div class="footer">
      <div class="footer-left">
        <button class="btn-ghost" onclick={cancel}>Cancel</button>
        <button class="btn-ghost" onclick={back} disabled={step === 0}>Back</button>
      </div>
      <div class="footer-right">
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <label class="save-later" onclick={() => saveLaterMap[step] = !(saveLaterMap[step] ?? false)}>
          <Toggle checked={saveLaterMap[step] ?? false} onchange={() => saveLaterMap[step] = !(saveLaterMap[step] ?? false)} />
          <span>Save for later</span>
        </label>
        <button class="btn-primary" onclick={skip} disabled={loading}>
          {step < total - 1 ? "Next" : "Finish"}
        </button>
      </div>
    </div>
  </div>

  {#if showDetails && detailsMod}
    <ModDetails mod={detailsMod} zIndex={450} onClose={() => showDetails = false} />
  {/if}
</div>

<style>
  .backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
    background: rgba(0,0,0,var(--overlay-dim));
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 400;
  }

  .modal {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    width: fit-content;
    max-width: 90%;
    height: auto;
    max-height: 90%;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-floating);
    overflow: hidden;
  }

  .header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .name-row {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .mod-name {
    font-size: 13px;
    color: var(--accent);
    text-shadow: 0 0 12px var(--accent-glow);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .step-label { font-size: 12px; color: var(--text-dim); }

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

  .reset-btn {
    width: 26px;
    height: 26px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    transition: color 0.3s, border-color 0.3s, background 0.3s;
    flex-shrink: 0;
  }

  .reset-btn:hover { color: var(--accent); background: var(--bg-hover); border-color: var(--accent); }

  .body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-right: 3px;
  }

  .body::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .loading { color: var(--text-dim); padding: 16px; text-align: center; }
  .empty { color: var(--text); font-size: 12px; text-align: center; padding: 16px; line-height: 1.5; }

  .footer {
    display: flex;
    gap: 8px;
    justify-content: space-between;
    padding: 10px 14px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }

  .footer-right {
    display: flex;
    gap: 8px;
  }

  .footer-left {
    display: flex;
    gap: 8px;
  }

  .save-later {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-dim);
    margin-right: 4px;
    cursor: pointer;
    white-space: nowrap;
  }

  </style>
