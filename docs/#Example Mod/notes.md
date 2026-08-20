<!-- LANG:EN -->

A complete showcase mod demonstrating every feature of the Minify modding system. Read it top to bottom as a template when writing your own mod. Full reference: `docs/wiki/development/mod-structure.md` and `docs/wiki/development/ui-modding.md`.

## What this mod demonstrates

* Every manifest input type — `inputbox`, `checkbox`, `combo`, `number` (`int`/`float`), `slider`, `color`, `list`, `file`, `button` — plus `depends_on`, `presets`, `dependencies`, `conflicts`, `order`, `version`, `visual`, `preview_file`, `skip_workshop_check` and `styling_mode`.
* `styling.css` with `@key` gating, `<&placeholder>` substitution and `@define` (visible on the main-menu credits screen, alongside `#base`).
* `xml.json` with all seven layout actions (`add_script`, `add_style_include`, `set_attribute`, `add_child`, `move_into`, `insert_after`, `insert_before`).
* `blacklist.txt` with every pattern type, gated off by default so it is safe to experiment with.
* `replacer.json` (file-to-file replacement) and every script hook (`script.py`, `script_setup.py`, `script_initial.py`, `script_after_decompile.py`, `script_after_recompile.py`, `script_after_patch.py`, `script_prelaunch.py`, `script_uninstall.py`, `script_utility.py`).

## Files

| File | Purpose |
| --- | --- |
| `manifest.json` | metadata + settings schema (JSONC — comments allowed) |
| `styling.css` | styling with `@key` / `<&>` / `@define` |
| `xml.json` | layout modifications (7 actions) |
| `blacklist.txt` | file blanking (all gated off by default) |
| `replacer.json` | copy one game file over another |
| `script*.py` | lifecycle hooks |
| `files/` | copied into the game pak verbatim |
| `files_uncompiled/` | sources compiled at patch time (`.js` → `.vjs_c`, `.css` → `.vcss_c`) |
| `preview.png` | shown on the mods grid and details view |

## Notes

* The credits styling depends on `#base` (declared in `dependencies`).
* A `conflicts` entry against `User Styles` is included on purpose — remove it if you want both enabled.
* Replace the default blacklist targets before shipping a real mod; they are examples, not recommendations.