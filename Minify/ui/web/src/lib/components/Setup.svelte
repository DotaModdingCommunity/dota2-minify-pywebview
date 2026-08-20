<script lang="ts">
  import { setupStore } from '$lib/stores/setup'
  import { loadLocale } from '$lib/i18n.svelte'
  import { localeStore } from '$lib/stores/locale'
  import StatusBarCenter from './StatusBarCenter.svelte'
  import { focusTrap } from '$lib/actions/focusTrap'

  import { fade } from 'svelte/transition'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }
  import SetupStep from './SetupStep.svelte'
  import SetupLanguage from './SetupLanguage.svelte'
  import SetupGameLang from './SetupGameLang.svelte'
  import SetupProfiles from './SetupProfiles.svelte'
  import SetupLaunchOptions from './SetupLaunchOptions.svelte'

  let setupError = $state<string | null>(null)
  let launchDone = $state(false)
  let launchSuppressBack = $state(false)
  let launchTrigger = $state(0)
  let isRunning = $state(false)
  let launchCancel = $state(0)

  const totalSteps = 4

  function stepTitle(): string {
    const s = $setupStore?.step
    if (s === 1) return _("setup_step_1_title", "Choose Minify Language")
    if (s === 2) return _("setup_step_2_title", "Choose Dota 2 Language")
    if (s === 3) return _("setup_step_3_title", "Choose Steam Profiles")
    if (s === 4) return _("setup_step_4_title", "Setting Up Launch Options")
    return ""
  }

  function stepDesc(): string | undefined {
    const s = $setupStore?.step
    if (s === 1) return _("setup_step_1_desc", "Select your preferred language for the application.")
    if (s === 2) return _("setup_step_2_desc", "Choose the language for Dota 2 in-game text.")
    if (s === 3) return _("setup_step_3_desc", "Select your Steam account.")
    if (s === 4) return undefined
    return undefined
  }

  function nextStep() {
    setupStore.update(s => s ? { ...s, step: s.step + 1 } : s)
  }

  function prevStep() {
    setupStore.update(s => s ? { ...s, step: Math.max(1, s.step - 1) } : s)
  }

  function canGoNext(): boolean {
    const s = $setupStore
    if (!s) return false
    switch (s.step) {
      case 1: return !!s.data.lang
      case 2: return !!s.data.game_lang
      case 3: return s.data.steam_ids.length > 0
      case 4: return launchDone || isRunning
      default: return false
    }
  }

  function nextLabel(): string {
    const s = $setupStore
    if (!s) return ""
    if (s.step === 4) {
      if (isRunning) return _("cancel", "Cancel")
      if (!launchDone) return _("setup_launch_apply", "Apply")
      return _("finish", "Finish")
    }
    return s.step < totalSteps ? _("next", "Next") : _("finish", "Finish")
  }

  function nextDisabled(): boolean {
    const s = $setupStore
    if (!s) return true
    if (s.step === 4 && !launchDone) return false
    return !canGoNext()
  }

  function handleNextClick() {
    const s = $setupStore
    if (!s) return
    if (s.step === 4) {
      handleStep4Next()
    } else if (s.step < totalSteps) {
      nextStep()
    } else {
      finishSetup()
    }
  }

  function handleStep4Next() {
    if (isRunning) {
      launchCancel++
    } else if (!launchDone) {
      launchTrigger++
    } else {
      finishSetup()
    }
  }

  async function finishSetup() {
    const s = $setupStore
    if (!s) return
    setupError = null

    try {
      const res = await window.pywebview.api.save_setup({
        lang: s.data.lang,
        game_lang: s.data.game_lang,
        steam_ids: s.data.steam_ids,
      })
      if (!res.ok) { setupError = res.error; return }
    } catch (e) {
      setupError = `Connection error: ${e}`
      return
    }

    await loadLocale(s.data.lang)
    setupStore.set(null)
  }
</script>

{#if $setupStore}
  <div class="setup-overlay">
    <div class="setup-panel" use:focusTrap>
      <SetupStep
        title={stepTitle()}
        description={stepDesc()}
        stepNumber={$setupStore.step}
        {totalSteps}
      >
        <div in:fade={{ duration: 150 }} out:fade={{ duration: 100 }}>
          {#if $setupStore.step === 1}
            <SetupLanguage />
          {:else if $setupStore.step === 2}
            <SetupGameLang />
          {:else if $setupStore.step === 3}
            <SetupProfiles />
          {:else if $setupStore.step === 4}
            <SetupLaunchOptions bind:done={launchDone} bind:suppressBack={launchSuppressBack} trigger={launchTrigger} bind:isRunning cancelTrigger={launchCancel} oncloseSetup={() => setupStore.set(null)} />
          {/if}
        </div>
        {#if setupError}
          <p class="setup-error">{_("setup_error_save", "Failed to save setup. Please try again.")}</p>
        {/if}
      </SetupStep>
      <div class="setup-statusbar">
        <span class="status-side">
          {#if $setupStore.step > 1 && !launchSuppressBack}
            <button onclick={prevStep} class="btn-ghost">
              {_("back", "Back")}
            </button>
          {/if}
        </span>
        <StatusBarCenter />
        <span class="status-side status-right">
          <button onclick={handleNextClick} disabled={nextDisabled()} class="btn-primary">
            {nextLabel()}
          </button>
        </span>
      </div>
    </div>
  </div>
{/if}

<style>
  .setup-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
    background: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 200;
  }

  .setup-panel {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    width: 95%;
    height: 95%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: var(--shadow-floating);
    animation: pop-in 0.15s ease-out;
  }

  .setup-error {
    color: var(--red);
    font-size: 11px;
    text-align: center;
    padding: 0 24px 8px;
  }

  .setup-statusbar {
    display: flex;
    align-items: center;
    width: calc(100% - 12px);
    margin: 0 auto;
    padding: 12px 4px;
    border-top: 1px solid var(--border);
    flex-shrink: 0;
  }

  .status-side {
    flex: 1;
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .status-right {
    justify-content: flex-end;
  }

  @keyframes pop-in {
    from { transform: scale(0.94); opacity: 0; }
    to   { transform: scale(1);    opacity: 1; }
  }
</style>
