<script lang="ts">
  import { fade } from 'svelte/transition'
  import { onMount, onDestroy } from 'svelte'

  import { scrollPositions } from '$lib/stores/scroll'
  import { get } from 'svelte/store'
  import type { D2pfxMod, D2pfxVariant, CardItem } from '$lib/api'
  import { localeStore } from '$lib/stores/locale'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }
  import {
    d2pfxCategories, d2pfxMods, selectedCategory,
    d2pfxLoading
  } from '$lib/stores/d2pfx'
  import { searchQuery } from '$lib/stores/search'
  import { modalStore } from '$lib/stores/modal'
  import { detailOverlayOpen } from '$lib/stores/overlay'
  import D2pfxCategoryList from './D2pfxCategoryList.svelte'
  import D2pfxModDetails from './D2pfxModDetails.svelte'
  import ModCard from './ModCard.svelte'
  import VirtualGrid from './VirtualGrid.svelte'
  import SkeletonGrid from './SkeletonGrid.svelte'

  // Stable preview-fetch closures: the card's preview $effect tracks the
  // `getPreview` prop by identity, so a fresh closure per render would cancel
  // and restart in-flight fetches (stuck previews / placeholder flashes on
  // fast variant switching). Memoize per (category, filename) instead.
  const stablePreviewFns = new Map<string, () => Promise<string | null>>()
  function previewFn(catId: string, filename: string): () => Promise<string | null> {
    const key = `${catId}:${filename}`
    let fn = stablePreviewFns.get(key)
    if (!fn) {
      fn = () => window.pywebview.api.get_d2pfx_preview(catId, filename).then(r => (r.ok ? r.data : null))
      stablePreviewFns.set(key, fn)
    }
    return fn
  }

  let { refreshing = false }: { refreshing?: boolean } = $props()

  let showDetailsMod = $state<D2pfxMod | null>(null)
  let selectedVariant = $state<Record<string, string>>({})

  function selectedVariantIndex(mod: D2pfxMod, variants: D2pfxVariant[]): number {
    const saved = selectedVariant[mod.modDirName]
    if (saved && variants.length > 0) {
      const i = variants.findIndex(v => v.modDirName === saved)
      if (i >= 0) return i
    }
    const enabled = variants.findIndex(v => v.enabled)
    return enabled >= 0 ? enabled : 0
  }

  $effect(() => {
    detailOverlayOpen.set(showDetailsMod !== null)
  })

  const RETRY_BASE_MS = 1500
  const RETRY_CAP_MS = 60_000
  let retryDelay = RETRY_BASE_MS
  let retryTimer: ReturnType<typeof setTimeout> | undefined

  onMount(() => {
    loadCategories()
    loadSavedVariantSelection()
  })

  onDestroy(() => clearTimeout(retryTimer))

  async function loadSavedVariantSelection() {
    try {
      const res = await window.pywebview.api.get_d2pfx_selected_variants()
      if (res.ok && res.data) selectedVariant = { ...res.data }
    } catch {
      // ignore
    }
  }

  async function loadCategories() {
    d2pfxLoading.set(true)
    try {
      for (let i = 0; i < 30; i++) {
        const state = await window.pywebview.api.get_d2pfx_state()
        if (!state.ok) { scheduleRetry(); return }
        if (state.data.loaded) break
        if (!state.data.loading) {
          window.pywebview.api.reload_d2pfx()
          scheduleRetry()
          return
        }
        await new Promise(r => setTimeout(r, 1000))
      }
      const res = await window.pywebview.api.get_d2pfx_categories()
      if (res.ok) {
        d2pfxCategories.set(res.data)
        if (res.data.length > 0) {
          const saved = get(selectedCategory)
          const catId = saved && res.data.some(c => c.id === saved) ? saved : res.data[0].id
          selectedCategory.set(catId)
          if (!get(d2pfxMods)[catId]) await loadMods(catId)
        }
        retryDelay = RETRY_BASE_MS
        d2pfxLoading.set(false)
      } else {
        scheduleRetry()
      }
    } catch {
      scheduleRetry()
    }
  }

  function scheduleRetry() {
    clearTimeout(retryTimer)
    retryTimer = setTimeout(() => { loadCategories() }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, RETRY_CAP_MS)
  }

  async function loadMods(id: string) {
    const res = await window.pywebview.api.get_d2pfx_mods(id)
    if (res.ok) {
      d2pfxMods.update(m => ({ ...m, [id]: res.data }))
    } else {
      modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
    }
  }

  async function selectCategory(id: string) {
    selectedCategory.set(id)
    d2pfxLoading.set(true)
    try {
      await loadMods(id)
    } finally {
      d2pfxLoading.set(false)
    }
  }

  function applyVariantState(catId: string, modDirName: string, enabled: boolean, targetDir: string) {
    d2pfxMods.update(m => {
      const list = (m[catId] ?? []).map(x => {
        if (x.modDirName !== modDirName) return x
        const variants = x.variants ?? []
        if (variants.length > 0) {
          const updated = variants.map(v => ({
            ...v,
            enabled: v.modDirName === targetDir
              ? enabled
              : enabled ? false : v.enabled,
          }))
          return { ...x, variants: updated, enabled: updated.some(v => v.enabled) }
        }
        return { ...x, enabled }
      })
      return { ...m, [catId]: list }
    })
  }

  async function toggleMod(catId: string, mod: D2pfxMod, enabled: boolean) {
    const variants = mod.variants ?? []
    const idx = selectedVariantIndex(mod, variants)
    const variant = variants[idx] ?? mod
    const disableOthers = variants.length > 0
      ? variants.filter(v => v.modDirName !== variant.modDirName).map(v => v.modDirName)
      : []
    // Apply optimistically so the UI responds instantly instead of flickering
    // between stale and confirmed enabled states while the backend call is in flight.
    if (enabled && variants.length > 0) {
      selectedVariant[mod.modDirName] = variant.modDirName
      persistVariantSelection()
    }
    applyVariantState(catId, mod.modDirName, enabled, variant.modDirName)
    const res = await window.pywebview.api.toggle_d2pfx_mod(
      variant.modDirName, enabled, variant.fileUrl, variant.isZip,
      enabled ? disableOthers : undefined
    )
    if (res.ok) {
      // Re-apply idempotently from the *current* selected variant so an in-flight
      // response can never clobber a newer variant click.
      const current = get(d2pfxMods)[catId]?.find(x => x.modDirName === mod.modDirName)
      if (current) {
        const curVariants = current.variants ?? []
        const curIdx = selectedVariantIndex(current, curVariants)
        const curVariant = curVariants[curIdx]
        if (curVariant && enabled && curVariants.length > 0) {
          selectedVariant[mod.modDirName] = curVariant.modDirName
          persistVariantSelection()
        }
        applyVariantState(catId, mod.modDirName, enabled, curVariant?.modDirName ?? variant.modDirName)
      }
    } else {
      modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
      await loadMods(catId)
    }
  }

  async function selectVariant(catId: string, mod: D2pfxMod, idx: number) {
    const variants = mod.variants ?? []
    selectedVariant[mod.modDirName] = variants[idx]?.modDirName ?? ''
    persistVariantSelection()
    if (variants.length > 0 && variants.some(v => v.enabled)) {
      await toggleMod(catId, mod, true)
    }
  }

  function persistVariantSelection() {
    try {
      window.pywebview.api.set_d2pfx_selected_variants({ ...selectedVariant })
    } catch {
      // ignore
    }
  }

  function d2pfxModToCardItem(mod: D2pfxMod): CardItem {
    const authorParts: string[] = []
    if (mod.author) authorParts.push(Array.isArray(mod.author) ? mod.author.join(', ') : mod.author)
    if (mod.sender) authorParts.push(Array.isArray(mod.sender) ? mod.sender.join(', ') : mod.sender)
    const variants = mod.variants ?? []
    const sel = selectedVariantIndex(mod, variants)
    const variant = variants[sel]
    const name = mod.name
    const label = variant?.label ?? mod.label
    return {
      id: mod.modDirName,
      name,
      displayName: label ? `${name} (${label})` : undefined,
      author: authorParts.join(' · ') || undefined,
      tags: mod.tags,
      enabled: variant ? variant.enabled : mod.enabled,
      hasPreview: !!(variant?.preview || mod.preview),
    }
  }

  let cats = $derived($d2pfxCategories)
  let selCat = $derived($selectedCategory)

  type SortKey = 'name' | 'author' | 'enabled' | ''
  function parseSearchQuery(query: string): { by: string[]; tags: string[]; sortKey: SortKey; terms: string[] } {
    const by: string[] = []
    const tags: string[] = []
    let sortKey: SortKey = ''
    const terms: string[] = []
    const sortKeys: SortKey[] = ['name', 'author', 'enabled']
    for (const token of query.split(/\s+/)) {
      if (!token) continue
      const match = token.match(/^([a-z]+):(.*)$/i)
      if (match) {
        const key = match[1].toLowerCase()
        const value = match[2].toLowerCase()
        if (key === 'by') by.push(value)
        else if (key === 'tag') tags.push(value)
        else if (key === 'sort' && (sortKeys as string[]).includes(value)) sortKey = value as SortKey
        else terms.push(token.toLowerCase())
      } else {
        terms.push(token.toLowerCase())
      }
    }
    return { by, tags, sortKey, terms }
  }

  function modAuthorText(mod: D2pfxMod): string {
    const parts = [mod.author, mod.sender]
      .filter(Boolean)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter(Boolean)
    return parts.join(' ').toLowerCase()
  }

  let currentMods = $derived.by(() => {
    let list = selCat ? ($d2pfxMods[selCat] ?? []) : []
    const q = $searchQuery.trim()
    if (!q) return list
    const { by, tags, sortKey, terms } = parseSearchQuery(q)
    list = list.filter((m) => {
      if (terms.length > 0) {
        const haystack = `${m.name} ${m.label ?? ''}`.toLowerCase()
        if (!terms.every((t) => haystack.includes(t))) return false
      }
      if (by.length > 0) {
        const author = modAuthorText(m)
        if (!by.every((t) => author.includes(t))) return false
      }
      if (tags.length > 0) {
        const modTags = (m.tags ?? []).map((t) => t.toLowerCase())
        if (!tags.every((t) => modTags.some((mt) => mt.includes(t)))) return false
      }
      return true
    })
    if (sortKey === 'name') list = [...list].sort((a, b) => a.name.localeCompare(b.name))
    else if (sortKey === 'author') list = [...list].sort((a, b) => modAuthorText(a).localeCompare(modAuthorText(b)))
    else if (sortKey === 'enabled') list = [...list].sort((a, b) => Number(b.enabled) - Number(a.enabled))
    return list
  })
  let cardItems = $derived(currentMods.map(d2pfxModToCardItem))
  let modsById = $derived.by(() => {
    const map = new Map<string, D2pfxMod>()
    for (const m of currentMods) map.set(m.modDirName, m)
    return map
  })


