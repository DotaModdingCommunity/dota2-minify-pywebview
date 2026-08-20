<script lang="ts">
  import type { D2pfxMod } from "$lib/api"
  import { localeStore } from "$lib/stores/locale"
  import { settingsStore } from '$lib/stores/settings'
  import Panel from './Panel.svelte'

  let { mod, catId, onClose, activeVariant = 0, onSelectVariant }: {
    mod: D2pfxMod
    catId: string
    onClose: () => void
    activeVariant?: number
    onSelectVariant?: (index: number) => void
  } = $props()

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  const variants = $derived(mod.variants ?? [])
  const current = $derived(variants[activeVariant] ?? null)

  const RETRY_BASE_MS = 1500
  const RETRY_CAP_MS = 60_000

  let previewSrc = $state<string | null>(null)
  let loading = $state(true)
  let previewRetry = $state(0)
  let retryDelay = RETRY_BASE_MS
  let retryTimer: ReturnType<typeof setTimeout> | undefined
  let lastPreviewKey: string | undefined
  const isVideo = $derived(previewSrc?.startsWith('data:video/') ?? false)
  const videoAutoplay = $derived(($settingsStore?.values?.global?.d2pfx_video_autoplay as boolean | undefined) !== false)
  let videoEl = $state<HTMLVideoElement | undefined>()

  // Two-layer manual crossfade — see ModCard.svelte for why Svelte's `crossfade`
  // transition is avoided inside these keyed preview blocks.
  let prevPreviewSrc = $state<string | null>(null)
  const prevIsVideo = $derived(prevPreviewSrc?.startsWith('data:video/') ?? false)
  let lastPreviewSrc: string | null = null
  let prevFadeTimer: ReturnType<typeof setTimeout> | undefined

  $effect.pre(() => {
    if (previewSrc === lastPreviewSrc) return
    if (lastPreviewSrc) {
      prevPreviewSrc = lastPreviewSrc
      clearTimeout(prevFadeTimer)
      prevFadeTimer = setTimeout(() => { prevPreviewSrc = null }, 170)
    } else {
      prevPreviewSrc = null
    }
    lastPreviewSrc = previewSrc
  })

  $effect(() => {
    return () => clearTimeout(prevFadeTimer)
  })

  $effect(() => {
    if (!videoEl) return
    if (videoAutoplay) { if (videoEl.paused) videoEl.play().catch(() => {}) }
    else videoEl.pause()
  })

  $effect(() => {
    const preview = current?.preview ?? mod.preview
    if (!preview) {
      previewSrc = null
      loading = false
      return
    }
    if (lastPreviewKey !== preview) {
      lastPreviewKey = preview
      retryDelay = RETRY_BASE_MS
    }
    void previewRetry
    let cancelled = false
    loading = true
    window.pywebview.api.get_d2pfx_preview(catId, preview).then(res => {
      if (cancelled) return
      if (res.ok && res.data) {
        previewSrc = res.data
        loading = false
        retryDelay = RETRY_BASE_MS
      } else {
        scheduleRetry()
      }
    }).catch(scheduleRetry)
    return () => { cancelled = true; clearTimeout(retryTimer) }
  })

  function scheduleRetry() {
    retryTimer = setTimeout(() => { previewRetry++ }, retryDelay)
    retryDelay = Math.min(retryDelay * 2, RETRY_CAP_MS)
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose()
  }
</script>

<svelte:window onkeydown={onKeydown} />

<Panel
  title={current ? `${mod.name} (${current.label})` : (mod.label ? `${mod.name} (${mod.label})` : mod.name)}
  onClose={onClose}
  style="--panel-max-width:90%;--panel-max-height:calc(94vh / var(--zoom));--panel-shadow:none;--panel-body-padding:14px 9px 14px 14px;--panel-body-gap:12px;--panel-overflow-anchor:auto;--panel-scroll-margin:14px"
>
      {#if previewSrc}
        <div class="content">
          <div class="preview-wrap">
            {#if isVideo}
              {#key previewSrc}
                <video bind:this={videoEl} class="preview" src={previewSrc} muted autoplay={videoAutoplay} loop playsinline></video>
              {/key}
            {:else}
              {#key previewSrc}
                <img class="preview" src={previewSrc} alt={mod.name} />
              {/key}
            {/if}
            {#if prevPreviewSrc}
              <div class="prev-preview" aria-hidden="true">
                {#if prevIsVideo}
                  <video class="preview" src={prevPreviewSrc} muted autoplay loop playsinline></video>
                {:else}
                  <img class="preview" src={prevPreviewSrc} alt="" />
                {/if}
              </div>
            {/if}
            {#if variants.length > 0}
              <div class="variant-circles">
                {#each variants as v, i}
                  <button
                    class="variant-dot"
                    class:active={i === activeVariant}
                    style:background={v.color ?? 'var(--text-dim)'}
                    onclick={() => onSelectVariant?.(i)}
                    title={v.label}
                    aria-label={v.label}
                  ></button>
                {/each}
              </div>
            {/if}
          </div>
          {#if mod.author || mod.sender}
            <div class="meta-row">
              <span class="meta-label">{_("author", "Author")}:</span>
              <span>{[mod.author].flat().concat([mod.sender].flat()).filter(Boolean).join(' · ')}</span>
            </div>
          {/if}
          {#if mod.tags.length > 0}
            <div class="tags">{mod.tags.join(', ')}</div>
          {/if}
        </div>
      {:else if loading}
        <div class="loading">{_("loading", "Loading\u2026")}</div>
      {/if}
      {#if !previewSrc && !loading}
        <p class="empty">{_("no_preview", "No preview available.")}</p>
      {/if}
</Panel>

<style>
  .loading {
    color: var(--text-dim);
    text-align: center;
    padding: 16px;
  }

  .preview {
    grid-area: 1 / 1;
    max-width: 100%;
    height: auto;
    max-height: calc(80vh / var(--zoom));
    object-fit: contain;
    align-self: center;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
  }

  .content {
    width: fit-content;
    min-width: min(636px, 100%);
    max-width: 100%;
    align-self: center;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .preview-wrap {
    position: relative;
    display: grid;
    grid-template: auto / auto;
    justify-items: center;
    justify-content: center;
    overflow: hidden;
  }

  .prev-preview {
    position: absolute;
    inset: 0;
    z-index: 1;
    display: grid;
    place-items: center;
    animation: preview-fade-out 160ms ease forwards;
    pointer-events: none;
  }

  .prev-preview .preview {
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
  }

  @keyframes preview-fade-out {
    from { opacity: 1; }
    to   { opacity: 0; }
  }

  .variant-circles {
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 10px;
  }

  .variant-dot {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: none;
    padding: 0;
    cursor: pointer;
    flex-shrink: 0;
    transition: transform 0.12s, box-shadow 0.12s;
  }

  .variant-dot:hover { transform: scale(1.15); }

  .meta-row {
    font-size: 12px;
    color: var(--text);
    display: flex;
    gap: 6px;
  }

  .meta-label {
    color: var(--text-dim);
    flex-shrink: 0;
  }

  .tags {
    font-size: 11px;
    color: var(--accent);
  }

  .empty {
    color: var(--text-dim);
    font-size: 12px;
  }
</style>
