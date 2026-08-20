<script lang="ts">
  import { fade } from 'svelte/transition'
  import { onMount, onDestroy } from 'svelte'
  import type { Mod, CardItem, SetModEnabledResult } from '$lib/api'
  import { ready } from '$lib/stores/bridge'
  import { modsStore } from '$lib/stores/mods'
  import { searchQuery } from '$lib/stores/search'
  import { scrollPositions } from '$lib/stores/scroll'
  import { get } from 'svelte/store'
  import ModSettings from './ModSettings.svelte'
  import ModCard from './ModCard.svelte'
  import VirtualGrid from './VirtualGrid.svelte'
  import ModDetails from './ModDetails.svelte'
  import SkeletonGrid from './SkeletonGrid.svelte'
  import { modalStore } from '$lib/stores/modal'
  import { localeStore } from '$lib/stores/locale'
  import { detailOverlayOpen } from '$lib/stores/overlay'

  let _t = $derived($localeStore.t)
  let loading = $state(true)
  let { refreshing = false }: { refreshing?: boolean } = $props()
  let dragOver = $state(false)
  let showDetailsMod = $state<Mod | null>(null)
  let showSettingsMod = $state<Mod | null>(null)

  $effect(() => {
    detailOverlayOpen.set(showDetailsMod !== null || showSettingsMod !== null)
  })

  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let _loaded = false

  $effect(() => {
    if ($ready && !_loaded) {
      _loaded = true
      loadMods()
    }
  })

  async function loadMods() {
    const fallback = setTimeout(() => {
      if (loading) {
        modalStore.set({ title: "Error", messages: ["Loading mods timed out — check backend connection"], buttons: ["OK"] })
        loading = false
      }
    }, 10_000)

    try {
      const res = await window.pywebview.api.get_mods()
      if (res.ok) {
        modsStore.set(res.data)
      } else {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [`Failed to load mods: ${e}`], buttons: ["OK"] })
      console.error(e)
    } finally {
      clearTimeout(fallback)
      if (loading) {
        loading = false
      }
    }
  }

  function modToCardItem(mod: Mod): CardItem {
    return {
      id: mod.raw_name,
      name: mod.name,
      author: mod.author || undefined,
      tags: mod.tags,
      version: mod.version || undefined,
      status: mod.status,
      isBase: mod.always || undefined,
      unsupported: mod.unsupported || undefined,
      enabled: mod.enabled,
      hasSettings: mod.hasSettings || undefined,
      hasPreview: mod.hasPreview || undefined,
      hasNotes: mod.hasNotes || undefined,
    }
  }

  let filteredMods = $derived.by(() => {
    let list = $modsStore
    const q = $searchQuery.trim().toLowerCase()
    if (q) list = list.filter(m => m.name.toLowerCase().includes(q))
    return list
  })

  let cardItems = $derived(
    filteredMods.map(modToCardItem).sort((a, b) => {
      if (a.isBase && !b.isBase) return -1;
      if (!a.isBase && b.isBase) return 1;
      return (a.unsupported ? 1 : 0) - (b.unsupported ? 1 : 0);
    })
  )

  function displayName(rawName: string): string {
    return $modsStore.find(m => m.raw_name === rawName)?.name ?? rawName
  }

  async function applyEnable(rawName: string, disabled: string[] = []) {
    try {
      const res = await window.pywebview.api.set_mod_enabled(rawName, true, true)
      if (res.ok) {
        modsStore.update(list =>
          list.map(m =>
            m.raw_name === rawName
              ? { ...m, enabled: true }
              : disabled.includes(m.raw_name)
                ? { ...m, enabled: false }
                : m
          )
        )
      } else {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [`Failed to toggle mod: ${e}`], buttons: ["OK"] })
    }
  }

  async function toggleMod(rawName: string, enabled: boolean) {
    try {
      const res = await window.pywebview.api.set_mod_enabled(rawName, enabled)
      if (res.ok) {
        const data: SetModEnabledResult = res.data ?? {}
        if (data.needs_confirmation && data.conflicts?.length) {
          const names = data.conflicts.map(displayName).join(", ")
          modalStore.set({
            title: _("mod_conflict_title", "Mod Conflict"),
            messages: [_("mod_conflict_msg", 'Enabling "{0}" conflicts with enabled mods: {1}. Disable them and enable "{0}"?').replace(/\{0\}/g, displayName(rawName)).replace("{1}", names)],
            buttons: [_("cancel", "Cancel"), _("mod_conflict_confirm", "Proceed")],
            onrespond: (label) => {
              if (label === _("mod_conflict_confirm", "Proceed")) {
                applyEnable(rawName, data.conflicts ?? [])
              }
            },
          })
          return
        }
        modsStore.update(list =>
          list.map(m => m.raw_name === rawName ? { ...m, enabled } : m)
        )
      } else {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [`Failed to toggle mod: ${e}`], buttons: ["OK"] })
    }
  }

  function handleSettings(mod: Mod) {
    showSettingsMod = mod
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault()
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy'
  }

  function handleDragEnter(e: DragEvent) {
    if (Date.now() < suppressDragUntil) return
    if (!e.dataTransfer || !Array.from(e.dataTransfer.types).includes('Files')) return
    e.preventDefault()
    dragOver = true
  }

  function handleDragLeave(e: DragEvent) {
    const related = e.relatedTarget as Node | null
    if (related && e.currentTarget instanceof Node && (e.currentTarget as Node).contains(related)) return
    dragOver = false
  }

  function handleDrop() {
    dragOver = false
  }

  function endDrag() {
    dragOver = false
    // WebView2 may re-fire dragenter after a native file drop; ignore
    // re-enters briefly so the overlay doesn't flash back up mid-install.
    suppressDragUntil = Date.now() + 1000
  }

  let suppressDragUntil = 0

  onMount(() => {
    function onDropEnd() { endDrag() }
    window.addEventListener('dropcomplete', onDropEnd)
    const onWinDrop = () => endDrag()
    const onWinDragEnd = () => endDrag()
    window.addEventListener('drop', onWinDrop, true)
    window.addEventListener('dragend', onWinDragEnd, true)
    onDestroy(() => {
      window.removeEventListener('dropcomplete', onDropEnd)
      window.removeEventListener('drop', onWinDrop, true)
      window.removeEventListener('dragend', onWinDragEnd, true)
    })
  })
