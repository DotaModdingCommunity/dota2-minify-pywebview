<script lang="ts">
  import { fade, fly } from 'svelte/transition'
  import { modalStore } from '$lib/stores/modal'
  import { localeStore } from '$lib/stores/locale'
  import { resolveText } from '$lib/stores/terminal'
  import { smoothscroll } from '$lib/actions/smoothscroll'
  import { focusTrap } from '$lib/actions/focusTrap'

  let _t = $derived($localeStore.t)

  function openUrl(url: string) {
    if (url) window.pywebview.api.open_url(url)
  }

  function respond(label: string) {
    const cb = $modalStore?.onrespond
    modalStore.dismiss()
    if (cb) {
      cb(label)
    }
  }

  let bodyEl = $state<HTMLElement | null>(null)

  // The .modal-body is shared across modalStore.set() calls. When the modal
  // content is swapped (or a new modal opens), reset the scroll so a stale
  // offset from a taller modal can never overshoot the new, shorter content.
  $effect(() => {
    $modalStore
    if (bodyEl) bodyEl.scrollTop = 0
  })

  function onKeydown(e: KeyboardEvent) {
    if (!$modalStore) return
    if (e.key === 'Enter') respond($modalStore.buttons[$modalStore.buttons.length - 1])
    if (e.key === 'Escape') respond($modalStore.buttons[0])
  }
</script>

<svelte:window onkeydown={onKeydown} />

{#if $modalStore}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div class="backdrop" in:fade={{ duration: 160 }} out:fade={{ duration: 110 }} role="dialog" aria-modal="true">
    <div class="modal" in:fly={{ y: 8, duration: 160 }} out:fly={{ y: -8, duration: 110 }} use:focusTrap={{ initial: '.modal-buttons button' }}>
      <h2 class="modal-title">{resolveText($modalStore.title, [], _t)}</h2>
      <div class="modal-body" bind:this={bodyEl} data-scrollable use:smoothscroll>
        {#each $modalStore.messages as msg}
          <p>{resolveText(msg, [], _t)}</p>
        {/each}
      </div>
      <div class="modal-footer">
        {#if $modalStore.social}
          <div class="social-row">
            <button class="social-btn" title="Discord" onclick={() => openUrl($modalStore.social!.discord)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
                ><path
                  d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z"
                /></svg
              >
            </button>
            <button class="social-btn" title="Telegram" onclick={() => openUrl($modalStore.social!.telegram)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
                ><path
                  d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
                /></svg
              >
            </button>
            <button class="social-btn" title="GitHub" onclick={() => openUrl($modalStore.social!.github_io)}>
              <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
                ><path
                  d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
                /></svg
              >
            </button>
          </div>
        {/if}
        <div class="modal-buttons">
          {#each $modalStore.buttons as btn}
            <button onclick={() => respond(btn)}>{btn}</button>
          {/each}
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
    background: rgba(0,0,0,var(--overlay-dim));
    backdrop-filter: blur(3px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 500;
  }

  .modal {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    padding: 20px 24px;
    min-width: 340px;
    max-width: min(500px, calc(100% - 48px));
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-floating);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .modal-title { font-size: 15px; font-weight: 600; color: var(--accent); text-shadow: 0 0 12px var(--accent-glow); }

  .modal-body { max-height: calc(60vh / var(--zoom)); overflow-y: auto; }
  .modal-body::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }
  .modal-body p { font-size: 12.5px; color: var(--text); line-height: 1.5; user-select: text; }

  .modal-buttons {
    display: flex;
    gap: 8px;
    margin-left: auto;
  }

  .modal-buttons button:not(:last-child):hover {
    color: var(--red);
    border-color: var(--red);
  }

  .modal-buttons button:not(:last-child):focus-visible,
  :global(html.keyboard-focus) .modal-buttons button:not(:last-child):focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }

  .modal-footer {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .social-row {
    display: flex;
    gap: 4px;
  }

  .social-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 28px;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    padding: 0;
    transition: color 0.15s, border-color 0.15s, background 0.15s;
    flex-shrink: 0;
  }
  .social-btn:hover {
    color: var(--accent);
    border-color: var(--accent-dim);
    background: rgba(0, 230, 230, 0.06);
  }
</style>
