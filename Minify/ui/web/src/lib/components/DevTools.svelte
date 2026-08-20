<script lang="ts">
  import { fade } from 'svelte/transition'
  import { localeStore } from "$lib/stores/locale"
  import { onMount } from 'svelte'
  import { scrollPositions } from '$lib/stores/scroll'
  import { get } from 'svelte/store'
  import { modsStore } from "$lib/stores/mods"
  import type { ApiResult } from '$lib/api'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let devToolsEl: HTMLDivElement

  onMount(() => {
    const pos = get(scrollPositions)['devtools']
    if (pos > 0 && devToolsEl) devToolsEl.scrollTop = pos
  })



  async function api<T>(fn: () => Promise<ApiResult<T>>): Promise<T | null> {
    const res = await fn()
    if (!res.ok) {
      console.error("API error:", res.error)
      return null
    }
    return res.data ?? null
  }

  async function refreshMods() {
    const mods = await api(() => window.pywebview.api.get_mods())
    if (mods) modsStore.set(mods)
  }

  function openDevPath(name: string, args?: string) {
    api(() => window.pywebview.api.open_path(name, args ?? ""))
  }

  function createDebugZip() {
    api(() => window.pywebview.api.create_debug_zip())
  }

  function compileAssets() {
    api(() => window.pywebview.api.compile_assets())
  }

  async function selectCompileDir() {
    await api(() => window.pywebview.api.select_compile_dir())
  }

  function compileFromCustom() {
    api(() => window.pywebview.api.compile_from_custom())
  }

  async function setAllMods(enabled: boolean) {
    const res = await window.pywebview.api.set_all_mods(enabled)
    if (res.ok) {
      await refreshMods()
    }
  }

  function wipeLanguagePaths() {
    api(() => window.pywebview.api.wipe_language_paths())
  }

  function extractWorkshopTools() {
    api(() => window.pywebview.api.extract_workshop_tools())
  }

  function launchSteam() {
    api(() => window.pywebview.api.launch_steam())
  }

  function killSteam() {
    api(() => window.pywebview.api.kill_steam())
  }

  function validateDota2() {
    api(() => window.pywebview.api.validate_dota2())
  }
</script>

<div class="devtools" bind:this={devToolsEl} data-scrollable in:fade={{ duration: 200 }}
     onscroll={() => scrollPositions.update(p => ({ ...p, devtools: devToolsEl.scrollTop }))} use:smoothscroll>
  <div class="section">
    <div class="section-header">{_("devtools_nav", "Navigation")}</div>
    <div class="btn-grid">
      <button onclick={() => openDevPath("compile_output")}>
        Compile output path
      </button>
      <button onclick={() => openDevPath("minify_root")}>
        Minify root
      </button>
      <button onclick={() => openDevPath("logs")}>
        Logs directory
      </button>
      <button onclick={() => openDevPath("config")}>
        Config directory
      </button>
      <button onclick={() => openDevPath("mods")}>
        Mods directory
      </button>
      <button onclick={() => openDevPath("dota2")}>
        Dota 2 directory
      </button>
      <button onclick={() => openDevPath("dota2_pak01")}>
        Dota 2 pak01 VPK
      </button>
      <button onclick={() => openDevPath("dota2_core")}>
        Dota 2 pak01 (core) VPK
      </button>
      <button onclick={() => openDevPath("compile_output_pak")}>
        Compiled pak66 VPK
      </button>
      <button onclick={() => openDevPath("dota2_tools")}>
        Dota2 Tools
      </button>
    </div>
  </div>

  <div class="section">
    <div class="section-header">{_("devtools_workarounds", "Workarounds")}</div>
    <div class="btn-grid">
      <button class="btn-action" onclick={compileAssets}>
        Compile assets
      </button>
      <button onclick={selectCompileDir}>
        Select path to compile
      </button>
      <button onclick={compileFromCustom}>
        Compile items from path
      </button>
      <button onclick={() => setAllMods(true)}>
        Tick all mods
      </button>
      <button onclick={() => setAllMods(false)}>
        Untick all mods
      </button>
      <button class="btn-danger" onclick={wipeLanguagePaths}>
        Wipe language paths
      </button>
      <button onclick={extractWorkshopTools}>
        Extract workshop tools
      </button>
      <button onclick={launchSteam}>
        Launch Steam
      </button>
      <button onclick={killSteam}>
        Kill Steam
      </button>
      <button onclick={validateDota2}>
        Validate Dota 2
      </button>
    </div>
  </div>

  <div class="section">
    <div class="section-header">{_("devtools_debugging", "Debugging")}</div>
    <div class="btn-grid">
      <button class="btn-action" onclick={createDebugZip}>
        Create debug zip
      </button>
      <button onclick={() => openDevPath("logs")}>
        Open logs
      </button>
      <button onclick={() => openDevPath("config")}>
        Open config
      </button>
    </div>
  </div>
</div>

<style>
  .devtools {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    padding: 10px 14px;
    gap: 16px;
    flex: 1;
    margin-right: 3px;
  }

  .devtools::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .section { display: flex; flex-direction: column; gap: 6px; }

  .btn-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .devtools button {
    background: var(--bg-surface);
    font-size: 12px;
    font-weight: 500;
  }

  .btn-action {
    font-weight: 600;
  }

  .btn-action:hover:not(:disabled) {
    background: rgba(0, 230, 230, 0.06);
    color: var(--accent);
    border-color: var(--accent);
  }

  .btn-danger:hover:not(:disabled) {
    background: rgba(255, 68, 68, 0.08);
    color: var(--red);
    border-color: var(--red);
  }

  .btn-danger:focus-visible,
  :global(html.keyboard-focus) .btn-danger:focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }
</style>
