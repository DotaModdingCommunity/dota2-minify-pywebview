<script lang="ts">
  let {
    mod,
    fileBase,
    refreshToken = 0,
  }: {
    mod: string
    fileBase: string
    refreshToken?: number
  } = $props()

  let loading = $state(true)
  let url = $state<string | null>(null)
  let isVideo = $state(false)

  $effect(() => {
    void refreshToken
    loading = true
    window.pywebview.api
      .get_mod_file_preview(mod, fileBase)
      .then(r => {
        url = r.ok ? r.data : null
        isVideo = !!url?.startsWith('data:video/')
      })
      .catch(() => {
        url = null
        isVideo = false
      })
      .finally(() => {
        loading = false
      })
  })
</script>

{#if loading}
  <div class="preview-loading">Loading preview&hellip;</div>
{:else if url}
  {#if isVideo}
    <video class="preview" src={url} muted loop playsinline autoplay></video>
  {:else}
    <img class="preview" src={url} alt="Preview" />
  {/if}
{:else}
  <div class="preview-empty">No preview available.</div>
{/if}

<style>
  .preview {
    display: block;
    max-width: 100%;
    max-height: 260px;
    width: auto;
    height: auto;
    object-fit: contain;
    align-self: center;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 8px;
  }

  .preview-loading,
  .preview-empty {
    width: 100%;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-size: 12px;
    border: 1px dashed var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 8px;
  }
</style>