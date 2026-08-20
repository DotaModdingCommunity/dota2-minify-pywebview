<script lang="ts">
  import { terminalStore, resolveLine, resolveText } from '$lib/stores/terminal'
  import { hudStore } from '$lib/stores/hud'
  import { localeStore } from '$lib/stores/locale'
import { smoothscroll } from '$lib/actions/smoothscroll'
import { fade } from 'svelte/transition'
import ProgressBar from './ProgressBar.svelte'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let {
    onClose,
  }: {
    onClose?: () => void
  } = $props()

  let container = $state<HTMLDivElement | undefined>(undefined)
  let isScrolledUp = $state(false)

  let pct = $derived.by(() => {
    const v = $hudStore?.value ?? 0
    return Math.round(v <= 1 ? v * 100 : Math.min(100, v))
  })
  let active = $derived($hudStore?.visible ?? false)
  let statusText = $derived(
    active
      ? resolveText($hudStore?.status ?? '', $hudStore?.args ?? [], _t).trim() ||
        resolveText($hudStore?.messages?.[0] ?? '', [], _t).trim()
      : ''
  )

  function onScroll() {
    if (container) {
      isScrolledUp = container.scrollHeight - container.clientHeight - container.scrollTop > 40
    }
  }

  $effect(() => {
    $terminalStore;
    if (container && !isScrolledUp) container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' })
  })

  function close() {
    onClose?.()
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close()
  }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="terminal" in:fade={{ duration: 200 }}>
  <div class="term-header">
    <span class="term-title">{_("terminal", "Terminal")}</span>
    {#if active}
      <ProgressBar {pct} style="flex:1;min-width:80px;height:5px" />
      <span class="term-status">{statusText}</span>
    {/if}
  </div>

  <div class="term-log" bind:this={container} tabindex="-1" data-scrollable onscroll={onScroll} use:smoothscroll>
    {#each $terminalStore as line}
      {#if line.type === '__sep__'}
        <div class="line sep"></div>
      {:else}
        <div class="line" class:error={line.type === 'error'} class:warning={line.type === 'warning'} class:success={line.type === 'success'} class:section={line.type === 'section'} class:detail={line.type === 'detail'}>{resolveLine(line, _t)}</div>
      {/if}
    {/each}
  </div>
</div>

<style>
  .terminal {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .term-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--bg-surface);
    flex-shrink: 0;
  }

  .term-title {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    flex-shrink: 0;
  }

  .term-status {
    max-width: 40%;
    min-width: 0;
    font-size: 11px;
    color: var(--text-dim);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
  }

  .term-log {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    outline: none;
    background: var(--bg);
    padding: 8px 14px;
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 1.5;
    user-select: text;
    cursor: text;
    margin-right: 3px;
  }

  .term-log::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .line { color: var(--text); white-space: pre-wrap; word-break: break-word; animation: term-line-in 180ms ease-out; }
  .line.error { color: var(--red); font-weight: 600; }
  .line.warning { color: var(--yellow); font-weight: 600; }
  .line.success { color: var(--green); font-weight: 600; }
  .line.section { color: var(--accent); font-weight: 600; }
  .line.detail { color: var(--text-dim); --slide: -8px; }
  .line.sep { height: 0; border-top: 1px dashed var(--border); margin: 6px 0; animation: term-sep-in 180ms ease-out; }

  @keyframes term-line-in {
    from { opacity: 0; transform: translateX(var(--slide, -14px)); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes term-sep-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }
</style>