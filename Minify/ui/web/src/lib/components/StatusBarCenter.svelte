<script lang="ts">
  import { hudStore } from '$lib/stores/hud'
  import { resolveText } from '$lib/stores/terminal'
  import { localeStore } from '$lib/stores/locale'
  import ProgressBar from './ProgressBar.svelte'

  let _t = $derived($localeStore.t)

  let pct = $derived.by(() => {
    const v = $hudStore?.value ?? 0
    return Math.round(v <= 1 ? v * 100 : Math.min(100, v))
  })

  let active = $derived($hudStore?.visible ?? false)
  let text = $derived(
    active
      ? resolveText($hudStore?.status ?? '', $hudStore?.args ?? [], _t).trim() ||
        resolveText($hudStore?.messages?.[0] ?? '', [], _t).trim()
      : ''
  )
</script>

<div class="status-center" title={text || undefined}>
  <span class="center-text">{text}</span>
  {#if active}
    <ProgressBar {pct} style="width:100%;max-width:200px;height:3px" />
  {/if}
</div>

<style>
  .status-center {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    padding: 1px 12px;
    overflow: hidden;
    color: var(--text-dim);
  }

  .center-text {
    max-width: 100%;
    min-height: 12px;
    max-height: 12px;
    font-size: 10px;
    line-height: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
