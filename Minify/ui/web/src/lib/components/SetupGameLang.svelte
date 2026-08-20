<script lang="ts">
  import { onMount } from 'svelte'
  import { setupStore } from '$lib/stores/setup'
  import { localeStore } from '$lib/stores/locale'
  import { ready } from '$lib/stores/bridge'
  import { get } from 'svelte/store'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let outputs = $state<string[]>([])
  let outputNames = $state<Record<string, string>>({})
  let loadError = $state(false)

  onMount(() => {
    if (get(ready)) load()
    else ready.subscribe(v => { if (v) load() })
  })

  function load() {
    window.pywebview.api.get_app_info().then(res => {
      if (res.ok) {
        outputs = res.data.output_list
        outputNames = res.data.output_names ?? {}
      } else loadError = true
    }).catch(e => { loadError = true; console.error("get_app_info failed:", e) })
  }

  function select(locale: string) {
    setupStore.update(s => s ? { ...s, data: { ...s.data, game_lang: locale } } : s)
  }
</script>

{#if loadError}
  <p class="setup-lang-error">{_("setup_error_load_languages", "Failed to load language options.")}</p>
{/if}
<div class="output-grid">
  {#each outputs as locale}
    <button
      class="output-btn"
      class:selected={$setupStore?.data.game_lang === locale}
      onclick={() => select(locale)}
    >
      {outputNames[locale] ?? locale}
    </button>
  {/each}
</div>

<style>
  .setup-lang-error {
    color: var(--red);
    font-size: 11px;
    text-align: center;
    margin-bottom: 8px;
  }

  .output-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
    gap: 3px;
  }

  .output-btn {
    width: 100%;
    height: 38px;
    padding: 0 6px;
    font-size: 13px;
    text-align: center;
    border-radius: var(--radius-sm);
  }

  .output-btn.selected {
    border-color: var(--accent);
    background: var(--bg-hover);
    color: var(--accent);
  }
</style>
