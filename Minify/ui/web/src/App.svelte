<script lang="ts">
  import { fade, fly } from 'svelte/transition'
  import { onMount, onDestroy } from "svelte";
  import { terminalStore, resolveText } from "$lib/stores/terminal";
  import { modalStore } from "$lib/stores/modal";
  import { hudStore } from "$lib/stores/hud";
  import { loadLocale } from "$lib/i18n.svelte";
  import { setupStore } from "$lib/stores/setup";
  import { setupFlowStore } from "$lib/stores/setupFlow";
  import { lock, depsDownloading } from "$lib/stores/lock";
  import { settingsOpen, settingsStore } from "$lib/stores/settings";
  import { searchQuery } from "$lib/stores/search";
  import { patchRunning } from "$lib/stores/patchProgress";
  import { modsStore } from "$lib/stores/mods";
  import { d2pfxMods, d2pfxEnabledCount, d2pfxEnabledCountFromApi, d2pfxTotalCount, d2pfxCategories, d2pfxLoading, selectedCategory } from "$lib/stores/d2pfx";
  import { detailOverlayOpen } from "$lib/stores/overlay";
  import { localeStore } from "$lib/stores/locale";
  import { ready } from "$lib/stores/bridge";
  import { applyZoom, cycleZoom, zoomBy, ZOOM_STEP } from "$lib/zoom";
  import Setup from "$lib/components/Setup.svelte";
  import Welcome from "$lib/components/Welcome.svelte";

  import ActionButtons from "$lib/components/ActionButtons.svelte";
  import ModGrid from "$lib/components/ModGrid.svelte";
  import D2pfxBrowser from "$lib/components/D2pfxBrowser.svelte";
  import DevTools from "$lib/components/DevTools.svelte";


  import Modal from "$lib/components/Modal.svelte";
  import SetupFlow from "$lib/components/SetupFlow.svelte";
  import Terminal from "$lib/components/Terminal.svelte";
  import StatusBarCenter from "$lib/components/StatusBarCenter.svelte";

