<script lang="ts">
  import type { SettingSchema } from '$lib/api'
  import ComboBox from '$lib/components/ComboBox.svelte'
  import Toggle from '$lib/components/Toggle.svelte'

  let {
    schema,
    value = $bindable(),
    disabled = false,
    baseline,
    onaction,
  }: {
    schema: SettingSchema
    value: unknown
    disabled?: boolean
    baseline?: unknown
    onaction?: () => void
  } = $props()

  const HEX_RE = /^#[0-9a-fA-F]{6}$/

  let colorInput = $state<HTMLInputElement | undefined>(undefined)
  let hexText = $state('')

  let listItems = $state<string[]>([])
  let listNew = $state('')
  let listError = $state('')

  const recentColors = $state<string[]>(['#ffffff', '#000000', '#ff4444', '#ffd040', '#40ff80', '#00e6e6'])

  $effect(() => {
    const v = Array.isArray(value) ? value.map(String) : []
    if (JSON.stringify(v) !== JSON.stringify(listItems)) listItems = [...v]
  })

  const baselineVal = $derived(baseline === undefined ? schema.default : baseline)

  const changed = $derived(JSON.stringify(value) !== JSON.stringify(baselineVal))

  const numMin = $derived(schema.min ?? 0)
  const numMax = $derived(schema.max ?? 100)
  const numStep = $derived(schema.step ?? (schema.type === 'slider' ? 1 : 1))

  const numValue = $derived(Number(value))

  const numInvalid = $derived(
    typeof value === 'number' &&
      !Number.isNaN(value) &&
      (value < numMin || value > numMax)
  )

  const color = $derived(
    typeof value === 'string' && HEX_RE.test(value) ? value : '#000000'
  )

  const colorInvalid = $derived(
    typeof value === 'string' && value.length > 0 && !HEX_RE.test(value)
  )

  const listSuggestions = $derived(
    Array.isArray(schema.items) ? schema.items.map(String) : []
  )

  function reset() {
    if (disabled) return
    value = baselineVal
  }

  function clampSnap(n: number): number {
    let v = Number.isNaN(n) ? Number(schema.default ?? 0) : n
    v = Math.min(Math.max(v, numMin), numMax)
    if (numStep && numStep > 0) v = Math.round((v - numMin) / numStep) * numStep + numMin
    const dec = Math.max(0, -Math.floor(Math.log10(Math.abs(numStep) || 1)))
    const f = 10 ** dec
    return Math.round(v * f) / f
  }

  function onNumBlur() {
    if (disabled) return
    const v = clampSnap(Number(value))
    value = Object.is(v, -0) ? 0 : v
  }

  function onSliderChange() {
    if (disabled) return
    value = clampSnap(Number(value))
  }

  function onListItemInput(i: number, e: Event) {
    listItems[i] = (e.currentTarget as HTMLInputElement).value
    listError = ''
    value = listItems.map(x => x)
  }

  function addListItem(item?: string) {
    const t = (item ?? listNew).trim()
    if (!t) return
    if (schema.constrain && !listSuggestions.includes(t)) {
      listError = `Only these values are allowed: ${listSuggestions.join(', ')}`
      return
    }
    if (listItems.some(x => x.toLowerCase() === t.toLowerCase())) {
      listError = 'That value is already in the list.'
      return
    }
    listItems = [...listItems, t]
    listNew = ''
    listError = ''
    value = listItems.map(x => x)
  }

  function removeListItem(i: number) {
    listItems.splice(i, 1)
    listError = ''
    value = listItems.map(x => x)
  }

  function clearList() {
    listItems = []
    listError = ''
    value = []
  }

  function moveListItem(i: number, dir: -1 | 1) {
    const j = i + dir
    if (j < 0 || j >= listItems.length) return
    const next = [...listItems]
    ;[next[i], next[j]] = [next[j], next[i]]
    listItems = next
    value = next.map(x => x)
  }

  $effect(() => {
    if (typeof value === 'string' && HEX_RE.test(value)) {
      hexText = value.toUpperCase()
    }
  })

  function onHexInput(e: Event) {
    const text = (e.currentTarget as HTMLInputElement).value
    hexText = text
    const m = HEX_RE.exec(text)
    if (m) value = m[0].toLowerCase()
  }

  function onHexBlur() {
    if (!HEX_RE.test(hexText) && typeof value === 'string' && HEX_RE.test(value)) {
      hexText = value.toUpperCase()
    }
  }

  function onSwatchClick() {
    if (disabled) return
    colorInput?.click()
  }

  function onRecentColor(c: string) {
    if (disabled) return
    value = c
    hexText = c.toUpperCase()
  }

  function pushRecent(c: string) {
    if (!HEX_RE.test(c)) return
    const lower = c.toLowerCase()
    if (!recentColors.includes(lower)) {
      recentColors.unshift(lower)
      if (recentColors.length > 10) recentColors.pop()
    }
  }

  $effect(() => {
    if (changed && typeof value === 'string') pushRecent(value)
  })

  const fileLabel = $derived(
    typeof value === 'string' && value ? value.split(/[\\/]/).pop() ?? value : ''
  )

  async function openFile() {
    if (disabled || typeof value !== 'string' || !value) return
    try {
      await window.pywebview.api.open_path(value)
    } catch {
      // best-effort reveal; ignore bridge failures
    }
  }
