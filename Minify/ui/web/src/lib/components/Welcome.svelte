<script lang="ts">
  import { fade, scale } from 'svelte/transition'
  import { localeStore } from '$lib/stores/locale'
  import { focusTrap } from '$lib/actions/focusTrap'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { onDismiss }: { onDismiss: () => void } = $props()
</script>

<div class="welcome-overlay" in:fade={{ duration: 150 }} out:fade={{ duration: 100 }}>
  <div class="welcome-panel" in:scale={{ start: 0.94, duration: 150 }} out:fade={{ duration: 100 }} use:focusTrap>
    <div class="welcome-scroll" data-scrollable use:smoothscroll>
      <h1>{_("welcome_title", "Welcome to Dota 2 Minify!")}</h1>

      <section>
        <h2>{_("welcome_whats_new", "What\u2019s New")}</h2>
        <ul>
          <li>{_("welcome_changelog_1", "Redesigned card-based mod browser")}</li>
          <li>{_("welcome_changelog_2", "Streamlined 4-step onboarding setup")}</li>
          <li>{_("welcome_changelog_3", "Improved performance and stability")}</li>
        </ul>
      </section>

      <section>
        <h2>{_("welcome_how_to", "How to Use")}</h2>
        <ol>
          <li>{_("welcome_howto_1", "Browse mods in the grid and enable the ones you want")}</li>
          <li>{_("welcome_howto_2", "Click Patch to apply changes to Dota 2")}</li>
          <li>{_("welcome_howto_3", "Adjust per-mod settings from the Settings button")}</li>
        </ol>
      </section>
    </div>

    <button class="btn-primary" onclick={onDismiss}>
      {_("welcome_get_started", "Get Started")}
    </button>
  </div>
</div>

<style>
  .welcome-overlay {
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
    z-index: 100;
  }

  .welcome-panel {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    max-width: 460px;
    width: 90%;
    max-height: calc(100% - 48px);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .welcome-scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 20px 32px 12px;
    display: flex;
    flex-direction: column;
    gap: 20px;
    margin-right: 3px;
  }

  .welcome-scroll::-webkit-scrollbar-track {
    margin-top: 20px;
    margin-bottom: 12px;
  }

  h1 { font-size: 18px; color: var(--accent); text-shadow: 0 0 14px var(--accent-glow); }

  h2 { font-size: 13px; color: var(--text); margin-bottom: 6px; }

  ul, ol {
    margin: 0;
    padding-left: 18px;
    font-size: 12px;
    color: var(--text-dim);
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .btn-primary {
    align-self: flex-end;
    flex-shrink: 0;
    margin: 12px 32px 16px 0;
  }
</style>