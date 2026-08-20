<script lang="ts">
  import { onMount } from "svelte";
  import { marked } from "marked";
  import DOMPurify from "dompurify";
  import type { Mod } from "$lib/api";
  import { localeStore } from "$lib/stores/locale";
  import Panel from './Panel.svelte'

  let _t = $derived($localeStore.t)
  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let { mod, onClose, zIndex }: { mod: Mod; onClose: () => void; zIndex?: number } = $props();

  let panelStyle = $derived(
    "--panel-max-width:90%;--panel-max-height:calc(94vh / var(--zoom));--panel-shadow:none;--panel-body-padding:14px 9px 14px 14px;--panel-body-gap:12px;--panel-overflow-anchor:auto;--panel-scroll-margin:14px" +
      (zIndex != null ? `;--overlay-z:${zIndex}` : "")
  )

  let previewSrc = $state<string | null>(null);
  let notesHtml = $state<string>("");
  let error = $state(false);

  onMount(async () => {
    try {
      if (mod.hasPreview) {
        const res = await window.pywebview.api.get_mod_preview(mod.raw_name);
        if (res.ok && res.data) previewSrc = res.data;
      }
      if (mod.hasNotes) {
        const res = await window.pywebview.api.get_mod_notes_html(mod.raw_name);
        if (res.ok && res.data) {
          const preprocessed = res.data.replace(/^!!:\s*(.+)$/gm, '<h4 class="note-warn">$1</h4>');
          notesHtml = DOMPurify.sanitize(marked(preprocessed) as string);
        }
      }
    } catch {
      error = true;
    }
  });

  function onKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }
</script>

<svelte:window onkeydown={onKeydown} />

<Panel
  title={mod.name}
  onClose={onClose}
  style={panelStyle}
>
      <div class="content">
        {#if previewSrc}
          <img class="preview" src={previewSrc} alt="Preview for {mod.name}" />
        {/if}
        {#if notesHtml}
          <div class="notes">{@html notesHtml}</div>
        {/if}
      </div>
      {#if error}
        <p class="error">{_("mod_details_error", "Failed to load details.")}</p>
      {:else if !previewSrc && !notesHtml}
        {#if mod.hasPreview || mod.hasNotes}
          <div class="loading">{_("loading", "Loading\u2026")}</div>
        {:else}
          <p class="empty">{_("no_details", "No details available.")}</p>
        {/if}
      {/if}
</Panel>

<style>
  .loading {
    color: var(--text-dim);
    text-align: center;
    padding: 16px;
  }

  .content {
    width: fit-content;
    min-width: min(636px, 100%);
    max-width: 100%;
    align-self: center;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .preview {
    max-width: 100%;
    height: auto;
    max-height: calc(80vh / var(--zoom));
    object-fit: contain;
    align-self: center;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
  }

  .notes {
    font-size: 12.5px;
    line-height: 1.6;
    color: var(--text);
    user-select: text;
    -webkit-user-select: text;
  }

  :global(.notes h1, .notes h2, .notes h3) {
    color: var(--accent);
    margin: 8px 0 4px;
  }
  :global(.notes .note-warn) {
    color: var(--red);
    font-size: 1.35em;
    font-weight: 700;
    margin: 10px 0 4px;
  }
  :global(.notes p) {
    margin-bottom: 6px;
  }
  :global(.notes code) {
    background: var(--bg-raised);
    padding: 1px 4px;
    font-size: 11px;
    font-family: var(--font-mono);
  }
  :global(.notes pre) {
    background: var(--bg-raised);
    padding: 8px;
    border-radius: var(--radius-sm);
    overflow-x: auto;
  }
  :global(.notes a) {
    color: var(--accent);
  }
  :global(.notes ul, .notes ol) {
    padding-left: 18px;
  }

  .error {
    color: var(--red);
    font-size: 12px;
    text-align: center;
    padding: 16px;
  }

  .empty {
    color: var(--text-dim);
    font-size: 12px;
  }
</style>
