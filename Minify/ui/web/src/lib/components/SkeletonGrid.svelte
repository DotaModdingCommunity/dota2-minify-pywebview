<script lang="ts">
  let { count = 6 }: { count?: number } = $props()
</script>

<div class="skeleton-grid">
  {#each { length: count } as _i}
    <div class="skeleton-card">
      <div class="skeleton-img"></div>
      <div class="skeleton-line short"></div>
      <div class="skeleton-line"></div>
    </div>
  {/each}
</div>

<style>
  .skeleton-grid {
    flex: 1;
    min-height: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 12px;
    padding: 12px;
    align-content: start;
    justify-content: center;
  }

  .skeleton-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 5px;
    border-radius: 12px;
  }

  .skeleton-img {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: var(--bg-raised);
    border-radius: 5px;
  }

  .skeleton-line {
    height: 10px;
    background: var(--bg-raised);
  }

  .skeleton-line.short { width: 60%; }

  .skeleton-card > * {
    position: relative;
    overflow: hidden;
  }

  .skeleton-card > *::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      105deg,
      transparent 25%,
      rgba(154, 154, 165, 0.12) 42%,
      rgba(154, 154, 165, 0.2) 50%,
      rgba(154, 154, 165, 0.12) 58%,
      transparent 75%
    );
    transform: translateX(-100%);
    pointer-events: none;
    animation: shimmer 5s ease-in-out infinite;
  }

  @keyframes shimmer {
    0%   { transform: translateX(-100%); }
    40%  { transform: translateX(100%); }
    100% { transform: translateX(100%); }
  }
</style>