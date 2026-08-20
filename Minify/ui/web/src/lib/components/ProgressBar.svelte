<script lang="ts">
  let { pct, style = "" }: { pct: number; style?: string } = $props()
</script>

<div class="track" {style}>
  <div
    class="fill"
    class:indeterminate={pct <= 0}
    class:done={pct >= 100}
    style="width: {pct}%"
  ></div>
</div>

<style>
  .track {
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
  }

  .fill {
    height: 100%;
    width: 0%;
    background: var(--accent);
    border-radius: var(--radius-sm);
    transition: width 0.25s ease;
    box-shadow: 0 0 8px var(--accent-glow);
    position: relative;
    overflow: hidden;
  }

  .fill.indeterminate {
    width: 30%;
    animation: pb-slide 1.6s ease-in-out infinite;
  }

  .fill.done {
    width: 100% !important;
    background: var(--accent-secondary);
    animation: none;
  }

  @keyframes pb-slide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(400%); }
  }
</style>