</script>

<tr class="widget-row" class:disabled={disabled}>
  {#if schema.type === 'checkbox'}
    <td colspan="2">
      <div class="full-row">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
        <label class="check-label" onclick={() => { if (!disabled) value = !value }}>
          <Toggle checked={value as boolean} onchange={() => { if (!disabled) value = !value }} />
          <span>{schema.text}</span>
        </label>
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'combo'}
    <td class="label-cell"><span class="label">{schema.text}:</span></td>
    <td class="control-cell">
      <div class="control-row">
        <ComboBox
          value={value as string}
          options={(schema.items ?? []) as string[]}
          onchange={v => { if (!disabled) value = v }}
        />
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'number'}
    <td class="label-cell"><label class="label" for={`set-${schema.key}`}>{schema.text}:</label></td>
    <td class="control-cell">
      <div class="control-row">
        <input
          id={`set-${schema.key}`}
          type="number"
          bind:value
          step={numStep}
          min={numMin}
          max={numMax}
          class:invalid={numInvalid}
          disabled={disabled}
          onblur={onNumBlur}
        />
        {#if numInvalid}
          <span class="field-error" role="alert">Range {numMin}&ndash;{numMax}</span>
        {/if}
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'slider'}
    <td class="label-cell"><label class="label" for={`set-${schema.key}-slider`}>{schema.text}:</label></td>
    <td class="control-cell">
      <div class="control-row">
        <div class="slider-wrap">
          <input
            id={`set-${schema.key}-slider`}
            class="slider"
            type="range"
            bind:value
            step={numStep}
            min={numMin}
            max={numMax}
            disabled={disabled}
            onchange={onSliderChange}
          />
          <input
            id={`set-${schema.key}-num`}
            class="slider-num"
            type="number"
            bind:value
            aria-label={schema.text}
            step={numStep}
            min={numMin}
            max={numMax}
            class:invalid={numInvalid}
            disabled={disabled}
            onblur={onNumBlur}
          />
        </div>
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'color'}
    <td class="label-cell"><label class="label" for={`set-${schema.key}-hex`}>{schema.text}:</label></td>
    <td class="control-cell">
      <div class="control-row">
        <div class="color-picker">
          <button
            class="swatch"
            class:disabled={disabled}
            style:background={color}
            aria-label={schema.text}
            onclick={onSwatchClick}
          ></button>
          <input
            id={`set-${schema.key}-color`}
            class="color-pop-input"
            type="color"
            bind:this={colorInput}
            bind:value
            aria-label={schema.text}
            tabindex="-1"
            disabled={disabled}
          />
          <input
            id={`set-${schema.key}-hex`}
            class="hex"
            class:invalid={colorInvalid}
            type="text"
            value={hexText}
            placeholder="#RRGGBB"
            oninput={onHexInput}
            onblur={onHexBlur}
            disabled={disabled}
          />
        </div>
        {@render rowActions()}
      </div>
      {#if recentColors.length > 0}
        <div class="recent-colors" role="none">
          {#each recentColors as c}
            <button
              class="recent-swatch"
              class:active={value === c}
              style:background={c}
              onclick={() => onRecentColor(c)}
              aria-label={c}
            ></button>
          {/each}
        </div>
      {/if}
    </td>

  {:else if schema.type === 'button'}
    <td colspan="2">
      <div class="full-row">
        <button style="flex:1" onclick={() => { if (!disabled) onaction?.() }}>{schema.text}</button>
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'file'}
    <td colspan="2">
      <div class="full-row">
        <div class="file-row">
          <input id={`set-${schema.key}-file`} type="text" bind:value aria-label={schema.text} style="flex:1; min-width:0" disabled={disabled} />
          <button
            onclick={async () => {
              if (disabled) return
              const r = await window.pywebview.api.open_file_dialog(schema.file_types)
              if (r.ok && r.data) value = r.data
            }}
          >Browse</button>
          <button onclick={openFile} disabled={disabled || !fileLabel}>Open</button>
          <button onclick={() => { if (!disabled) value = schema.default ?? '' }} disabled={disabled}>Clear</button>
        </div>
        {#if fileLabel}
          <div class="file-hint" title={String(value)}>{fileLabel}</div>
        {/if}
        {@render rowActions()}
      </div>
    </td>

  {:else if schema.type === 'list'}
    <td class="label-cell"><label class="label" for={`set-${schema.key}-add`}>{schema.text}:</label></td>
    <td class="control-cell">
      <div class="control-row list-control">
        <div class="control-row-top">
          {@render rowActions()}
        </div>
        <div class="list-picker">
          {#each listItems as item, i (i)}
            <div class="list-item">
              <input
                id={`set-${schema.key}-${i}`}
                type="text"
                value={item}
                aria-label={schema.text}
                oninput={(e) => { if (!disabled) onListItemInput(i, e) }}
                disabled={disabled}
              />
              <button class="list-move" aria-label="Move up" onclick={() => { if (!disabled) moveListItem(i, -1) }} disabled={disabled || i === 0}>↑</button>
              <button class="list-move" aria-label="Move down" onclick={() => { if (!disabled) moveListItem(i, 1) }} disabled={disabled || i === listItems.length - 1}>↓</button>
              <button
                class="list-remove"
                aria-label="Remove item"
                onclick={() => { if (!disabled) removeListItem(i) }}
                disabled={disabled}
              >✕</button>
            </div>
          {/each}
          {#if listItems.length > 0}
            <button class="list-clear" onclick={clearList} disabled={disabled}>Clear all</button>
          {/if}
          <div class="list-item">
            <input
              id={`set-${schema.key}-add`}
              type="text"
              bind:value={listNew}
              aria-label={schema.text}
              placeholder="Add item..."
              disabled={disabled}
              onkeydown={(e) => { if (!disabled && e.key === 'Enter') addListItem() }}
            />
            <button class="list-add" onclick={() => { if (!disabled) addListItem() }} disabled={disabled}>Add</button>
          </div>
          {#if listSuggestions.length > 0}
            <div class="list-suggestions">
              {#each listSuggestions as sug}
                <button
                  class="list-chip"
                  class:used={listItems.some(x => x.toLowerCase() === sug.toLowerCase())}
                  onclick={() => { if (!disabled) addListItem(sug) }}
                  disabled={disabled}
                >+ {sug}</button>
              {/each}
            </div>
          {/if}
          {#if listError}
            <span class="field-error" role="alert">{listError}</span>
          {/if}
        </div>
      </div>
    </td>

  {:else}
    <!-- inputbox / default -->
    <td class="label-cell"><label class="label" for={`set-${schema.key}`}>{schema.text}:</label></td>
    <td class="control-cell">
      <div class="control-row">
        <input id={`set-${schema.key}`} class="inputbox" type="text" bind:value disabled={disabled} />
        {@render rowActions()}
      </div>
    </td>
  {/if}
</tr>

{#snippet rowActions()}
  <span class="row-actions">
    {#if schema.description}
      <button type="button" class="help" aria-label={schema.description} tabindex="0">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
        <span class="help-pop" role="tooltip">{schema.description}</span>
      </button>
    {/if}
    <button
      class="row-reset"
      class:changed={changed}
      title="Reset to default"
      aria-label={`Reset ${schema.text} to default`}
      aria-hidden={!changed}
      tabindex={changed ? 0 : -1}
      onclick={reset}
      disabled={disabled}
    >↺</button>
  </span>
{/snippet}

<style>
  .widget-row.disabled {
    opacity: 0.45;
  }

  .widget-row.disabled input,
  .widget-row.disabled button,
  .widget-row.disabled .swatch {
    cursor: not-allowed;
  }

  td {
    padding: 3px 0;
    vertical-align: middle;
    font-size: 12px;
  }

  td.label-cell {
    white-space: nowrap;
    width: 1%;
  }

  td.control-cell {
    padding-left: 8px;
    min-width: 0;
  }

  .full-row {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    min-width: 0;
  }

  .control-row {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .control-row > .row-actions,
  .full-row > .row-actions {
    margin-left: auto;
  }

  .control-row > input[type="text"].inputbox {
    flex: 1;
    width: auto;
    min-width: 0;
  }

  .control-row.list-control {
    flex-direction: column;
    align-items: stretch;
  }

  .control-row-top {
    display: flex;
    justify-content: flex-end;
    min-height: 0;
  }

  .control-row-top .row-actions {
    margin-left: 0;
  }

  .full-row > .file-row {
    flex: 1;
    width: auto;
    min-width: 0;
  }

  .check-label {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
  }

  .label {
    color: var(--text-dim);
    white-space: nowrap;
  }

  input[type="text"],
  input[type="number"] {
    max-width: 100%;
  }

  input[type="text"] {
    min-width: 160px;
  }

  input[type="text"].inputbox {
    width: 100%;
  }

  input[type="number"]:not(.slider-num) {
    min-width: 80px;
  }

  input.invalid {
    border-color: var(--red);
  }

  input.invalid:focus {
    outline-color: var(--red);
    border-color: var(--red);
  }

  .field-error {
    display: inline-block;
    margin-left: 8px;
    color: var(--red);
    font-size: 11px;
  }

  /* ── Row actions (help + reset) ─────────────────────── */

  .row-actions {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    margin-left: 6px;
    vertical-align: middle;
  }

  .row-reset {
    border: none;
    background: transparent;
    color: var(--text-muted);
    font-size: 12px;
    line-height: 1;
    padding: 0 2px;
    cursor: pointer;
    visibility: hidden;
  }

  .row-reset.changed {
    visibility: visible;
  }

  .row-reset:hover:not(:disabled) {
    color: var(--accent);
  }

  .row-reset:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }

  .help {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: help;
  }

  .help:hover,
  .help:focus-visible {
    color: var(--accent);
    outline: none;
  }

  .help-pop {
    position: absolute;
    left: 50%;
    bottom: calc(100% + 6px);
    transform: translateX(-50%);
    z-index: 60;
    min-width: 180px;
    max-width: 300px;
    padding: 6px 9px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-floating);
    color: var(--text);
    font-size: 11px;
    font-weight: 400;
    line-height: 1.45;
    white-space: normal;
    text-align: left;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.12s;
  }

  .help:hover .help-pop,
  .help:focus-visible .help-pop,
  .help:focus .help-pop {
    opacity: 1;
    pointer-events: auto;
  }

  /* ── Slider ─────────────────────────────────────────── */

  input.slider-num {
    flex: 0 0 60px;
    width: 60px;
    min-width: 60px;
    text-align: right;
  }

  .slider-wrap {
    display: flex;
    align-items: center;
    gap: 6px;
    width: fit-content;
    max-width: 100%;
  }

  input[type="range"].slider {
    -webkit-appearance: none;
    appearance: none;
    min-width: 140px;
    max-width: 100%;
    height: 4px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 999px;
    outline: none;
    cursor: pointer;
    accent-color: var(--accent);
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  input[type="range"].slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent);
    border: 1px solid rgba(255, 255, 255, 0.25);
    box-shadow: 0 0 8px var(--accent), 0 1px 3px rgba(0, 0, 0, 0.3);
    cursor: pointer;
    transition: transform 0.12s ease, box-shadow 0.12s ease;
  }

  input[type="range"].slider::-webkit-slider-thumb:hover,
  input[type="range"].slider::-webkit-slider-thumb:active {
    transform: scale(1.15);
    box-shadow: 0 0 12px var(--accent), 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  input[type="range"].slider:hover {
    border-color: var(--accent-dim);
  }

  input[type="range"].slider:focus {
    outline: none;
    border-color: var(--accent-dim);
  }

  input[type="range"].slider:focus::-webkit-slider-thumb {
    transform: scale(1.1);
    box-shadow: 0 0 12px var(--accent), 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  input[type="range"].slider:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  input[type="range"].slider:disabled::-webkit-slider-thumb {
    background: var(--text-muted);
    box-shadow: none;
  }

  /* ── Color ──────────────────────────────────────────── */

  .color-picker {
    position: relative;
    display: flex;
    align-items: center;
    gap: 6px;
    width: fit-content;
    max-width: 100%;
  }

  .swatch {
    width: 22px;
    height: 22px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    background-clip: padding-box;
    flex-shrink: 0;
    cursor: pointer;
    padding: 0;
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  .swatch:hover {
    border-color: var(--accent);
    box-shadow: 0 0 8px var(--accent-glow);
  }

  .hex {
    font-family: var(--font-mono);
    font-size: 11px;
    text-transform: uppercase;
    min-width: 64px;
    max-width: 100%;
  }

  .color-pop-input {
    position: absolute;
    top: calc(100% + 3px);
    left: 0;
    width: 1px;
    height: 1px;
    padding: 0;
    border: 0;
    opacity: 0;
    pointer-events: none;
  }

  .recent-colors {
    display: flex;
    flex-wrap: wrap;
    gap: 3px;
    margin-top: 4px;
  }

  .recent-swatch {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid var(--border);
    padding: 0;
    cursor: pointer;
  }

  .recent-swatch:hover {
    border-color: var(--accent);
  }

  .recent-swatch.active {
    box-shadow: 0 0 0 2px var(--accent);
  }

  /* ── File ───────────────────────────────────────────── */

  .file-row {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    min-width: 0;
  }

  .file-row button {
    flex-shrink: 0;
    font-size: 11px;
    padding: 2px 8px;
  }

  .file-hint {
    font-size: 10px;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
  }

  /* ── List ───────────────────────────────────────────── */

  .list-picker {
    display: flex;
    flex-direction: column;
    gap: 4px;
    width: 100%;
    min-width: 200px;
    max-width: 100%;
  }

  .list-item {
    display: flex;
    align-items: center;
    gap: 4px;
    width: 100%;
    min-width: 0;
  }

  .list-item input[type="text"] {
    flex: 1;
    min-width: 0;
  }

  .list-item button {
    flex-shrink: 0;
    font-size: 11px;
    padding: 2px 8px;
  }

  .list-move {
    padding: 2px 4px !important;
  }

  .list-remove:hover:not(:disabled) {
    color: var(--red);
    border-color: var(--red);
    background: rgba(255, 68, 68, 0.08);
  }

  .list-remove:focus-visible,
  :global(html.keyboard-focus) .list-remove:focus {
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }

  .list-clear {
    align-self: flex-start;
    font-size: 11px;
    padding: 1px 8px;
  }

  .list-clear:hover:not(:disabled) {
    color: var(--red);
    border-color: var(--red);
  }

  .list-suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .list-chip {
    font-size: 11px;
    padding: 1px 8px;
    border-radius: var(--radius-sm);
    background: var(--bg-hover);
  }

  .list-chip.used {
    opacity: 0.35;
    pointer-events: none;
  }
</style>