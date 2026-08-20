<script lang="ts">
  import { localeStore } from '$lib/stores/locale'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let {
    title,
    description,
    stepNumber,
    totalSteps = 5,
    children,
  }: {
    title: string
    description?: string
    stepNumber: number
    totalSteps?: number
    children?: import('svelte').Snippet
  } = $props()

  let bodyEl = $state<HTMLDivElement | null>(null)
  let lastStep = $state<number | null>(null)

  // If the viewport is resized while a step is scrolled, re-clamp the scroll
  // position so a stale offset can never leave the top of the content cropped.
  function onResize() {
    if (!bodyEl) return
    const max = Math.max(0, bodyEl.scrollHeight - bodyEl.clientHeight)
    if (bodyEl.scrollTop > max) bodyEl.scrollTop = max
    if (bodyEl.scrollTop < 0) bodyEl.scrollTop = 0
  }

  // The .step-body is shared across steps. When the step actually changes,
  // reset the scroll so a stale offset from a taller step can never overshoot
  // the new, shorter content (0 is always in range regardless of outro timing).
  // Guarded against the parent re-passing the same stepNumber on unrelated
  // re-renders (e.g. clicking a language button), which must not reset scroll.
  $effect(() => {
    const isNew = lastStep !== null && stepNumber !== lastStep
    lastStep = stepNumber
    if (isNew && bodyEl) bodyEl.scrollTop = 0
  })
</script>

<svelte:window onresize={onResize} />

<div class="setup-step">
  <div class="step-header">
    <span class="step-counter">
      {_("step", "Step")} {stepNumber} / {totalSteps}
    </span>
    <h2>{title}</h2>
    {#if description}
      <p class="step-desc">{description}</p>
    {/if}
  </div>

  <div class="step-body" bind:this={bodyEl} data-scrollable use:smoothscroll>
    {@render children?.()}
  </div>
</div>

<style>
  .setup-step {
    display: flex;
    flex-direction: column;
    min-height: 0;
    flex: 1;
    gap: 16px;
  }

  .step-header {
    text-align: center;
    padding: 24px 24px 0;
  }

  .step-counter {
    font-size: 12px;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .step-header h2 {
    font-size: 18px;
    color: var(--accent);
    margin-top: 6px;
    text-shadow: 0 0 14px var(--accent-glow);
  }

  .step-desc {
    font-size: 13px;
    color: var(--text-dim);
    margin-top: 6px;
    line-height: 1.5;
  }

  .step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 3px;
    margin-left: 8px;
    margin-right: 3px;
    margin-bottom: 3px;
  }

  .step-body::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }
</style>
