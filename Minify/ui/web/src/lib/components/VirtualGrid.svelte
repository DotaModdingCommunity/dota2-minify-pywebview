<script lang="ts" generics="T">
  import type { Snippet } from 'svelte'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  interface Props<T> {
    items: T[]
    itemKey: (item: T) => string
    children: Snippet<[T]>
    gap?: number
    initialScrollTop?: number
    onScrollTop?: (n: number) => void
  }

  let {
    items,
    itemKey,
    children,
    gap = 10,
    initialScrollTop = 0,
    onScrollTop,
  }: Props<T> = $props()

  const BUFFER_ROWS = 2
  const GRID_PADDING_X = 10
  const GRID_PAD_Y = 16
  const MIN_COL_WIDTH = 280
  const MAX_COL_WIDTH = 400
  const CONTENT_H = 92

  let scrollEl: HTMLDivElement
  let scrollTop = $state(0)
  let viewportH = $state(0)
  let cols = $state(1)
  let cardW = $state(MIN_COL_WIDTH)
  let rafPending = false
  let appliedInit = false

  let rowHeight = $derived(Math.round(cardW * 9 / 16) + CONTENT_H)
  let totalRows = $derived(Math.max(0, Math.ceil(items.length / Math.max(1, cols))))
  let row0 = $derived(Math.max(0, Math.floor(scrollTop / rowHeight) - BUFFER_ROWS))
  let row1 = $derived(Math.min(totalRows, Math.ceil((scrollTop + viewportH) / rowHeight) + BUFFER_ROWS))
  let visible = $derived(items.slice(row0 * cols, row1 * cols))
  let topPad = $derived(row0 * rowHeight)
  let bottomPad = $derived(Math.max(0, (totalRows - row1) * rowHeight))
  let totalHeight = $derived(Math.max(0, totalRows * rowHeight + GRID_PAD_Y))
  let maxScroll = $derived(Math.max(0, totalHeight - viewportH))

  function handleScroll() {
    if (rafPending) return
    rafPending = true
    requestAnimationFrame(() => {
      rafPending = false
      if (!scrollEl) return
      scrollTop = scrollEl.scrollTop
      onScrollTop?.(scrollTop)
    })
  }

  function clampScroll() {
    if (!scrollEl || scrollTop <= maxScroll) return
    scrollEl.scrollTop = maxScroll
    scrollTop = maxScroll
  }

  $effect(() => {
    if (!scrollEl) return
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) {
        if (e.target !== scrollEl) continue
        viewportH = e.contentRect.height
        const availW = e.contentRect.width - GRID_PADDING_X
        cols = Math.max(1, Math.floor((availW + gap) / (MIN_COL_WIDTH + gap)))
        const idealW = Math.floor((availW - (cols - 1) * gap) / cols)
        cardW = Math.min(MAX_COL_WIDTH, Math.max(MIN_COL_WIDTH, idealW))
      }
    })
    obs.observe(scrollEl)
    return () => obs.disconnect()
  })

  $effect(() => {
    if (appliedInit || !scrollEl) return
    appliedInit = true
    if (initialScrollTop > 0) scrollEl.scrollTop = initialScrollTop
  })

  $effect(() => {
    if (!scrollEl) return
    maxScroll
    scrollTop
    clampScroll()
  })
</script>

<div
  class="vg-scroll"
  bind:this={scrollEl}
  data-scrollable
  role="none"
  onscroll={handleScroll}
  use:smoothscroll
>
  <div class="vg-spacer" style:height="{topPad}px"></div>
  <div class="vg-grid" style:grid-template-columns="repeat({cols}, minmax(0, {cardW}px))">
    {#each visible as item (itemKey(item))}
      <div class="vg-item" style:height="{rowHeight - gap}px">{@render children(item)}</div>
    {/each}
  </div>
  <div class="vg-spacer" style:height="{bottomPad}px"></div>
</div>

<style>
  .vg-scroll {
    flex: 1;
    min-height: 0;
    overflow-x: hidden;
    overflow-y: auto;
    overflow-anchor: none;
    margin-left: 2px;
    margin-right: 3px;
  }

  .vg-scroll::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .vg-grid {
    display: grid;
    gap: 10px;
    padding: 8px 3px 8px 6px;
    align-content: start;
    justify-content: center;
  }

  .vg-item {
    width: 100%;
  }
</style>
