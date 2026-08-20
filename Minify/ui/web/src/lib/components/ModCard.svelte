<script module lang="ts">
  const previewCache = new Map<string, string>()
</script>

<script lang="ts">
  import type { CardItem } from '$lib/api'
  import ModStatusBadge from './ModStatusBadge.svelte'
  import Toggle from './Toggle.svelte'
  import { localeStore } from '$lib/stores/locale'
  import { settingsStore } from '$lib/stores/settings'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { item, onToggle, onShowDetails, onSettings, getPreview, variantCircles, activeVariant, onSelectVariant, previewKey }: {
    item: CardItem
    onToggle?: (enabled: boolean) => void
    onShowDetails?: () => void
    onSettings?: () => void
    getPreview?: () => Promise<string | null>
    variantCircles?: { color?: string; enabled?: boolean }[]
    activeVariant?: number
    onSelectVariant?: (index: number) => void
    previewKey?: string
  } = $props()

  const RETRY_BASE_MS = 1500
  const RETRY_CAP_MS = 60_000

  let previewSrc = $state<string | null>(null)
  let previewLoading = $state(true)
  let previewRetry = $state(0)
  let retryDelay = RETRY_BASE_MS
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let lastCacheKey: string | undefined
  let previewEl: HTMLDivElement
  let visible = $state(false)
  const cacheKey = $derived(previewKey ?? item.id)
  const isVideo = $derived(previewSrc?.startsWith('data:video/') ?? false)
  const videoAutoplay = $derived(($settingsStore?.values?.global?.d2pfx_video_autoplay as boolean | undefined) !== false)
  let videoEl = $state<HTMLVideoElement | undefined>()

  $effect(() => {
    if (!videoEl) return
    if (videoAutoplay) { if (videoEl.paused) videoEl.play().catch(() => {}) }
    else videoEl.pause()
  })

  // Only start loading once the card actually scrolls near the viewport.
  // Without this, every card in a big category fires its preview fetch
  // on mount at once, regardless of whether it's ever seen.
  $effect(() => {
    if (!previewEl) return
    if (previewCache.has(cacheKey)) { visible = true; return }
    const obs = new IntersectionObserver((entries) => {
      if (entries[0]?.isIntersecting) {
        visible = true
        obs.disconnect()
      }
    }, { rootMargin: '150px' })
    obs.observe(previewEl)
    return () => obs.disconnect()
  })

  $effect(() => {
    if (!item.hasPreview || !getPreview) {
      previewSrc = null
      previewLoading = false
      return
    }
    if (lastCacheKey !== cacheKey) {
      lastCacheKey = cacheKey
      retryDelay = RETRY_BASE_MS
    }
    const cached = previewCache.get(cacheKey)
    if (cached) {
      previewSrc = cached
      previewLoading = false
      return
    }
    if (!visible) return
    void previewRetry
    previewLoading = true
    let cancelled = false
    getPreview()
      .then(res => {
        if (cancelled) return
        if (res) {
          previewCache.set(cacheKey, res)
          previewSrc = res
          previewLoading = false
          retryDelay = RETRY_BASE_MS
        } else {
          scheduleRetry()
        }
      })
      .catch(scheduleRetry)
    return () => { cancelled = true; clearTimeout(retryTimer) }
  })

  function scheduleRetry() {
    retryTimer = setTimeout(() => { previewRetry++ }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, RETRY_CAP_MS)
  }
</script>

