<script lang="ts">
  import type { D2pfxCategory } from '$lib/api'
import { localeStore } from '$lib/stores/locale'
import { onMount } from 'svelte'
import { fade } from 'svelte/transition'
  import { scrollPositions } from '$lib/stores/scroll'
  import { get } from 'svelte/store'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { categories, selected, onSelect }: {
    categories: D2pfxCategory[]
    selected: string | null
    onSelect: (id: string) => void
  } = $props()

  let filter = $state('')
  let listEl: HTMLDivElement
  let filtered = $derived(
    filter ? categories.filter(c => c.name.toLowerCase().includes(filter.toLowerCase())) : categories
  )

  onMount(() => {
    const pos = get(scrollPositions)['d2pfx-cat']
    if (pos > 0 && listEl) listEl.scrollTop = pos
  })


</script>

<div class="sidebar" in:fade={{ duration: 200 }}>
  <input id="d2pfx-cat-search" type="text" class="search" placeholder={_("d2pfx_search_categories", "Search categories\u2026")} aria-label={_("d2pfx_search_categories", "Search categories\u2026")} bind:value={filter} />
  <div class="list" bind:this={listEl} data-scrollable
     onscroll={() => scrollPositions.update(p => ({ ...p, 'd2pfx-cat': listEl.scrollTop }))} use:smoothscroll>
    {#each filtered as cat (cat.id)}
      <button
        class="cat-item"
        class:active={cat.id === selected}
        onclick={() => onSelect(cat.id)}
      >
        {cat.name}
      </button>
    {/each}
    {#if filtered.length === 0}
      <div class="empty">{_("d2pfx_no_categories", "No categories")}</div>
    {/if}
  </div>
</div>

<style>
  .sidebar {
    width: 160px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
  }

  .search {
    margin: 8px;
    padding: 4px 8px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 11px;
    font-family: inherit;
    outline: none;
    border-radius: var(--radius-sm);
  }

  .search:focus { border-color: var(--accent-dim); outline: 2px solid var(--accent); outline-offset: -2px; box-shadow: none; }

  .list {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1px;
    margin-right: 3px;
  }

  .list::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .cat-item {
    text-align: left;
    padding: 6px 12px;
    font-size: 11.5px;
    border: none;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    border-left: 2px solid transparent;
    margin-right: 3px;
  }

  .cat-item:hover { color: var(--text); background: var(--bg-hover); }

  .cat-item.active {
    color: var(--accent);
    border-left-color: var(--accent);
    background: rgba(0, 230, 230, 0.06);
  }

  .empty {
    padding: 12px;
    font-size: 11px;
    color: var(--text-dim);
    text-align: center;
  }


</style>