loadLocale("EN").catch(() => {});

  let _t = $derived($localeStore.t)

  let hasEnabledMods = $derived(
    $modsStore.some(m => !m.always && m.enabled) ||
    $d2pfxEnabledCountFromApi > 0 ||
    Object.values($d2pfxMods).some(catMods => catMods.some(m => m.enabled))
  )

  function _(key: string, fb?: string) { return _t[key] ?? fb ?? key }

  let showWelcome = $state(false);
  let showDevTools = $derived(!!$settingsStore?.values?.global?.devtools_enabled);
  let activeTab = $state<"mods" | "d2pfx" | "devtools" | "terminal">("mods");
  let lastTab = $state<"mods" | "d2pfx" | "devtools">("mods");

  function openTerminal() {
    if (activeTab !== 'terminal') lastTab = activeTab as 'mods' | 'd2pfx' | 'devtools';
    activeTab = 'terminal';
  }

  function closeTerminal() {
    if ($lock) return;
    activeTab = lastTab;
  }

  function cycleTab(forward: boolean) {
    const tabs: Array<"mods" | "d2pfx" | "devtools" | "terminal"> = showDevTools
      ? ["mods", "d2pfx", "devtools", "terminal"]
      : ["mods", "d2pfx", "terminal"];
    const idx = tabs.indexOf(activeTab);
    const next = tabs[(idx + (forward ? 1 : -1) + tabs.length) % tabs.length];
    if (next === "terminal") openTerminal();
    else { lastTab = next; activeTab = next; }
  }

  let totalMods = $derived($modsStore.filter(m => !m.always).length + $d2pfxTotalCount)
  let enabledMods = $derived(
    $modsStore.filter(m => !m.always && m.enabled).length +
    Math.max($d2pfxEnabledCount, $d2pfxEnabledCountFromApi)
  )

  let appVersion = $state("");
  let appInfo = $state<{
    discord: string;
    telegram: string;
    github_io: string;
  } | null>(null);

  let _bridgeReady = false;
  let _backendReady = false;

  const isMac = navigator.platform?.toLowerCase().includes("mac") ?? false;

  let searchOpen = $state(false);
  let searchInput = $state<HTMLInputElement | null>(null);
  let showShortcuts = $state(false);
  let refreshing = $state(false);
  let _refreshStart = 0;

  function refreshD2pfxCounts() {
    window.pywebview.api.get_d2pfx_counts().then((res3) => {
      if (res3.ok) {
        d2pfxTotalCount.set(res3.data.total)
        d2pfxEnabledCountFromApi.set(res3.data.enabled)
      }
    })
  }

  const MIN_REFRESH_MS = 450

  async function refreshActiveTab() {
    if (refreshing) return
    refreshing = true
    _refreshStart = Date.now()
    try {
      if (activeTab === 'mods') {
        const res = await window.pywebview.api.refresh_mods()
        if (res.ok) {
          const mods = await window.pywebview.api.get_mods()
          if (mods.ok) modsStore.set(mods.data)
        }
      } else if (activeTab === 'd2pfx') {
        d2pfxLoading.set(true)
        try {
          const cats = await window.pywebview.api.get_d2pfx_categories()
          if (cats.ok) {
            d2pfxCategories.set(cats.data)
            refreshD2pfxCounts()
            const sel = $selectedCategory ?? (cats.data[0]?.id ?? null)
            if (sel) {
              selectedCategory.set(sel)
              const mods = await window.pywebview.api.get_d2pfx_mods(sel)
              if (mods.ok) {
                d2pfxMods.update(m => ({ ...m, [sel]: mods.data }))
              }
            }
          }
        } catch (e) {
          modalStore.set({ title: "Error", messages: [String(e)], buttons: ["OK"] })
        } finally {
          d2pfxLoading.set(false)
        }
      }
    } finally {
      const elapsed = Date.now() - _refreshStart
      if (elapsed < MIN_REFRESH_MS) await new Promise(r => setTimeout(r, MIN_REFRESH_MS - elapsed))
      refreshing = false
    }
  }

  onMount(() => {
    (window as any).__termPush = (payload: {
      raw: string;
      args: unknown[];
      type: string | null;
    }) => {
      terminalStore.pushLine(payload.raw, payload.args ?? [], payload.type);
    };
    (window as any).__termSep = () => {
      terminalStore.pushSeparator();
    };
    (window as any).__termClear = () => {
      terminalStore.clear();
    };
    (window as any).__modalPush = (payload: {
      title: string;
      messages: string[];
      buttons: string[];
      id: string;
    }) => {
      modalStore.push({ ...payload, onrespond: (label: string) => {
        window.pywebview.api.modal_respond(payload.id, label);
      } });
    };
    (window as any).__hudPush = (payload: {
      messages: string[];
      value: number;
      status: string;
      args?: unknown[];
    }) => {
      hudStore.set({ ...payload, visible: true });
    };
    (window as any).__hudSetProgress = (payload: {
      value: number;
      status: string;
      args?: unknown[];
    }) => {
      hudStore.update((h) => (h ? { ...h, ...payload } : h));
    };
    (window as any).__hudHide = () => {
      hudStore.set(null);
    };
    (window as any).__setLocked = (val: boolean) => {
      lock.set(val);
    };
    (window as any).__setDepsDownloading = (val: boolean) => {
      depsDownloading.set(val);
    };

    (window as any).__setupFlowPush = (payload: {
      pending: { name: string; message: string }[];
      id: string;
    }) => {
      setupFlowStore.set({ pending: payload.pending, waiterId: payload.id });
    };
    (window as any).__d2pfxLoaded = () => {
      refreshD2pfxCounts();
    };

    (window as any).__patchEnd = () => {
      modalStore.push({
        title: _("patch_complete", "Patch Complete"),
        messages: [
          _("start_text_1_var", "Want to contribute to the project's growth?"),
          _("start_text_2_var", "-> Join our Discord or Telegram community!"),
          _("start_text_3_var", "-> Share Minify with your friends and online groups"),
          _("start_text_4_var", "-> Star the project on GitHub"),
          _("start_text_5_var", "-> Create and maintain mods for this project"),
        ],
        buttons: [_("ok", "OK")],
        social: appInfo
          ? { discord: appInfo.discord, telegram: appInfo.telegram, github_io: appInfo.github_io }
          : undefined,
        onrespond: () => patchRunning.set(false),
      });
      lock.set(false);
    };
    (window as any).__patchCancelled = () => {
      patchRunning.set(false);
      lock.set(false);
      closeTerminal();
    };
    (window as any).__patchError = (msg: string) => {
      modalStore.push({
        title: _("patch_failed", "Patch Failed"),
        messages: [msg, _("check_terminal", "Check the terminal above for full error details")],
        buttons: [_("ok", "OK")],
        onrespond: () => patchRunning.set(false),
      });
      lock.set(false);
    };
    (window as any).__uninstallEnd = () => {
      modalStore.push({
        title: _t["uninstall_complete"] ?? "Uninstall Complete",
        messages: [_t["uninstall_done"] ?? "All mods have been removed from the game."],
        buttons: ["OK"],
      });
    };
    (window as any).__dropComplete = (payload?: { ok?: boolean; error?: string | null }) => {
      if (payload && payload.ok === false) {
        modalStore.push({
          title: "Drop Install",
          messages: [payload.error ?? "One or more files failed to install."],
          buttons: ["OK"],
        });
      }
      refreshActiveTab();
      window.dispatchEvent(new CustomEvent('dropcomplete'));
    };
    (window as any).__hideDropOverlay = () => {
      window.dispatchEvent(new CustomEvent('dropcomplete'));
    };

    // Signal Python that our handlers are registered so buffered JS is flushed.
    const notifyReady = () => window.pywebview?.api?.frontend_ready?.();
    notifyReady();
    window.addEventListener("pywebviewready", notifyReady, { once: true });

    window.addEventListener("wheel", zoomWheelHandler, { capture: true, passive: false });

    function checkReady() {
      if (_bridgeReady && _backendReady) {
        ready.set(true)
        initApp()
      }
    }

    (window as any).__backendReady = () => { _backendReady = true; checkReady() }
    window.addEventListener("pywebviewready", () => { _bridgeReady = true; checkReady() }, { once: true })
    if (window.pywebview?.api) { _bridgeReady = true; checkReady() }

    setTimeout(() => {
      if (!_bridgeReady || !_backendReady) {
        console.error("backend failed to initialize after 30s")
        const el = document.createElement("div")
        el.style.cssText = "position:fixed;inset:0;display:flex;align-items:center;justify-content:center;color:var(--red);font-size:13px;"
        el.textContent = "Failed to connect to application backend. Please restart."
        document.body.appendChild(el)
      }
    }, 30_000)

    function initApp() {
      window.pywebview.api.get_setup_state().then((res) => {
        if (res.ok && !res.data.complete) {
          loadLocale("EN");
          setupStore.set({
            step: 1,
            data: {
              lang: "EN",
              game_lang: "english",
              steam_ids: [],
            },
          });
        }
        window.pywebview.api.get_app_info().then((res2) => {
          if (res2.ok) {
            loadLocale(res2.data.current_lang);
            appVersion = res2.data.version;
            appInfo = res2.data;
          } else {
            console.error("get_app_info failed:", res2.error);
          }
          refreshD2pfxCounts()
          window.pywebview.api.get_welcome_state().then((r) => {
            if (r.ok && r.data.show) {
              showWelcome = true;
            }
          })
          window.pywebview.api.get_settings().then((r) => {
            if (r.ok) settingsStore.set(r.data)
          })
        });
      }).catch((err) => {
        console.error("get_setup_state failed:", err);
      });
    }
  });

  onDestroy(() => {
    delete (window as any).__termPush;
    delete (window as any).__termSep;
    delete (window as any).__termClear;
    delete (window as any).__modalPush;
    delete (window as any).__hudPush;
    delete (window as any).__hudSetProgress;
    delete (window as any).__hudHide;
    delete (window as any).__setLocked;
    delete (window as any).__setDepsDownloading;
    delete (window as any).__setupFlowPush;
    delete (window as any).__d2pfxLoaded;
    delete (window as any).__patchEnd;
    delete (window as any).__patchCancelled;
    delete (window as any).__patchError;
    delete (window as any).__uninstallEnd;
    delete (window as any).__dropComplete;
    delete (window as any).__hideDropOverlay;
    window.removeEventListener("wheel", zoomWheelHandler, { capture: true });
  });

  $effect(() => {
    if ($patchRunning) {
      openTerminal();
    }
  });

  $effect(() => {
    if (!showDevTools && activeTab === 'devtools') {
      activeTab = 'mods';
    }
  });

  function dismissWelcome() {
    showWelcome = false;
    window.pywebview?.api.dismiss_welcome();
  }

  async function handlePatch() {
    patchRunning.set(true);
    lock.set(true);
    try {
      const res = await window.pywebview.api.patch();
      if (!res.ok) {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] });
        patchRunning.set(false);
        lock.set(false);
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [String(e)], buttons: ["OK"] });
      patchRunning.set(false);
      lock.set(false);
    }
  }

  async function handleUninstall() {
    if ($lock) return;
    try {
      const res = await window.pywebview.api.uninstall();
      if (!res.ok) {
        modalStore.set({ title: "Error", messages: [res.error], buttons: ["OK"] });
      }
    } catch (e) {
      modalStore.set({ title: "Error", messages: [`Failed to uninstall: ${e}`], buttons: ["OK"] });
    }
  }

  async function openUrl(url: string) {
    try {
      await window.pywebview.api.open_url(url);
    } catch {
      // best-effort external link; ignore bridge failures
    }
  }

  function openSearch() {
    searchOpen = true;
    requestAnimationFrame(() => searchInput?.focus());
  }

  function closeSearch() {
    searchOpen = false;
    searchQuery.set("");
  }

  let _zoomAcc = 0
  const zoomWheelHandler = (e: WheelEvent) => {
    if (!e.ctrlKey) return
    e.preventDefault()
    _zoomAcc += e.deltaY
    const stepPx = 100
    while (Math.abs(_zoomAcc) >= stepPx) {
      const dir = _zoomAcc > 0 ? -1 : 1
      zoomBy(dir * ZOOM_STEP)
      _zoomAcc -= Math.sign(_zoomAcc) * stepPx
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.ctrlKey || e.metaKey) {
      if (e.code === "Equal" || e.code === "NumpadAdd") {
        e.preventDefault();
        cycleZoom(1);
        return;
      } else if (e.code === "Minus" || e.code === "NumpadSubtract") {
        e.preventDefault();
        cycleZoom(-1);
        return;
      } else if (e.code === "Digit0" || e.code === "Numpad0") {
        e.preventDefault();
        applyZoom(1);
        return;
      }
    }
    if ($modalStore || $setupStore || $settingsOpen || $detailOverlayOpen || showWelcome) return;
    if ($patchRunning || $lock) return;
    if (searchOpen) {
      if (e.code === "Escape") closeSearch();
      return;
    }
    if ((e.ctrlKey || e.metaKey) && e.code === "Tab") {
      e.preventDefault();
      cycleTab(!e.shiftKey);
      return;
    }
    const tag = document.activeElement?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return;
    if ((e.ctrlKey || e.metaKey) && e.code === "KeyF") {
      e.preventDefault();
      openSearch();
    } else if ((e.ctrlKey || e.metaKey) && e.code === "KeyR") {
      e.preventDefault();
      refreshActiveTab();
    } else if (e.code === "Escape") {
      if (searchOpen) { closeSearch(); return; }
      if (showShortcuts) { showShortcuts = false; return; }
    } else if (e.code === "KeyH") {
      showShortcuts = !showShortcuts;
    } else if (e.code === "KeyP" && hasEnabledMods && !$depsDownloading) {
      handlePatch();
    } else if (e.code === "KeyU") {
      handleUninstall();
    } else if (e.code === "Space") {
      const el = document.activeElement as HTMLElement | null
      const interactive = !!el?.closest(
        'button, a[href], input, select, textarea, [contenteditable], [tabindex], [role="button"], [role="checkbox"], [role="switch"]'
      )
      if (!interactive) e.preventDefault();
    } else if (e.code === "KeyS") {
      settingsOpen.set(true);
    } else if (e.code === "KeyT") {
      if (activeTab === 'terminal') closeTerminal();
      else openTerminal();
    }
  }