</script>

<div class="mod-grid-scroll-wrapper" role="none" class:drop-target={dragOver} class:refreshing
     ondragover={handleDragOver} ondragenter={handleDragEnter} ondragleave={handleDragLeave} ondrop={handleDrop}>
  {#if loading}
    <SkeletonGrid />
  {:else if $modsStore.length === 0 || ($searchQuery && filteredMods.length === 0)}
    <div class="empty" in:fade={{ duration: 200 }}>
      {#if $searchQuery && $modsStore.length > 0}
        <span>{_("no_mods_search", "No mods match your search.")}</span>
      {:else}
        <svg class="empty-icon" viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="9" y1="13" x2="15" y2="13"/>
          <line x1="12" y1="10" x2="12" y2="16"/>
        </svg>
        <span>{_("no_mods", "No mods found.")}</span>
      {/if}
    </div>
  {:else}
    <div class="grid-fill" in:fade={{ duration: 200 }}>
      <VirtualGrid
        items={cardItems}
        itemKey={(it) => it.id}
        initialScrollTop={get(scrollPositions)['mods']}
        onScrollTop={(n) => scrollPositions.update(p => ({ ...p, mods: n }))}
      >
        {#snippet children(item)}
          <ModCard
            {item}
            onToggle={(enabled) => toggleMod(item.id, enabled)}
            onShowDetails={() => {
              const mod = $modsStore.find(m => m.raw_name === item.id)
              if (mod && (mod.hasNotes || mod.hasPreview)) showDetailsMod = mod
            }}
            onSettings={() => handleSettings($modsStore.find(m => m.raw_name === item.id)!)}
            getPreview={() => window.pywebview.api.get_mod_preview(item.id).then(r => r.ok ? r.data : null)}
          />
        {/snippet}
      </VirtualGrid>
    </div>
  {/if}

  {#if dragOver}
    <div class="drop-overlay" in:fade={{ duration: 100 }} role="none">
      <div class="drop-label">
        <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <span>Drop mod folder, .zip or .vpk</span>
      </div>
    </div>
  {/if}
</div>

{#if showDetailsMod}
  <ModDetails mod={showDetailsMod} onClose={() => showDetailsMod = null} />
{/if}

{#if showSettingsMod}
  <ModSettings mod={showSettingsMod} onClose={() => showSettingsMod = null} />
{/if}

<style>
  .empty {
    color: var(--text-dim);
    padding: 48px 24px;
    text-align: center;
    font-size: 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex: 1;
    min-height: 0;
  }

  .empty-icon {
    color: var(--text-muted);
    opacity: 0.4;
  }

  .mod-grid-scroll-wrapper {
    flex: 1;
    min-height: 0;
    position: relative;
    display: flex;
  }

  .mod-grid-scroll-wrapper.refreshing::after {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 5;
    background: linear-gradient(
      105deg,
      transparent 25%,
      rgba(154, 154, 165, 0.08) 42%,
      rgba(154, 154, 165, 0.14) 50%,
      rgba(154, 154, 165, 0.08) 58%,
      transparent 75%
    );
    transform: translateX(-100%);
    pointer-events: none;
    animation: gridSweep 0.7s ease-out forwards;
  }

  @keyframes gridSweep {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }

  .grid-fill {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .drop-overlay {
    position: absolute;
    inset: 0;
    z-index: 10;
    background: rgba(0, 0, 0, 0.45);
    border: 2px dashed var(--accent-dim);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }

  .drop-label {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 26px 44px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-floating);
    color: var(--accent);
    font-size: 12px;
    font-weight: 500;
  }

  .drop-target {
    outline: 2px dashed var(--accent-dim);
    outline-offset: -2px;
  }
</style>
