<script lang="ts">
  let { checked = false, onchange }: { checked?: boolean; onchange?: () => void } = $props()
</script>

<span class="toggle-switch" class:on={checked} onclick={(e) => { e.stopPropagation(); onchange?.(); }}
  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); onchange?.(); } }}
  role="switch" aria-checked={checked} tabindex="0">
  <span class="toggle-thumb"></span>
</span>

<style>
  .toggle-switch {
    width: 36px;
    height: 18px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    cursor: pointer;
    flex-shrink: 0;
    position: relative;
    display: inline-block;
    transition: background 0.15s ease, border-color 0.15s ease;
    border-radius: 9px;
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.2);
  }

  .toggle-thumb {
    position: absolute;
    top: 1px;
    left: 1px;
    width: 14px;
    height: 14px;
    background: var(--text-dim);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.15s ease, box-shadow 0.15s ease;
    border-radius: 50%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }

  .toggle-switch.on {
    border-color: var(--accent);
    background: rgba(0, 230, 230, 0.06);
  }

  .toggle-switch.on .toggle-thumb {
    transform: translateX(18px);
    background: var(--accent);
    box-shadow: 0 0 10px var(--accent), 0 1px 3px rgba(0,0,0,0.3);
  }

  .toggle-switch:active { transform: scale(0.92); }
  .toggle-switch:active .toggle-thumb { transform: scale(0.9); }
  .toggle-switch.on:active .toggle-thumb { transform: translateX(18px) scale(0.9); }

  .toggle-switch:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
</style>
