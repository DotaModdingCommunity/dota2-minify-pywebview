<script lang="ts">
  import { fade, scale } from 'svelte/transition'
  import { onMount } from 'svelte'
  import { smoothscroll } from '$lib/actions/smoothscroll'

  let {
    value = '',
    options = [] as string[],
    placeholder,
    onchange,
  }: {
    value: string
    options: string[]
    placeholder?: string
    onchange?: (val: string) => void
  } = $props()

  let open = $state(false)
  let flip = $state(false)
  let rootEl: HTMLDivElement

  $effect(() => {
    if (open && rootEl) {
      const trigger = rootEl.querySelector('.trigger')!
      const triggerRect = trigger.getBoundingClientRect()
      const spaceBelow = window.innerHeight - triggerRect.bottom
      flip = spaceBelow < 180
    }
  })

  function select(opt: string) {
    open = false
    onchange?.(opt)
  }

  function toggle() {
    open = !open
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') open = false
  }

  onMount(() => {
    const clickHandler = (e: MouseEvent) => {
      if (open && rootEl && !rootEl.contains(e.target as Node)) {
        open = false
      }
    }
    document.addEventListener('click', clickHandler, true)

    const wheelHandler = (e: WheelEvent) => {
      if (open && rootEl && !rootEl.contains(e.target as Node)) {
        e.preventDefault()
      }
    }
    document.addEventListener('wheel', wheelHandler, { capture: true, passive: false })

    return () => {
      document.removeEventListener('click', clickHandler, true)
      document.removeEventListener('wheel', wheelHandler, { capture: true })
    }
  })
</script>

<svelte:window onkeydown={onKeydown} />

<div class="combo" bind:this={rootEl}>
  <button class="trigger" class:open onclick={toggle}>
    <span class="trigger-text" class:placeholder={!value}>{value || placeholder}</span>
    <span class="arrow">&#9660;</span>
  </button>
  {#if open}
    <div class="dropdown" class:flip in:scale={{ start: 0.95, duration: 120 }} out:fade={{ duration: 80 }}>
      <div class="dropdown-scroll" data-scrollable onwheel={(e) => e.stopPropagation()} use:smoothscroll>
        {#each options as opt}
          <button
            class="option"
            class:selected={opt === value}
            onclick={() => select(opt)}
          >
            {opt}
          </button>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .combo {
    position: relative;
  }

  .trigger {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 100%;
    padding: 4px 8px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius-sm);
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.12s;
    text-align: left;
  }

  .trigger:hover {
    border-color: var(--accent-dim);
  }

  .trigger.open {
    border-color: var(--accent-dim);
  }

  .trigger-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .trigger-text.placeholder {
    color: var(--text-muted);
  }

  .arrow {
    font-size: 7px;
    color: var(--text-dim);
    flex-shrink: 0;
    transition: transform 0.12s;
  }

  .open .arrow {
    transform: rotate(180deg);
  }

  .dropdown {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    min-width: 100%;
    max-width: min(420px, calc((100vw - 24px) / var(--zoom)));
    z-index: 50;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-floating);
    overflow: hidden;
    transform-origin: top left;
  }

  .dropdown-scroll {
    max-height: 180px;
    overflow-x: hidden;
    overflow-y: auto;
    overscroll-behavior: contain;
    margin-right: 3px;
  }

  .dropdown-scroll::-webkit-scrollbar-track {
    margin-top: 8px;
    margin-bottom: 8px;
  }

  .dropdown.flip {
    top: auto;
    bottom: calc(100% + 2px);
    transform-origin: bottom left;
  }

  .option {
    display: block;
    box-sizing: border-box;
    padding: 5px 10px;
    background: transparent;
    border: none;
    color: var(--text);
    font-size: 12px;
    text-align: left;
    white-space: nowrap;
    cursor: pointer;
    border-radius: 0;
    margin-right: 3px;
  }

  .option:hover {
    background: var(--bg-hover);
  }

  .option.selected {
    color: var(--accent);
    font-weight: 500;
  }
</style>
