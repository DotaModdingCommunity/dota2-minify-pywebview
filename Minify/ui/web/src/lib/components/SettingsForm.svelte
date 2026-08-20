<script lang="ts">
  import type { ModPreset, SettingSchema } from '$lib/api'
  import { localeStore } from '$lib/stores/locale'
  import SettingsWidget from '$lib/components/SettingsWidget.svelte'
  import PresetPicker from '$lib/components/PresetPicker.svelte'
  import Toggle from '$lib/components/Toggle.svelte'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let {
    schema,
    values,
    presets = [] as ModPreset[],
    applyPreset,
    onaction,
    title,
    placeholder = _('search_settings', 'Search settings\u2026'),
    minForSearch = 6,
  }: {
    schema: SettingSchema[]
    values: Record<string, unknown>
    presets?: ModPreset[]
    applyPreset?: (values: Record<string, unknown>) => void
    onaction?: (key: string) => void
    title?: string
    placeholder?: string
    minForSearch?: number
  } = $props()

  let query = $state('')
  let showAdvanced = $state(false)
  let appliedPreset = $state<string | null>(null)

  const hasAdvanced = $derived(schema.some(s => s.advanced))
  const showSearch = $derived(schema.length >= minForSearch)

  function baselineFor(s: SettingSchema): unknown {
    const p = appliedPreset ? presets.find(pr => pr.name === appliedPreset) : null
    if (p && Object.prototype.hasOwnProperty.call(p.values, s.key)) {
      return p.values[s.key]
    }
    return s.default
  }

  function settingDisabled(s: SettingSchema): boolean {
    if (s.depends_on != null) return !values[s.depends_on]
    if (s.when?.key != null) {
      const cur = values[s.when.key]
      if (s.when.value === undefined) return !cur
      return String(cur) !== String(s.when.value)
    }
    return false
  }

  function matchesQuery(s: SettingSchema): boolean {
    const q = query.trim().toLowerCase()
    if (!q) return true
    return [s.text, s.key, s.description, s.section ?? '']
      .filter(Boolean)
      .some(x => String(x).toLowerCase().includes(q))
  }

  const basic = $derived(schema.filter(s => !s.advanced))
  const advanced = $derived(schema.filter(s => s.advanced))

  const searching = $derived(query.trim().length > 0)

  function group(list: SettingSchema[]): { section: string; items: SettingSchema[] }[] {
    const out: { section: string; items: SettingSchema[] }[] = []
    for (const s of list) {
      if (!matchesQuery(s)) continue
      const section = s.section ?? ''
      const last = out[out.length - 1]
      if (last && last.section === section) last.items.push(s)
      else out.push({ section, items: [s] })
    }
    return out
  }

  const groupsToRender = $derived(
    group(searching ? schema : showAdvanced ? schema : basic)
  )

  const visibleCount = $derived(groupsToRender.reduce((n, g) => n + g.items.length, 0))

  function clearQuery() {
    query = ''
  }
</script>

{#if title}
  <div class="form-title">{title}</div>
{/if}

{#if showSearch}
  <div class="form-search" role="search">
    <input
      type="text"
      bind:value={query}
      placeholder={placeholder}
      aria-label={placeholder}
    />
    {#if query}
      <button class="search-clear" onclick={clearQuery} aria-label={_('clear_search', 'Clear search')}>✕</button>
    {/if}
  </div>
{/if}

{#if presets.length > 0 && !searching}
  <PresetPicker {presets} {schema} {values} bind:applied={appliedPreset} apply={v => applyPreset?.(v)} />
{/if}

{#if !searching && hasAdvanced}
  <!-- svelte-ignore a11y_label_has_associated_control -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <label class="advanced-toggle">
    <Toggle checked={showAdvanced} onchange={() => showAdvanced = !showAdvanced} />
    <span>{_('advanced', 'Advanced')}</span>
  </label>
{/if}

{#each groupsToRender as g}
    {#if g.section}
      <div class="form-section">
        <div class="form-section-header">{g.section}</div>
        <table class="widget-list">
          {#each g.items as s}
            <SettingsWidget
              schema={s}
              bind:value={values[s.key]}
              baseline={baselineFor(s)}
              disabled={settingDisabled(s)}
              onaction={s.type === 'button' ? () => onaction?.(s.key) : undefined}
            />
          {/each}
        </table>
      </div>
    {:else}
      <table class="widget-list">
        {#each g.items as s}
          <SettingsWidget
            schema={s}
            bind:value={values[s.key]}
            baseline={baselineFor(s)}
            disabled={settingDisabled(s)}
            onaction={s.type === 'button' ? () => onaction?.(s.key) : undefined}
          />
        {/each}
      </table>
    {/if}
  {/each}

{#if searching && visibleCount === 0}
  <p class="form-empty">{_('no_settings_found', 'No settings match your search.')}</p>
{/if}

<style>
  .form-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    margin-bottom: 4px;
  }

  .form-search {
    position: relative;
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 6px;
  }

  .form-search input {
    flex: 1;
    min-width: 0;
  }

  .search-clear {
    flex-shrink: 0;
    font-size: 11px;
    padding: 2px 7px;
    border-color: transparent;
  }

  .search-clear:hover {
    color: var(--red);
    border-color: var(--red);
  }

  .advanced-toggle {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: var(--text-dim);
    padding: 6px 0 2px;
    border-top: 1px solid var(--border);
    margin-top: 6px;
    cursor: pointer;
  }

  .form-section {
    margin-top: 8px;
  }

  .form-section-header {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 3px;
    margin-bottom: 4px;
  }

  .form-empty {
    color: var(--text-dim);
    font-size: 12px;
    text-align: center;
    padding: 12px;
  }
</style>