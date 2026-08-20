<script lang="ts">
  import { onMount, untrack } from 'svelte'
  import { get } from 'svelte/store'
  import { setupStore } from '$lib/stores/setup'
  import { localeStore } from '$lib/stores/locale'
  import { modalStore } from '$lib/stores/modal'
  import { ready } from '$lib/stores/bridge'
  import type { LaunchOptionResult, RestartSteamResult } from '$lib/api'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let results = $state<LaunchOptionResult[]>([])
  let phase = $state<'idle' | 'running'>('idle')
  let result = $state<'success' | 'failure' | null>(null)
  let errorMessage = $state<string | null>(null)
  let didRestart = $state(false)
  let aborted = $state(false)
  let aliases = $state<Record<string, string>>({})

  let { done = $bindable(false), suppressBack = $bindable(false), trigger = 0, isRunning = $bindable(false), cancelTrigger = 0, oncloseSetup }: {
    done?: boolean
    suppressBack?: boolean
    trigger?: number
    isRunning?: boolean
    cancelTrigger?: number
    oncloseSetup?: () => void
  } = $props()

  $effect(() => {
    if (trigger && untrack(() => phase === 'idle')) restartAndApply()
  })

  $effect(() => {
    isRunning = phase === 'running'
  })

  $effect(() => {
    if (cancelTrigger && untrack(() => phase === 'running')) cancel()
  })

  let locale = $derived((aliases[$setupStore?.data?.game_lang ?? "english"] ?? $setupStore?.data?.game_lang ?? "english") || "english")
  let steamIds = $derived($setupStore?.data?.steam_ids ?? [])

  onMount(() => {
    if (get(ready)) loadAliases()
    else ready.subscribe(v => { if (v) loadAliases() })
  })

  function loadAliases() {
    window.pywebview.api.get_app_info().then(res => {
      if (res.ok) aliases = res.data.locale_aliases ?? {}
    }).catch(e => console.error("get_app_info failed:", e))
  }

  function isSuccess(data: RestartSteamResult): boolean {
    for (const r of data.apply_results) {
      if (r.status !== 'ok' && r.status !== 'already_set') return false
    }
    if (!data.restart_needed) return true
    if (!data.steam_killed) return false
    if (!data.steam_exited) return false
    return true
  }

  function buildErrorMessage(data: RestartSteamResult): string {
    if (data.restart_needed) {
      if (!data.steam_killed) return _("setup_launch_steam_not_found", "Steam executable not found. Set Steam Root in Settings.")
      if (!data.steam_exited) return _("setup_launch_steam_not_exited", "Steam did not exit within timeout.")
    }
    const failed = data.apply_results.filter(r => r.status !== 'ok' && r.status !== 'already_set')
    return failed.map(r => {
      switch (r.status) {
        case 'no_vdf': return _("setup_launch_no_vdf", "{name} - Steam config not found").replace("{name}", r.name)
        case 'no_dota_data': return _("setup_launch_no_dota_data", "{name} - No Dota 2 data found").replace("{name}", r.name)
        case 'permission_error': return _("setup_launch_permission_error", "{name} - Permission denied. Run Minify as Administrator or set manually.").replace("{name}", r.name)
        case 'no_steam_root': return _("setup_launch_no_steam_root", "{name} - Steam path not configured. Set Steam Root in Settings.").replace("{name}", r.name)
        default: return _("setup_launch_error", "{name} - Unexpected error").replace("{name}", r.name)
      }
    }).join("\n")
  }

  function finish() {
    done = true
    suppressBack = true
  }

  function showManualModal(message: string) {
    phase = 'idle'
    modalStore.set({
      title: _("setup_launch_manual_title", "Manual Setup Required"),
      messages: [
        message,
        _("setup_launch_failure_instructions_modal", "To set manually: add `-language {locale}` to Dota 2 launch options in Steam.\n\n1. Open Steam\n2. Right-click Dota 2 in your Library\n3. Select Properties\n4. Under General, add `-language {locale}` to Launch Options\n5. Click OK").replace("{locale}", locale)
      ],
      buttons: [_("ok", "OK")],
      onrespond: () => {
        oncloseSetup?.()
      }
    })
  }

  function cancel() {
    aborted = true
    showManualModal(_("setup_launch_cancelled", "Operation cancelled."))
  }

  async function restartAndApply() {
    aborted = false
    phase = 'running'
    result = null
    errorMessage = null

    try {
      const timeout: Promise<never> = new Promise((_, reject) => setTimeout(() => reject(new Error("Timed out")), 90000))
      const res = await Promise.race([
        window.pywebview.api.restart_steam_and_apply({ steam_ids: steamIds, locale }),
        timeout,
      ])
      if (aborted) return
      if (!res.ok) {
        errorMessage = res.error
        result = 'failure'
        showManualModal(res.error)
        return
      }
      const data = res.data
      results = data.apply_results
      didRestart = data.restart_needed

      if (isSuccess(data)) {
        result = 'success'
      } else {
        errorMessage = buildErrorMessage(data)
        result = 'failure'
        showManualModal(errorMessage)
        return
      }
    } catch (e) {
      if (aborted) return
      if (String(e).includes("Timed out")) {
        errorMessage = _("setup_launch_timed_out", "The operation timed out. Try again or set the launch option manually.")
      } else {
        errorMessage = `Connection error: ${e}`
      }
      result = 'failure'
      showManualModal(errorMessage)
      return
    }

    if (aborted) return
    phase = 'idle'
    finish()
  }

  function statusClass(status: string): string {
    switch (status) {
      case 'ok':
      case 'already_set': return 'status-ok'
      case 'no_vdf':
      case 'no_dota_data': return 'status-warn'
      case 'no_steam_root':
      case 'permission_error':
      case 'error': return 'status-err'
      default: return ''
    }
  }

  function statusLabel(r: LaunchOptionResult): string {
    switch (r.status) {
      case 'ok': return _("setup_launch_ok_label", "-language {locale} set").replace("{locale}", locale)
      case 'already_set': return _("setup_launch_already_set_label", "Already set")
      case 'no_vdf': return _("setup_launch_no_vdf_label", "Steam config not found")
      case 'no_dota_data': return _("setup_launch_no_dota_data_label", "No Dota 2 data")
      case 'permission_error': return _("setup_launch_permission_error_label", "Permission denied")
      case 'no_steam_root': return _("setup_launch_no_steam_root_label", "Steam path not set")
      case 'error': return _("setup_launch_error_label", "Unexpected error")
      default: return r.status
    }
  }

  function statusText(r: LaunchOptionResult): string {
    switch (r.status) {
      case 'ok': return _("setup_launch_ok", "-language {locale} was set successfully for {name}").replace("{locale}", locale).replace("{name}", r.name)
      case 'already_set': return _("setup_launch_already_set", "{name} - Already set correctly").replace("{name}", r.name)
      case 'no_vdf': return _("setup_launch_no_vdf", "{name} - Steam config not found").replace("{name}", r.name)
      case 'no_dota_data': return _("setup_launch_no_dota_data", "{name} - No Dota 2 data found").replace("{name}", r.name)
      case 'permission_error': return _("setup_launch_permission_error", "{name} - Permission denied. Run Minify as Administrator or set manually.").replace("{name}", r.name)
      case 'no_steam_root': return _("setup_launch_no_steam_root", "{name} - Steam path not configured. Set Steam Root in Settings.").replace("{name}", r.name)
      case 'error': return _("setup_launch_error", "{name} - Unexpected error").replace("{name}", r.name)
      default: return `${r.name} - ${r.status}`
    }
  }