</script>

<div class="browser">
  <D2pfxCategoryList
    categories={cats}
    selected={selCat}
    onSelect={selectCategory}
  />

  <div class="main" class:refreshing>
    {#if $d2pfxLoading}
      <SkeletonGrid />
    {:else if currentMods.length === 0}
      <div class="empty-state">
        {$searchQuery ? _("d2pfx_no_search_results", "No mods match your search.") : _("d2pfx_empty_category", "No mods in this category.")}
      </div>
    {:else}
      <div class="grid-fill" in:fade={{ duration: 200 }}>
        <VirtualGrid
          items={cardItems}
          itemKey={(it) => it.id}
          initialScrollTop={get(scrollPositions)[`d2pfx:${selCat}`]}
          onScrollTop={(n) => scrollPositions.update(p => ({ ...p, [`d2pfx:${selCat}`]: n }))}
        >
          {#snippet children(item)}
            {@const mod = modsById.get(item.id)}
            {@const variants = mod?.variants ?? []}
            {@const sel = mod ? selectedVariantIndex(mod, variants) : 0}
            {@const selVariant = variants[sel]}
            {@const previewFilename = selVariant?.preview || mod?.preview}
            <ModCard
              {item}
              variantCircles={variants.length > 0
                ? variants.map(v => ({ color: v.color, enabled: v.enabled }))
                : undefined}
              activeVariant={variants.length > 0 ? sel : undefined}
              previewKey={variants.length > 0 && selVariant ? `${item.id}:${sel}` : item.id}
              onSelectVariant={(i: number) => {
                const m = modsById.get(item.id)
                if (m && selCat) selectVariant(selCat, m, i)
              }}
              onToggle={(enabled) => {
                const m = modsById.get(item.id)
                if (m) toggleMod(selCat!, m, enabled)
              }}
              onShowDetails={() => {
                const m = modsById.get(item.id)
                if (m) showDetailsMod = m
              }}
              getPreview={previewFilename
                ? previewFn(selCat!, previewFilename)
                : undefined}
            />
          {/snippet}
        </VirtualGrid>
      </div>
    {/if}
  </div>
</div>

{#if showDetailsMod && selCat}
  {@const detailMod = showDetailsMod}
  <D2pfxModDetails
    mod={detailMod}
    catId={selCat}
    activeVariant={selectedVariantIndex(detailMod, detailMod.variants ?? [])}
    onSelectVariant={(i) => { if (selCat) selectVariant(selCat, detailMod, i) }}
    onClose={() => showDetailsMod = null}
  />
{/if}

<style>
  .browser {
    display: flex;
    flex: 1;
    min-height: 0;
  }

  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    position: relative;
    overflow: hidden;
  }

  .main.refreshing::after {
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
    animation: d2pfxSweep 0.7s ease-out forwards;
  }

  @keyframes d2pfxSweep {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }

  .grid-fill {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }

  .empty-state {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--text-dim);
    font-size: 12px;
    gap: 10px;
  }

</style>
