<script lang="ts">
  import { settingsOpen, settingsStore } from '$lib/stores/settings'
  import { modalStore } from '$lib/stores/modal'
  import SettingsWidget from '$lib/components/SettingsWidget.svelte'
  import Toggle from '$lib/components/Toggle.svelte'
  import LangSelect from '$lib/components/LangSelect.svelte'
  import { setupStore } from '$lib/stores/setup'
  import { applyZoom } from '$lib/zoom'
  import type { SaveSettingsData } from '$lib/api'
  import { localeStore } from '$lib/stores/locale'
  import Panel from './Panel.svelte'

  import { onMount } from 'svelte'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let loading = $state(true)
  let localValues = $state<SaveSettingsData>({ global: {} })
  let showAdvanced = $state(false)
  let currentOutput = $state('')

  async function load() {
    loading = true
    try {
      const [settingsRes, infoRes] = await Promise.all([
        window.pywebview.api.get_settings(),
        window.pywebview.api.get_app_info(),
      ])
      if (infoRes.ok) currentOutput = infoRes.data.current_output
      const res = settingsRes
      if (res.ok) {
        settingsStore.set(res.data)
        showAdvanced = res.data.showAdvanced
        localValues = { global: { ...res.data.values.global } }
      } else {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [String(e)], buttons: ["OK"] })
    } finally {
      loading = false
    }
  }

  onMount(() => {
    load()
  })

  async function changeGameLang() {
    settingsOpen.set(false)
    const res = await window.pywebview.api.get_setup_data()
    if (res.ok) setupStore.set({ step: 2, data: res.data as { lang: string; game_lang: string; steam_ids: string[] } })
  }

  async function save() {
    const res = await window.pywebview.api.save_settings({ ...localValues, showAdvanced })
    if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
    else {
      settingsStore.update((s) => {
        if (!s) return s
        return {
          ...s,
          values: { ...s.values, global: { ...s.values.global, ...localValues.global } },
          showAdvanced,
        }
      })
      applyZoom(localValues.global.ui_zoom as number)
      settingsOpen.set(false)
    }
  }

  async function reset() {
    const res = await window.pywebview.api.reset_settings()
    if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
    else await load()
  }

  function resetModsSettings() {
    const confirmLabel = _("confirm", "Confirm")
    const msgTpl = _("reset_all_mods_msg", "Reset all mods' settings to defaults? This will prompt setup for every mod on the next patch.")
    modalStore.set({
      title: _("confirm", "Confirm"),
      messages: [msgTpl],
      buttons: [_("cancel", "Cancel"), confirmLabel],
      onrespond: async (btn: string) => {
        if (btn === confirmLabel) {
          const res = await window.pywebview.api.reset_all_mod_settings()
          if (!res.ok) {
            modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
          } else {
            modalStore.set({
              title: _("reset", "Reset"),
              messages: [_("reset_all_mods_done", "All mods' settings reset to defaults.")],
              buttons: ["OK"],
            })
          }
        }
      },
    })
  }

  async function openSteamSetup() {
    settingsOpen.set(false)
    const res = await window.pywebview.api.get_setup_data()
    if (res.ok) setupStore.set({ step: 3, data: res.data as { lang: string; game_lang: string; steam_ids: string[] } })
  }

  async function refreshD2pfx() {
    const res = await window.pywebview.api.refresh_d2pfx_catalogue()
    if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
    else
      modalStore.set({
        title: _("d2pfx", "D2PFX"),
        messages: [_("d2pfx_refresh_done", "Catalogue refresh started in the background.")],
        buttons: [_("ok", "OK")],
      })
  }

  function clearD2pfxCache() {
    const confirmLabel = _("confirm", "Confirm")
    modalStore.set({
      title: _("d2pfx_clear_cache", "Clear cached previews"),
      messages: [_("d2pfx_clear_cache_msg", "This will delete all cached D2PFX preview images. They will be re-downloaded on demand.")],
      buttons: [_("cancel", "Cancel"), confirmLabel],
      onrespond: async (btn: string) => {
        if (btn !== confirmLabel) return
        const res = await window.pywebview.api.clear_d2pfx_cache()
        if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      },
    })
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation()
      settingsOpen.set(false)
      return
    }
    const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return
    if (e.key.toLowerCase() === 's') settingsOpen.set(false)
  }