</script>

<div class="launch-setup">
  {#if phase === 'running'}
    <p class="launch-phase">{_("setup_launch_applying", "Applying launch options...")}</p>

  {:else if result === 'success'}
    <div class="success-banner">
      {#if didRestart}
        {_("setup_launch_step_restart_title", "Steam restarted with `-language {locale}` set in Dota 2 launch options").replace("{locale}", locale)}
      {:else}
        {_("setup_launch_step_already_set_title", "All launch options are already set correctly")}
      {/if}
    </div>
    <p class="section-heading">{_("setup_launch_step_options_heading", "Launch options:")}</p>
    <div class="launch-results">
      {#each results as r}
        <div class="launch-row {statusClass(r.status)}" title={statusText(r)}>
          <span class="launch-icon">
            {#if r.status === 'ok' || r.status === 'already_set'}
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7 12.5l3 3 7-7"></path></svg>
            {:else if r.status === 'no_vdf' || r.status === 'no_dota_data'}
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
            {:else}
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
            {/if}
          </span>
          <span class="launch-name">{r.name}</span>
          <span class="launch-status">{statusLabel(r)}</span>
        </div>
      {/each}
    </div>

  {:else if result === 'failure'}
    <div class="failure-state">
      {#if errorMessage}
        <p class="failure-message">{errorMessage}</p>
      {/if}
      <div class="launch-manual">
        <p>{_("setup_launch_failure_instructions", "To set manually: add `-language {locale}` to Dota 2 launch options in Steam.\n\n1. Open Steam\n2. Right-click Dota 2 in your Library\n3. Select Properties\n4. Under General, add `-language {locale}` to Launch Options\n5. Restart Steam").replace("{locale}", locale)}</p>
      </div>
    </div>

  {:else}
    <p class="launch-idle-text">{_("setup_launch_idle", "Click the button below to set the -language launch option for your Steam accounts. Steam will restart automatically.")}</p>
  {/if}
</div>

<style>
  .launch-setup {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .launch-phase {
    color: var(--text-dim);
    font-size: 13px;
    text-align: center;
    padding: 20px;
  }

  .failure-state {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .failure-message {
    color: var(--red);
    font-size: 12px;
    text-align: center;
    line-height: 1.5;
    white-space: pre-line;
  }

  .launch-manual {
    background: var(--bg-raised);
    padding: 12px 14px;
    border-radius: var(--radius-sm);
    font-size: 12px;
    color: var(--yellow);
    line-height: 1.6;
    white-space: pre-line;
  }

  .launch-results {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 0 12px;
  }

  .launch-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    font-size: 13px;
    border: 1px solid var(--border-dim);
    background: none;
    transition: background 0.12s;
  }

  .launch-row:hover { background: var(--bg-hover); }

  .launch-row.status-ok { border-color: var(--accent-glow); }
  .launch-row.status-warn { border-color: rgba(241, 196, 15, 0.35); }
  .launch-row.status-err { border-color: rgba(255, 68, 68, 0.35); }

  .launch-row.status-ok .launch-icon,
  .launch-row.status-ok .launch-status { color: var(--accent); }
  .launch-row.status-warn .launch-icon,
  .launch-row.status-warn .launch-status { color: var(--yellow); }
  .launch-row.status-err .launch-icon,
  .launch-row.status-err .launch-status { color: var(--red); }

  .launch-icon { display: flex; align-items: center; flex-shrink: 0; }

  .launch-name { font-weight: 500; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .launch-status {
    font-size: 11px;
    font-family: var(--font-mono);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .launch-idle-text {
    color: var(--text-dim);
    font-size: 13px;
    text-align: center;
    padding: 20px;
    line-height: 1.5;
  }

  .success-banner {
    background: rgba(0, 230, 230, 0.08);
    border: 1px solid var(--accent-glow);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    font-size: 12.5px;
    color: var(--accent);
    line-height: 1.5;
  }

  .section-heading {
    font-size: 13px;
    font-weight: 600;
    color: var(--text);
    padding: 0 12px;
    margin-bottom: 6px;
  }
</style>
