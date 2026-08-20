## Frontend (Svelte 5)

The GUI is a Svelte 5 app in `Minify/ui/web/`, built with Vite and loaded from `web/dist/` at runtime. The backend (pywebview + `ui/actions.py`) talks to it through a small JS API surface.

### Building

```shell
cd Minify/ui/web
npm ci
npm run build
```

The build output lands in `Minify/ui/web/dist/`, which `ui/web_window.py` loads when the app starts. Any change to the Svelte sources requires a rebuild before the GUI picks it up.

### Development mode

Instead of rebuilding for every tweak, point the app at Vite's dev server:

```shell
cd Minify/ui/web
npm run dev
```

Then launch the app from the repo root with the server URL:

```shell
# PowerShell / bash
$env:MINIFY_DEV_URL = "http://localhost:5173"
uv run python -m Minify
```

With `MINIFY_DEV_URL` set, `ui/web_window.py` loads that URL instead of `dist/index.html`, so you get hot reload while the backend keeps running normally. Running with the pywebview debug flag (`debug_env: true` in `config/minify_config.json`) also enables the browser devtools.

### How the JS API works

The frontend never calls Python directly. `ui/web_window.py` exposes a whitelist of handlers from `ui/actions.py` as a `pywebview` js_api object, and the frontend calls them through `src/lib/api.ts`. The whitelist lives in `web_window.py` — a handler only becomes callable from JS once it's listed there.

The backend pushes events the other way via `ui/output_bridge.py`:

- `window.__termPush(...)` / `window.__termSep()` / `window.__termClear()` — terminal output lines
- `window.__backendReady()` — backend finished initializing
- `window.__dropComplete(...)` / `window.__hideDropOverlay()` — drag-and-drop lifecycle

### Drag-and-drop

Dropping a mod folder, `.zip` or `.vpk` onto the window installs it into `mods/`. Unsupported archive formats (`.7z`, `.rar`, `.tar`, `.tgz`) are rejected with a hint to extract first. The drop paths come from pywebview's cross-platform `pywebviewFullPath` mechanism, so it works on all supported backends (WebView2, GTK, cocoa).