</script>

<svelte:window onkeydown={onKeydown} />

<Panel
  title={_("settings", "Settings")}
  onClose={() => settingsOpen.set(false)}
  class="settings-panel"
  style="--overlay-z:50"
>
      {#if loading}
        <div class="loading">{_("loading", "Loading\u2026")}</div>
      {:else if $settingsStore}

        <!-- Locale settings -->
        <section class="section">
          <div class="section-header">{_("settings_locale_section", "Language")}</div>
          <div class="locale-row">
            <span class="locale-label">{_("language", "Interface")}:</span>
            <LangSelect />
          </div>
          <div class="locale-row">
            <span class="locale-label">{_("settings_game_language", "Game Language")}:</span>
            <span class="locale-value">{currentOutput}</span>
            <button class="locale-change-btn" onclick={changeGameLang}>{_("change", "Change")}</button>
          </div>
        </section>

        <!-- Global settings -->
        <section class="section">
          <div class="section-header">{_("general", "General")}</div>
          <table class="widget-list">
            {#each $settingsStore.schema.global as schema}
              {#if !schema.advanced}
                <SettingsWidget {schema} bind:value={localValues.global[schema.key]} />
              {/if}
            {/each}
          </table>
        </section>

        <!-- Steam Accounts -->
        <section class="section">
          <div class="section-header">Steam Accounts</div>
          <div class="steam-accounts-row">
            <span>{(localValues.global.steam_ids as string[] | undefined)?.length ?? 0} {_("accounts_selected", "account(s) selected")}</span>
            <button onclick={openSteamSetup}>{_("configure", "Configure")}</button>
          </div>
        </section>

        <!-- D2PFX Catalogue -->
        <section class="section">
          <div class="section-header">D2PFX {_("d2pfx_catalogue", "Catalogue")}</div>
          <div class="d2pfx-actions-row">
            <button onclick={refreshD2pfx}>{_("d2pfx_refresh_now", "Refresh now")}</button>
            <button class="btn-danger" onclick={clearD2pfxCache}>{_("d2pfx_clear_cache", "Clear cached previews")}</button>
          </div>
        </section>

        <!-- Advanced toggle -->
        <div class="advanced-row">
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <label onclick={() => showAdvanced = !showAdvanced}>
            <Toggle checked={showAdvanced} onchange={() => showAdvanced = !showAdvanced} />
            <span>{_("advanced", "Advanced")}</span>
          </label>
        </div>

        {#if showAdvanced}
          <section class="section">
            <div class="section-header">{_("advanced_dev", "Developer")}</div>
            <table class="widget-list">
              {#each $settingsStore.schema.global as schema}
                {#if schema.advanced && schema.key !== 'steam_ids'}
                  <SettingsWidget {schema} bind:value={localValues.global[schema.key]} />
                {/if}
              {/each}
            </table>
          </section>
        {/if}

      {/if}

  {#snippet footer()}
    <button class="btn-ghost" onclick={reset}>{_("reset", "Reset")}</button>
    <button class="btn-ghost" onclick={resetModsSettings}>{_("reset_mods", "Reset Mods' Settings")}</button>
    <button class="btn-primary" onclick={save}>{_("save", "Save")}</button>
  {/snippet}
</Panel>

<style>
  :global(.settings-panel .panel-body .widget-list) {
    width: 100%;
  }

  .loading { color: var(--text-dim); padding: 16px; text-align: center; }

  .section { margin-bottom: 14px; }

  .section-header { margin-bottom: 6px; }

  .locale-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    font-size: 12px;
  }

  .locale-label {
    color: var(--text-dim);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .advanced-row {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    padding: 3px 0;
    border-top: 1px solid var(--border);
    padding-top: 6px;
    margin-top: 4px;
    margin-bottom: 6px;
  }

  .advanced-row label {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
  }
  .steam-accounts-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    font-size: 12px;
  }

  .d2pfx-actions-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    font-size: 12px;
  }

  .btn-ghost:hover:not(:disabled) {
    color: var(--red);
    border-color: var(--red);
  }

  .btn-danger:hover:not(:disabled) {
    color: var(--red);
    border-color: var(--red);
    background: rgba(255, 68, 68, 0.08);
  }

  .btn-danger:focus-visible,
  :global(html.keyboard-focus) .btn-danger:focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }
</style>