</script>

<svelte:window onkeydown={handleKeydown} />

<div class="stage">
{#if $setupStore}
  <Setup />
{:else}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="app" role="none">

    {#if searchOpen}
      <div class="search-overlay" in:fade={{ duration: 120 }} out:fade={{ duration: 80 }} role="none">
        <div class="search-bar" in:fly={{ y: -8, duration: 120 }} out:fade={{ duration: 80 }} role="none">
          <input
            id="global-search"
            type="text"
            class="search-input"
            bind:this={searchInput}
            bind:value={$searchQuery}
            placeholder={_("search_placeholder", "Search mods\u2026")}
            aria-label={_("search_mods", "Search mods")}
            onkeydown={(e: KeyboardEvent) => { if (e.code === 'Escape') closeSearch(); }}
          />
          <button class="search-close" onclick={closeSearch} title={_("close", "Close")}>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18"></path><path d="M6 6 18 18"></path></svg>
          </button>
        </div>
      </div>
    {/if}

    {#if showShortcuts}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div class="shortcuts-popover" in:fade={{ duration: 120 }} out:fade={{ duration: 80 }} onclick={() => showShortcuts = false} role="none">
        <div class="shortcuts-box">
          <h3>{_("keyboard_shortcuts", "Keyboard Shortcuts")}</h3>
          <div class="shortcut-row"><kbd>P</kbd><span>{_("button_patch", "Patch")}</span></div>
          <div class="shortcut-row"><kbd>S</kbd><span>{_("settings", "Settings")}</span></div>
          <div class="shortcut-row"><kbd>U</kbd><span>{_("button_uninstall", "Uninstall")}</span></div>
          <div class="shortcut-row"><kbd>{isMac ? "Cmd+F" : "Ctrl+F"}</kbd><span>{_("search_mods", "Search mods")}</span></div>
          <div class="shortcut-row"><kbd>{isMac ? "Cmd+R" : "Ctrl+R"}</kbd><span>{_("refresh_mods", "Refresh mods")}</span></div>
          <div class="shortcut-row"><kbd>T</kbd><span>{_("terminal", "Terminal")}</span></div>
          <div class="shortcut-row"><kbd>H</kbd><span>{_("help", "Help")}</span></div>
          <div class="shortcut-row"><kbd>Esc</kbd><span>{_("close_panel", "Close panel")}</span></div>
        </div>
      </div>
    {/if}

    <div class="app-header">
      <ActionButtons />
      <span class="header-spacer"></span>
        <div class="social-row">
          <button class="social-btn" title="Discord" onclick={() => openUrl(appInfo?.discord ?? "")}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
              ><path
                d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z"
              /></svg
            >
          </button>
          <button class="social-btn" title="Telegram" onclick={() => openUrl(appInfo?.telegram ?? "")}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
              ><path
                d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
              /></svg
            >
          </button>
          <button class="social-btn" title="GitHub" onclick={() => openUrl(appInfo?.github_io ?? "")}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"
              ><path
                d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
              /></svg
            >
          </button>
        </div>
    </div>
    <div class="app-main">
      {#if activeTab === 'mods'}
        <ModGrid refreshing={refreshing} />
      {:else if activeTab === 'devtools'}
        <DevTools />
      {:else if activeTab === 'd2pfx'}
        <D2pfxBrowser refreshing={refreshing} />
      {:else}
        <Terminal onClose={closeTerminal} />
      {/if}
    </div>
    <div class="status-bar">
      <button class="tab-btn" class:active={activeTab === 'mods'} disabled={$lock} onclick={() => { lastTab = 'mods'; activeTab = 'mods'; }}>
        {_("tab_minify_mods", "Minify Mods")}
      </button>
      <button class="tab-btn" class:active={activeTab === 'd2pfx'} disabled={$lock} onclick={() => { lastTab = 'd2pfx'; activeTab = 'd2pfx'; }}>
        {_("tab_d2pfx_mods", "D2PFX Mods")}
      </button>
      {#if showDevTools}
        <button class="tab-btn" class:active={activeTab === 'devtools'} disabled={$lock} onclick={() => { lastTab = 'devtools'; activeTab = 'devtools'; }}>
          {_("tab_devtools", "Dev Tools")}
        </button>
      {/if}
      <button class="tab-btn" class:active={activeTab === 'terminal'} disabled={$lock} onclick={openTerminal}>
        {_("terminal", "Terminal")}
      </button>
      <button class="refresh-btn" class:refreshing onclick={refreshActiveTab} disabled={refreshing || $lock} title={_("refresh_mods", "Refresh mods")}>↻<span class="refresh-shimmer" aria-hidden="true"></span></button>
      <StatusBarCenter />
      <span class="status-item mod-count">{resolveText("&mods_count", [enabledMods, totalMods], _t)}</span>
      <span class="status-sep"></span>
      <span class="status-item version">{appVersion}</span>
      <span class="status-sep"></span>
      <button class="social-btn help-btn" class:active={showShortcuts} onclick={() => showShortcuts = !showShortcuts} title={_("help", "Help")}>H</button>
    </div>
  </div>
{/if}
<Modal />

{#if showWelcome}
  <Welcome onDismiss={dismissWelcome} />
{/if}

{#if $setupFlowStore}
  <SetupFlow />
{/if}
</div>

<style>
  /* ── Base & Elements ────────────────────────────────── */
  :global(*) {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  :global(html) {
    background: var(--bg);
    --zoom: 1;
    zoom: var(--zoom);
    overflow: hidden;
  }

  @font-face {
    font-family: 'Fira Sans';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/FiraSans-Regular.woff2') format('woff2');
  }

  @font-face {
    font-family: 'Fira Sans';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url('/fonts/FiraSans-Medium.woff2') format('woff2');
  }

  @font-face {
    font-family: 'Fira Sans';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('/fonts/FiraSans-Bold.woff2') format('woff2');
  }

  @font-face {
    font-family: 'Fira Mono';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/FiraMono-Regular.woff2') format('woff2');
  }

  @font-face {
    font-family: 'Fira Mono';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url('/fonts/FiraMono-Medium.woff2') format('woff2');
  }

  /* ── Design Tokens ──────────────────────────────────── */
  :global(:root) {
    --bg: #0f0f12;
    --bg-surface: #1a1a1f;
    --bg-raised: #22222a;
    --bg-hover: #22222a;
    --accent: #00e6e6;
    --accent-dim: #009999;
    --accent-glow: rgba(0, 230, 230, 0.35);
    --accent-secondary: #2ecc71;
    --text: #e8e8ec;
    --text-dim: #9a9aa5;
    --text-muted: #6e6e7a;
    --border: #2e2e36;
    --border-dim: #25252d;
    --red: #ff4444;
    --red-dim: #cc3333;
    --yellow: #ffd040;
    --green: #40ff80;
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --shadow-floating: 0 4px 16px rgba(0,0,0,0.4);
    --shadow-glow: 0 0 12px rgba(0, 230, 230, 0.1);
    --overlay-dim: 0.75;
    --font-ui: "Fira Sans", system-ui, sans-serif;
    --font-mono: "Fira Mono", "Consolas", "Cascadia Code", "Courier New", monospace;
    font-family: var(--font-ui);
    font-size: 13.5px;
    color: var(--text);
    background: var(--bg);
  }

  :global(body) {
    background: var(--bg);
    overflow: hidden;
    user-select: none;
  }

  :global(input), :global(textarea), :global([contenteditable='true']) {
    user-select: text;
    -webkit-user-select: text;
  }

  /* ── Custom slim scrollbar ──────────────────────────── */

  /* Keep `scrollbar-color`/`scrollbar-width` unset app-wide, or Chromium
     switches to the unstylable standard scrollbar model. */
  /* Pre-promote scroll containers to their own compositor layers so the first
     scroll after launch doesn't stall on layer creation (WebView2 warm-up). */
  :global([data-scrollable]) {
    will-change: scroll-position;
    overflow-anchor: none;
    scrollbar-gutter: stable;
  }

  :global(*)::-webkit-scrollbar {
    width: 2px;
    height: 2px;
  }
  :global(*)::-webkit-scrollbar-track {
    background: transparent;
  }
  :global(*)::-webkit-scrollbar-thumb {
    background: var(--accent);
    border-radius: 1px;
  }
  :global(*)::-webkit-scrollbar-corner {
    background: transparent;
  }

  /* ── Widgets ────────────────────────────────────────── */
  /* Settings widget tables: columns sized by content (widest label/control),
     shrink-wrapped, capped at panel width so high zoom squeezes the control
     column instead of overflowing. Labels (nowrap) never compress. */
  :global(.widget-list) {
    display: table;
    width: auto;
    max-width: 100%;
    border-collapse: collapse;
    align-self: flex-start;
  }

  :global(.widget-list .combo) {
    width: fit-content;
    max-width: 100%;
  }

  /* ── Shared Utilities ───────────────────────────────── */
  /* Look-only rules shared across components (markup/handlers stay local). */

  :global(.btn-primary) {
    background: var(--bg-surface);
    font-weight: 600;
  }

  :global(.btn-primary:hover:not(:disabled)) {
    background: rgba(0, 230, 230, 0.06);
    color: var(--accent);
    border-color: var(--accent);
  }

  :global(.btn-ghost) {
    background: transparent;
    border-color: transparent;
    color: var(--text-dim);
  }

  :global(.section-header) {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    border-bottom: 1px solid var(--border);
    padding-bottom: 4px;
  }

  :global(.variant-dot.active) {
    box-shadow: 0 0 0 2px var(--accent), 0 0 8px var(--accent-glow);
  }

  :global(button) {
    cursor: pointer;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-dim);
    border-radius: var(--radius-sm);
    padding: 4px 12px;
    font-size: 12px;
    font-family: inherit;
    letter-spacing: 0.3px;
    transition:
      color 0.12s,
      border-color 0.12s,
      background 0.12s;
  }

  :global(button:hover:not(:disabled)) {
    color: var(--accent);
    border-color: var(--accent);
  }

  :global(button:active:not(:disabled)) {
    transform: scale(0.97);
  }

  :global(button:focus-visible) {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
    box-shadow: none;
  }

  :global(button:disabled) {
    opacity: 0.3;
    cursor: not-allowed;
  }

  :global(select, input[type="text"], input[type="number"]) {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    color: var(--text);
    border-radius: var(--radius-sm);
    padding: 4px 8px;
    font-size: 12px;
    font-family: inherit;
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  :global(select:focus, input:focus) {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
    box-shadow: none;
    border-color: var(--accent-dim);
  }

  :global(a:focus-visible) {
    outline: 2px solid var(--accent);
    outline-offset: -2px;
  }

  :global(input[type="checkbox"]) {
    accent-color: var(--accent);
  }

  .stage {
    position: relative;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
  }

  .app {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: calc(100vh / var(--zoom));
    width: calc(100vw / var(--zoom));
    min-width: 0;
    padding: 0 16px 4px 16px;
    gap: 4px;
    overflow: hidden;
    position: relative;
  }

  .app-header {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    overflow: hidden;
    padding-top: 2px;
  }

  .header-spacer {
    flex: 1;
  }

  .tab-btn {
    padding: 0 12px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    font-family: inherit;
    min-width: 0;
    flex-shrink: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    transition: color 0.12s, border-color 0.12s, background 0.12s, box-shadow 0.12s;
  }

  .tab-btn:hover:not(.active) {
    background: var(--bg-hover);
    color: var(--text);
    border-color: var(--accent);
  }

  .tab-btn.active {
    background: rgba(0, 230, 230, 0.06);
    color: var(--accent);
    border-color: var(--accent);
    text-shadow: 0 0 4px rgba(0, 230, 230, 0.18);
    box-shadow: var(--shadow-glow);
  }

  .app-main {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
  }

  .status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    min-width: 0;
    padding: 2px 3px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font-size: 10px;
    font-family: var(--font-ui);
    color: var(--text-dim);
    overflow: hidden;
    white-space: nowrap;
  }

  .status-item {
    white-space: nowrap;
    color: var(--text-muted);
    font-size: 10.5px;
    font-weight: 400;
    flex-shrink: 0;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-item.mod-count,
  .status-item.version {
    font-size: 12px;
  }

  .status-sep {
    display: inline-block;
    width: 3px;
    height: 3px;
    border-radius: 50%;
    background: var(--border-dim);
    flex-shrink: 0;
  }

  .social-row {
    display: flex;
    gap: 4px;
  }

  .social-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 28px;
    padding: 2px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    line-height: 1;
    position: relative;
    overflow: hidden;
    flex-shrink: 0;
  }
  .social-btn::after {
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
  }
  .social-row .social-btn:nth-child(1)::after { animation: shimmer 5s ease-in-out 0s infinite; }
  .social-row .social-btn:nth-child(2)::after { animation: shimmer 5s ease-in-out 0.6s infinite; }
  .social-row .social-btn:nth-child(3)::after { animation: shimmer 5s ease-in-out 1.2s infinite; }

  .social-btn:hover,
  .social-btn.active {
    color: var(--accent);
  }

  .help-btn {
    width: 24px;
    font-weight: 700;
    font-size: 11px;
  }

  .refresh-btn {
    width: 26px;
    height: 26px;
    position: relative;
    overflow: hidden;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    cursor: pointer;
    font-size: 16px;
    line-height: 1;
    padding: 0;
    margin: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.3s, border-color 0.3s, background 0.3s;
  }

  .refresh-btn:hover {
    background: var(--bg-hover);
    color: var(--accent);
    border-color: var(--accent);
  }

  .refresh-btn.refreshing {
    color: var(--accent);
    border-color: var(--accent);
    cursor: wait;
  }

  .refresh-shimmer {
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
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s ease, transform 0.3s ease;
  }

  .refresh-btn.refreshing .refresh-shimmer {
    opacity: 1;
    animation: refreshShimmer 1.1s linear infinite;
  }

  @keyframes refreshShimmer {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }

  /* ── Search overlay ──────────────────────────────────── */

  .search-overlay {
    position: absolute;
    inset: 0;
    z-index: 70;
    display: flex;
    justify-content: center;
    padding: 16px;
    align-items: flex-start;
    pointer-events: none;
  }

  .search-bar {
    display: flex;
    align-items: center;
    gap: 4px;
    background: var(--bg-surface);
    border: 1px solid var(--accent-dim);
    padding: 4px 4px 4px 10px;
    min-width: 320px;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-floating);
    pointer-events: auto;
  }

  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text);
    font-size: 13px;
    font-family: inherit;
    outline: none;
    box-shadow: none;
  }

  .search-input:focus {
    outline: 1px solid var(--border);
    outline-offset: -1px;
  }

  .search-close {
    font-size: 12px;
    padding: 2px 7px;
    color: var(--text-dim);
    border-color: transparent;
    flex-shrink: 0;
  }

  .search-close:hover { color: var(--red); border-color: var(--red); }

  .search-close:focus-visible,
  :global(html.keyboard-focus) .search-close:focus {
    color: var(--red);
    border-color: var(--red);
    outline: 2px solid var(--red);
    outline-offset: -2px;
  }

  /* ── Shortcuts popover ───────────────────────────────── */

  .shortcuts-popover {
    position: fixed;
    top: 0;
    left: 0;
    width: calc(100vw / var(--zoom));
    height: calc(100vh / var(--zoom));
    z-index: 260;
  }

  .shortcuts-box {
    position: absolute;
    bottom: 36px;
    right: 8px;
    background: var(--bg-raised);
    border: 1px solid var(--border);
    padding: 12px 16px;
    min-width: 300px;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-floating);
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px 20px;
  }

  .shortcuts-box h3 {
    grid-column: 1 / -1;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent);
    margin-bottom: 4px;
  }

  .shortcut-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 11.5px;
    color: var(--text);
  }

  .shortcut-row kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 52px;
    height: 20px;
    padding: 2px 5px 0 5px;
    font-size: 10px;
    font-weight: 600;
    font-family: inherit;
    color: var(--accent);
    border: 1px solid var(--accent-dim);
    background: rgba(0, 230, 230, 0.06);
    line-height: 1;
    border-radius: var(--radius-sm);
  }

  .shortcut-row span {
    color: var(--text-dim);
  }

  @keyframes shimmer {
    0%   { transform: translateX(-100%); }
    40%  { transform: translateX(100%); }
    100% { transform: translateX(100%); }
  }
</style>
