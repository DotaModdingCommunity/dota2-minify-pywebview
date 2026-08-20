<script lang="ts">
  import { fade, fly } from 'svelte/transition'
  import { localeStore } from '$lib/stores/locale'
  import { smoothscroll } from '$lib/actions/smoothscroll'
  import { focusTrap } from '$lib/actions/focusTrap'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let {
    title,
    onClose,
    closable = true,
    class: className = "",
    style = "",
    children,
    footer,
    headerExtra,
  }: {
    title?: string
    onClose?: () => void
    closable?: boolean
    class?: string
    style?: string
    children?: import('svelte').Snippet
    footer?: import('svelte').Snippet
    headerExtra?: import('svelte').Snippet
  } = $props()
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
  class="overlay {className}"
  {style}
  in:fade={{ duration: 160 }}
  out:fade={{ duration: 110 }}
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  use:focusTrap={{ initial: closable ? '.close-btn' : undefined }}
  onclick={onClose}
>
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="panel"
    in:fly={{ y: 8, duration: 160 }}
    out:fly={{ y: -8, duration: 110 }}
    role="none"
    onclick={(e: MouseEvent) => e.stopPropagation()}
  >
    {#if title || closable}
      <div class="panel-header">
        <div class="panel-title-row">
          {#if title}
            <h2>{title}</h2>
          {/if}
          {#if headerExtra}
            {@render headerExtra()}
          {/if}
        </div>
        {#if closable}
          <button class="close-btn" onclick={onClose} title={_("close", "Close")} aria-label={_("close", "Close")}>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18"></path><path d="M6 6 18 18"></path></svg>
          </button>
        {/if}
      </div>
    {/if}

    <div class="panel-body" data-scrollable use:smoothscroll>
      {@render children?.()}
    </div>

    {#if footer}
      <div class="panel-footer">
        {@render footer()}
      </div>
    {/if}
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
    background: rgba(0, 0, 0, var(--overlay-dim));
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--overlay-z, 60);
  }

  .panel {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    width: var(--panel-width, fit-content);
    max-width: var(--panel-max-width, 640px);
    max-height: var(--panel-max-height, calc(80vh / var(--zoom)));
    display: flex;
    flex-direction: column;
    border-radius: var(--radius-lg);
    box-shadow: var(--panel-shadow, var(--shadow-floating));
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }

  .panel-title-row {
    display: flex;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .panel-header h2 {
    font-size: 14px;
    color: var(--accent);
    text-shadow: 0 0 12px var(--accent-glow);
  }

  .close-btn {
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    flex-shrink: 0;
    transition: color 0.3s, border-color 0.3s, background 0.3s;
  }

  .close-btn:hover,
  .close-btn:focus-visible,
  :global(html.keyboard-focus) .close-btn:focus {
    color: var(--red);
    border-color: var(--red);
    background: var(--bg-hover);
  }

  .close-btn:focus-visible,
  :global(html.keyboard-focus) .close-btn:focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }

  .panel-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    overflow-anchor: var(--panel-overflow-anchor, none);
    padding: var(--panel-body-padding, 10px 14px);
    display: flex;
    flex-direction: column;
    gap: var(--panel-body-gap, 2px);
    margin-right: 3px;
  }

  .panel-body::-webkit-scrollbar-track {
    margin-top: var(--panel-scroll-margin, 8px);
    margin-bottom: var(--panel-scroll-margin, 8px);
  }

  .panel-footer {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    padding: 10px 14px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }
</style>