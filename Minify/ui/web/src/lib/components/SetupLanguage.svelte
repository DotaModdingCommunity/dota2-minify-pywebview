<script lang="ts">
  import { onMount } from 'svelte'
  import { setupStore } from '$lib/stores/setup'
  import { loadLocale } from '$lib/i18n.svelte'
  import { ready } from '$lib/stores/bridge'
  import { get } from 'svelte/store'

  let langs = $state<string[]>([])
  let langError = $state<string | null>(null)

  onMount(() => {
    if (get(ready)) load()
    else ready.subscribe(v => { if (v) load() })
  })

  function load() {
    window.pywebview.api.get_available_langs().then(res => {
      if (res.ok) langs = res.data
    }).catch(e => console.error("get_available_langs failed:", e))
  }

  async function select(lang: string) {
    langError = null
    try {
      const res = await window.pywebview.api.set_language(lang)
      if (!res.ok) { langError = res.error; return }
    } catch (e) {
      langError = `Connection error: ${e}`
      return
    }
    await loadLocale(lang)
    setupStore.update(s => s ? { ...s, data: { ...s.data, lang } } : s)
  }
</script>

{#if langError}
  <p class="setup-lang-error">{langError}</p>
{/if}
<div class="lang-grid">
  {#each langs as lang}
    <button
      class="lang-btn"
      class:selected={$setupStore?.data.lang === lang}
      onclick={() => select(lang)}
    >
      {lang}
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

  .lang-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(104px, 1fr));
    gap: 3px;
  }

  .lang-btn {
    width: 100%;
    height: 38px;
    padding: 0 6px;
    font-size: 13px;
    text-align: center;
    border-radius: var(--radius-sm);
  }

  .lang-btn.selected {
    border-color: var(--accent);
    background: var(--bg-hover);
    color: var(--accent);
  }
</style>