<div class="card" class:enabled={item.enabled} class:unsupported={item.unsupported}>
  <div class="preview" role="button" tabindex="0" bind:this={previewEl}
    onclick={onShowDetails}
    onkeydown={(e: KeyboardEvent) => { if ((e.key === 'Enter' || e.key === ' ') && onShowDetails && e.target === e.currentTarget) { e.preventDefault(); onShowDetails() } }}>
    {#if previewSrc}
      {#if isVideo}
        <video bind:this={videoEl} src={previewSrc} muted autoplay={videoAutoplay} loop playsinline></video>
      {:else}
        <img src={previewSrc} alt={item.name} decoding="async" />
      {/if}
    {:else if previewLoading}
      <div class="shimmer"></div>
    {:else}
      <div class="placeholder" data-letter={item.name[0]}></div>
    {/if}
    {#if (item.status && item.status !== 'working') || item.isBase}
      <div class="badge-overlay">
        {#if item.status && item.status !== 'working'}
          <ModStatusBadge status={item.status} />
        {/if}
        {#if item.isBase}
          <span class="base-badge">BASE</span>
        {/if}
      </div>
    {/if}
    {#if variantCircles && variantCircles.length > 0}
      <div class="variant-circles">
        {#each variantCircles as circle, i}
          <button
            class="variant-dot"
            class:active={i === activeVariant}
            style:background={circle.color ?? 'var(--text-dim)'}
            onclick={(e: MouseEvent) => {
              e.stopPropagation()
              onSelectVariant?.(i)
            }}
            title={circle.color ?? ''}
            aria-label={`Variant ${i + 1}`}
          ></button>
        {/each}
      </div>
    {/if}
  </div>

  <div class="body">
    <div class="name-row">
      <span class="mod-name">{item.displayName ?? item.name}</span>
      {#if item.version}
        <span class="mod-version">v{item.version}</span>
      {/if}
    </div>
    {#if item.author}
      <div class="author">{item.author}</div>
    {/if}
    {#if item.tags.length > 0}
      <div class="tags">
        {#each item.tags.slice(0, 4) as tag}
          <span class="tag-pill">{tag}</span>
        {/each}
      </div>
    {/if}
  </div>

  <div class="card-row">
    {#if !item.isBase && !item.unsupported}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div class="toggle-row" role="none" onclick={() => onToggle?.(!item.enabled)}>
        <Toggle checked={item.enabled} onchange={() => onToggle?.(!item.enabled)} />
        <span class="toggle-label">{item.enabled ? _("enabled", "Enabled") : _("disabled", "Disabled")}</span>
      </div>
    {/if}
    {#if item.hasSettings && !item.unsupported}
      <button class="btn-settings" onclick={() => onSettings?.()}>
        {_("settings", "Settings")}
      </button>
    {/if}
  </div>
</div>

<style>
  .card {
    position: relative;
    height: 100%;
    box-sizing: border-box;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    padding: 8px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.15s, background 0.15s, box-shadow 0.2s ease-out;
    cursor: default;
  }

  .card:hover {
    background: var(--bg-hover);
    box-shadow: var(--shadow-floating);
  }

  .card.enabled {
    border-color: var(--accent-dim);
  }

  .card.unsupported { opacity: 0.45; }

  .preview {
    width: 100%;
    aspect-ratio: 16 / 9;
    flex-shrink: 0;
    overflow: hidden;
    background: var(--bg-raised);
    display: grid;
    grid-template: 1fr / 1fr;
    align-items: center;
    justify-items: center;
    cursor: pointer;
    position: relative;
    border-radius: 5px;
  }

  .preview:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }

  .preview:focus-visible .placeholder::after {
    color: var(--accent);
    opacity: 1;
  }

  .preview img, .preview video { grid-area: 1 / 1; width: 100%; height: 100%; object-fit: cover; border-radius: 5px; }

  .badge-overlay {
    position: absolute;
    top: 4px;
    right: 4px;
    display: flex;
    gap: 3px;
  }

  .variant-circles {
    position: absolute;
    bottom: 6px;
    left: 6px;
    display: flex;
    gap: 5px;
  }

  .variant-dot {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: none;
    padding: 0;
    cursor: pointer;
    flex-shrink: 0;
    transition: transform 0.12s, box-shadow 0.12s;
  }

  .variant-dot:hover { transform: scale(1.15); }

  .variant-dot:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 1px;
  }

  .base-badge {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 1px 5px;
    background: var(--bg);
    border: 1px solid var(--accent);
    color: var(--accent);
    border-radius: 4px;
  }

  .placeholder {
    grid-area: 1 / 1;
    width: 100%;
    height: 100%;
    background: linear-gradient(155deg, var(--bg-raised), var(--bg-surface) 65%);
  }

  .shimmer {
    grid-area: 1 / 1;
    width: 100%;
    height: 100%;
    position: relative;
    overflow: hidden;
    background: var(--bg-raised);
    border-radius: 5px;
  }

  .shimmer::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      105deg,
      transparent 25%,
      rgba(154, 154, 165, 0.12) 42%,
      rgba(154, 154, 165, 0.2) 50%,
      rgba(154, 154, 165, 0.12) 58%,
      transparent 75%
    );
    transform: translateX(-100%);
    pointer-events: none;
    animation: shimmer 5s ease-in-out infinite;
  }

  @keyframes shimmer {
    0%   { transform: translateX(-100%); }
    40%  { transform: translateX(100%); }
    100% { transform: translateX(100%); }
  }

  .placeholder::after {
    content: attr(data-letter);
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
    font-weight: 700;
    text-transform: uppercase;
    font-family: var(--font-ui);
    color: var(--text-muted);
    opacity: 0.3;
  }

  .body { display: flex; flex-direction: column; gap: 1px; }

  .name-row {
    display: flex;
    align-items: baseline;
    gap: 4px;
    min-width: 0;
  }

  .mod-name {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    min-width: 0;
  }

  .mod-version {
    font-size: 10px;
    color: var(--text-dim);
    margin-left: auto;
    flex-shrink: 0;
  }

  .author {
    font-size: 10px;
    color: var(--text-dim);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tags {
    display: flex;
    flex-wrap: nowrap;
    overflow: hidden;
    gap: 3px;
  }

  .tag-pill {
    font-size: 9px;
    padding: 1px 5px;
    background: rgba(0, 230, 230, 0.14);
    border: 1px solid var(--accent-glow);
    color: var(--accent);
    border-radius: 4px;
    line-height: 1.4;
    white-space: nowrap;
  }

  .card-row {
    display: flex;
    align-items: center;
    gap: 5px;
    margin-top: auto;
  }

  .btn-settings {
    font-size: 11px;
    padding: 3px 9px;
    margin-left: auto;
    border-radius: 4px;
  }

  .toggle-row {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    user-select: none;
  }

  .toggle-label { font-size: 10px; color: var(--text-dim); }
</style>
