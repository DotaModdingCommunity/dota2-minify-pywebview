<script lang="ts">
  import type { ModStatus } from '$lib/api'
  import { localeStore } from '$lib/stores/locale'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { status }: { status: ModStatus } = $props()

  const labels: Record<ModStatus, string> = {
    working: 'Working',
    broken: 'Broken',
    minor_issues: 'Minor Issues',
  }
</script>

<span class="badge {status}">{_(`status_${status}`, labels[status] ?? status)}</span>

<style>
  .badge {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 1px 6px 1px 4px;
    display: inline-block;
    width: fit-content;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
  }

  .broken       { border-left: 3px solid var(--red);    color: var(--red); }
  .minor_issues { border-left: 3px solid var(--yellow); color: var(--yellow); }
</style>
