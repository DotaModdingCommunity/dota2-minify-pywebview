<script lang="ts">
  import { untrack } from 'svelte'
  import ComboBox from '$lib/components/ComboBox.svelte'
  import { localeStore } from '$lib/stores/locale'
  import { modalStore } from '$lib/stores/modal'
  import type { ModPreset, SettingSchema } from '$lib/api'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

let {
    presets,
    schema,
    values,
    apply,
    disabled = false,
    applied = $bindable(null),
  }: {
    presets: ModPreset[]
    schema: SettingSchema[]
    values: Record<string, unknown>
    apply: (values: Record<string, unknown>) => void
    disabled?: boolean
    applied?: string | null
  } = $props()

  const placeholder = $derived(_('select_preset', 'Select preset\u2026'))
  const customLabel = $derived(_('custom', 'Custom'))
  const defaultLabel = $derived(_('default', 'Default'))

  let loadedValues = $state<Record<string, unknown>>({})

  $effect(() => {
    presets
    schema
    applied = null
    loadedValues = untrack(() => ({ ...values }))
  })

  const options = $derived(
    presets.some(p => p.name === defaultLabel)
      ? presets.map(p => p.name)
      : [defaultLabel, ...presets.map(p => p.name)]
  )

  const appliedPreset = $derived(
    applied ? presets.find(p => p.name === applied) ?? null : null
  )

  const presetSummary = $derived(
    appliedPreset
      ? schema
          .filter(s => s.key in appliedPreset.values && JSON.stringify(appliedPreset.values[s.key]) !== JSON.stringify(s.default))
          .map(s => s.text)
      : []
  )

  const baseline = $derived(appliedPreset ? compose(appliedPreset) : loadedValues)

  const isCustom = $derived(JSON.stringify(values) !== JSON.stringify(baseline))

  const isDefault = $derived(JSON.stringify(values) === JSON.stringify(defaultsValues()))

  const display = $derived(isCustom ? (isDefault ? defaultLabel : customLabel) : applied ?? defaultLabel)

  function defaultsValues() {
    return Object.fromEntries(schema.map(s => [s.key, s.default]))
  }

  function compose(preset: ModPreset) {
    const known = new Set(schema.map(s => s.key))
    const presetValues = Object.fromEntries(
      Object.entries(preset.values).filter(([k]) => known.has(k))
    )
    return { ...defaultsValues(), ...presetValues }
  }

  function doApply(preset: ModPreset) {
    apply(compose(preset))
    applied = preset.name
  }

  function doDefaults() {
    apply(defaultsValues())
    applied = null
  }

  function confirmAnd(fn: () => void, label: string, msgKey: string, fb: string) {
    const msg = _(msgKey, fb)
    modalStore.set({
      title: _("preset", "Preset"),
      messages: [msg.replace("{preset}", label)],
      buttons: [_("cancel", "Cancel"), _("apply", "Apply")],
      onrespond: (btn: string) => {
        if (btn === _("apply", "Apply")) fn()
      },
    })
  }

  function onSelect(name: string) {
    if (disabled) return
    if (name === defaultLabel) {
      const applyNow = () => doDefaults()
      if (isCustom) confirmAnd(applyNow, defaultLabel, "default_apply_confirm", "Apply default values? Your current changes will be reset.")
      else applyNow()
      return
    }
    const preset = presets.find(p => p.name === name)
    if (!preset) return
    if (isCustom) confirmAnd(() => doApply(preset), preset.name, "preset_apply_confirm", "Apply preset '{preset}'? Your current changes will be reset.")
    else doApply(preset)
  }
</script>

{#if presets.length > 0}
  <div class="preset-row" class:disabled={disabled}>
    <span class="preset-label">{_('preset', 'Preset')}:</span>
    <ComboBox value={display} options={options} placeholder={placeholder} onchange={onSelect} />
  </div>
  {#if appliedPreset?.description}
    <div class="preset-desc">{appliedPreset.description}</div>
  {/if}
  {#if presetSummary.length > 0}
    <div class="preset-summary">
      <span class="preset-summary-label">{_('preset_changes', 'Applies')}:</span>
      <span>{presetSummary.join(', ')}</span>
    </div>
  {/if}
{/if}

<style>
  .preset-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    font-size: 12px;
  }

  .preset-row.disabled {
    opacity: 0.45;
    pointer-events: none;
  }

  .preset-label {
    color: var(--text-dim);
    white-space: nowrap;
  }

  .preset-desc {
    font-size: 11px;
    line-height: 1.45;
    color: var(--text-dim);
    padding: 3px 0 0 0;
  }

  .preset-summary {
    font-size: 10.5px;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preset-summary-label {
    color: var(--accent);
  }
</style>