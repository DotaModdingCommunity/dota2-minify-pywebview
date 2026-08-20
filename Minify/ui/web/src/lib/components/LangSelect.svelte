<script lang="ts">
  import { modalStore } from '$lib/stores/modal'
  import { loadLocale } from '$lib/i18n.svelte'
  import { onMount } from 'svelte'
  import { ready } from '$lib/stores/bridge'
  import { get } from 'svelte/store'
  import ComboBox from '$lib/components/ComboBox.svelte'

  let langs = $state<string[]>([])
  let current = $state('EN')

  onMount(() => {
    if (get(ready)) load()
    else ready.subscribe(v => { if (v) load() })
  })

  function load() {
    window.pywebview.api.get_available_langs().then(res => {
      if (res.ok) langs = res.data
    })
    window.pywebview.api.get_app_info().then(res => {
      if (res.ok) current = res.data.current_lang
    })
  }

  async function onLangChange(lang: string) {
    const res = await window.pywebview.api.set_language(lang)
    if (!res.ok) modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] })
    else {
      current = lang
      await loadLocale(lang)
    }
  }
</script>

<ComboBox value={current} options={langs} onchange={onLangChange} />
