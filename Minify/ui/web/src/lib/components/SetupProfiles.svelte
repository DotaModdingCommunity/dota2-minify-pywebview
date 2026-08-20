<script lang="ts">
  import Toggle from '$lib/components/Toggle.svelte'
  import { onMount, onDestroy } from 'svelte'
  import { setupStore } from '$lib/stores/setup'
  import { localeStore } from '$lib/stores/locale'
  import { ready } from '$lib/stores/bridge'
  import { get } from 'svelte/store'
  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let accounts = $state<{ id: string; name: string }[]>([])
  let selectedIds = $state<string[]>($setupStore?.data?.steam_ids ?? [])
  let loadError = $state<string | null>(null)

  let loading = $state(true)

  let _pollInterval: ReturnType<typeof setInterval> | undefined
  let _unsubReady: (() => void) | undefined

  onDestroy(() => {
    if (_pollInterval) clearInterval(_pollInterval)
    _unsubReady?.()
  })

  onMount(() => {
    if (get(ready)) load()
    else _unsubReady = ready.subscribe(v => { if (v) load() })
  })

  async function load() {
    try {
      const resolveRes = await window.pywebview.api.resolve_steam_path()
      if (resolveRes.ok && !resolveRes.data.path_known) {
        await new Promise<void>((resolve, reject) => {
          let attempts = 0
          _pollInterval = setInterval(async () => {
            attempts++
            if (attempts > 60) {
              clearInterval(_pollInterval!)
              reject(new Error(_("steam_not_found", "Steam installation not found")))
              return
            }
            try {
              const r = await window.pywebview.api.get_steam_path_state()
              if (r.ok && r.data.path_known) {
                clearInterval(_pollInterval!)
                resolve()
              } else if (r.ok && !r.data.path_known && !r.data.resolving) {
                clearInterval(_pollInterval!)
                reject(new Error(_("steam_not_found", "Steam installation not found")))
              } else if (!r.ok) {
                clearInterval(_pollInterval!)
                reject(new Error(r.error))
              }
            } catch (e) {
              clearInterval(_pollInterval!)
              reject(e)
            }
          }, 500)
        })
      }

      const res = await window.pywebview.api.get_steam_accounts()
      if (res.ok) accounts = res.data
      else loadError = res.error
    } catch (e) {
      loadError = `Connection error: ${e}`
    }
    loading = false
  }

  function toggle(id: string) {
    selectedIds = selectedIds.includes(id)
      ? selectedIds.filter(x => x !== id)
      : [...selectedIds, id]
    setupStore.update(s => s ? { ...s, data: { ...s.data, steam_ids: selectedIds } } : s)
  }

  let allSelected = $derived(accounts.length > 0 && selectedIds.length === accounts.length)

  function toggleAll() {
    selectedIds = allSelected ? [] : accounts.map(a => a.id)
    setupStore.update(s => s ? { ...s, data: { ...s.data, steam_ids: selectedIds } } : s)
  }
</script>

{#if loading}
  <p class="empty">{_("loading_accounts", "Locating Steam installation...")}</p>
{:else if loadError}
  <p class="setup-profile-error">{_("setup_error_load_accounts", "Failed to load Steam accounts. Check that Steam is running.")}</p>
{:else if accounts.length === 0}
  <p class="empty">{_("no_accounts", "No Steam accounts found. Make sure Steam is installed and logged in.")}</p>
{:else}
  <div class="account-list">
    <button class="select-all-btn" onclick={toggleAll}>
      {allSelected ? _("deselect_all", "Deselect all") : _("select_all", "Select all")}
      <span class="select-all-count">{selectedIds.length}/{accounts.length}</span>
    </button>
    {#each accounts as acc}
      <button class="account-row" class:selected={selectedIds.includes(acc.id)} onclick={() => toggle(acc.id)}>
        <Toggle checked={selectedIds.includes(acc.id)} onchange={() => toggle(acc.id)} />
        <span class="account-name">{acc.name}</span>
        <span class="account-id">{acc.id}</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .setup-profile-error {
    color: var(--red);
    font-size: 11px;
    text-align: center;
    padding: 12px 20px;
  }

  .empty {
    color: var(--text-dim);
    font-size: 12px;
    text-align: center;
    padding: 20px;
  }

  .account-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .account-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 13px;
    font-family: inherit;
    border: 1px solid var(--border-dim);
    background: none;
    color: inherit;
    width: 100%;
    text-align: left;
    transition: none;
  }

  .account-row:hover {
    background: var(--bg-hover);
    color: inherit;
    border-color: var(--border-dim);
  }

  .account-row:active { transform: none; }

  .account-row.selected {
    background: var(--bg-hover);
    border-color: var(--accent-dim);
  }

  .select-all-btn {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    font-size: 12px;
    border-radius: var(--radius-sm);
    background: var(--bg-raised);
    color: var(--text-dim);
    cursor: pointer;
    border: 1px dashed var(--border);
    margin-bottom: 4px;
    transition: background 0.12s, color 0.12s;
  }

  .select-all-btn:hover {
    background: var(--bg-hover);
    color: var(--text);
  }

  .select-all-count {
    font-family: var(--font-mono);
    font-size: 11px;
  }

  .account-name { font-weight: 500; flex: 1; }

  .account-id {
    color: var(--text-dim);
    font-size: 11px;
    font-family: var(--font-mono);
  }


</style>
