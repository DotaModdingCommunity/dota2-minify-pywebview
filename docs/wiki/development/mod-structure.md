## Mod files and explanations

```plaintext
mods
├── <mod_name>
│   ├── files
│   │   ├── <path_to_file_in_pak>
│   │   ├── <...>
│   │   └── <...>
│   ├── files_uncompiled
│   │   ├── <path_to_file_in_pak>
│   │   ├── <...>
│   │   └── <...>
│   ├── manifest.json
│   ├── notes.md
│   ├── preview.png
│   ├── blacklist.txt
│   ├── replacer.json
│   ├── script.py
│   ├── script_setup.py
│   ├── script_initial.py
│   ├── script_after_decompile.py
│   ├── script_after_recompile.py
│   ├── script_after_patch.py
│   ├── script_prelaunch.py
│   ├── script_uninstall.py
│   ├── script_utility.py
│   ├── styling.css
│   └── xml.json
```

> [!TIP]
> `docs/#Example Mod` is a fully commented showcase mod covering every file
> and feature listed here. It's kept out of the shipped releases, so use it as a
> reference when writing your own mod.

### `manifest.json`

```json
{ // defaults doesn't need to be indicated
  "always": false, // false by default, apply them without checking mods.json or checkbox
  "dependencies": ["<mod>"], // None by default, add a mod dependency's name here
  "conflicts": ["<mod>"], // None by default, add names of mutually exclusive mods here
  "order": 1, // default is 1, ordered from negative to positive to resolve any conflicts
  "visual": true, // true by default, show it in the UI as a checkbox
  "version": ">=1.13,<=1.14", // optional, enforces a Minify version requirement (supports operators: >=, <=, >, <, ==)
  "skip_workshop_check": false, // false by default, keeps the mod enabled even without Workshop Tools (see below)
  "styling_mode": "source", // "direct" (default), "source", or "disabled" — see ui-modding.md

  // preview_file: optional base name (no extension) of a user-supplied config file to preview.
  //               Minify looks for `<config>/<preview_file>.<ext>` (png/jpg/webp/mp4/webm) and shows
  //               it (image or video) at the top of the mod's settings/setup panel. The file itself is
  //               placed there by a `script_utility.py` button (e.g. Custom Backgrounds).
  "preview_file": "background",

  // presets system for custom mod settings
  "presets": [
    {
      "name": "Example Preset",
      "description": "Optional one-liner shown under the preset dropdown when selected.",
      "values": {
        "example_inputbox": "preset_value",
        "example_checkbox": true
      }
    }
  ],

  // dynamically injects settings into the global Settings Menu
  "settings": [
    // key*: the internal name
    // type*: inputbox, checkbox, combo, number, slider, color, list, button, file
    // text: string that gets displayed on the left of the input. falls back to key if not given
    // default: the default value to reset back to and start with. falls back to falsy values
    // description: optional help text shown as a tooltip on the "?" icon next to the setting
    // section: optional group name; settings sharing a section are rendered under a sub-header
    //          in the settings panel (groups are ordered by first appearance).
    // advanced: true hides the setting behind an "Advanced" toggle in the settings panel
    //           (defaults to false). Mirrors the global settings' Advanced section.
    // depends_on: key of an earlier checkbox setting. When that checkbox is off, this
    //             setting is greyed out and disabled in the UI. Skip for always-available settings.
    // when: richer alternative to depends_on. `{"key": "some_combo", "value": "A"}` disables the
    //       setting unless `some_combo` equals "A". Omit `value` to require any truthy value.
    // file_types: only for type "file" — the file-dialog filter, e.g. "Fonts (*.ttf;*.otf)". The chosen
    //             path is stored as the setting's value. Pair with a "button" setting to act on it
    //             (see Custom Fonts).
    {
      "key": "example_inputbox",
      "text": "Display Name",
      "force": false, // false by default, always show setting regardless of mod state
      "default": "example_value",
      "type": "inputbox",
    },
    {
      "key": "example_checkbox",
      "text": "Enable Feature",
      "force": false,
      "default": false,
      "type": "checkbox"
    },
    {
      "key": "example_combo",
      "text": "Select Option",
      "force": false,
      "default": "Value 1",
      "type": "combo",
      "items": ["Value 1", "Value 2"]
    },
    {
      "key": "example_number",
      "text": "Number",
      "force": false,
      "default": 10,
      "type": "number",
      "var_type": "int", // or "float"
      "min": 0, // optional, defaults to 0
      "max": 100, // optional
      "step": 1 // default is 1 for ints, 0.1 for floats
    },
    {
      "key": "example_slider",
      "text": "Slider",
      "force": false,
      "default": 50,
      "type": "slider",
      "min": 0,
      "max": 100,
      "step": 5, // default is 1 for ints, 0.1 for floats
      "section": "Appearance",
      "depends_on": "example_checkbox" // slider greys out while example_checkbox is off
    },
    {
      "key": "example_color",
      "text": "Color",
      "force": false,
      "default": "#ff0000",
      "type": "color", // color picker with hex input, use a 6-digit hex default (#rrggbb)
      "section": "Appearance",
      "depends_on": "example_checkbox",
      "description": "Choose the accent color used by the mod."
    },
    {
      "key": "example_list",
      "text": "List",
      "force": false,
      "default": ["Item 1", "Item 2"],
      "type": "list",
      "items": ["Item 1", "Item 2", "Item 3"], // optional, one-click suggestion chips
      "constrain": false // true restricts entries to the items above (rejects anything else)
    },
    {
      "key": "example_function", // binds the function named "example_function" from script_utility.py
      "text": "Function",
      "force": false,
      "type": "button"
    },
    {
      "key": "example_file", // file picker, path saved as the setting value
      "text": "Font File",
      "force": false,
      "default": "",
      "type": "file",
      "file_types": "Fonts (*.ttf;*.otf)"
    }
  ]
}
```

The `version` requirement uses the manifest's `version` field and is checked against
Minify's own version.

The `presets` array offers one-click combinations of setting values. When a mod declares presets, a "Preset:" combo appears at the top of its settings in the Mod Settings panel and in the patch-time Setup Flow. Picking a preset resets every setting to its schema default, then applies the preset's `values` (keys not in the `settings` array are ignored). Nothing is persisted until you hit Save (or Finish / Save for later in the Setup Flow), and the combo shows the applied preset's name — editing any setting manually switches it back to "Custom". If settings were already modified before picking a preset, Minify asks for confirmation before resetting. An optional `description` on a preset is shown under the dropdown while it is selected. While a preset is active, the per-setting reset (↺) reverts to that preset's value for the setting (or its default when the preset doesn't touch it).

`skip_workshop_check: true` is meant for mods that keep functioning without the Dota 2
Workshop Tools. Normally, a mod that ships any of `styling.css`, `xml.json`, or
`files_uncompiled` is greyed out (and disabled on patch) when Workshop Tools are missing;
setting this flag skips that check. This does **not** give you compilation — the actual
compile steps still require the tools.
### `files` and `files_uncompiled` directories

`files` drops whatever you put here straight into the pak Minify builds, so these files should already be compiled.

`files_uncompiled` drops the files onto the compile input folder instead — **if the Workshop Tools are available**. Without them, files here are skipped (unless `skip_workshop_check` is set, which then still skips compilation).

If not specifically protected by Dota2, these files will override any game content. This also applies for the rest of the modification methods available.

### Script hooks

Each `script*.py` defines a top-level `main()` that Minify executes at a specific point in the patch lifecycle. Importing Minify packages works once you add the Minify root to `sys.path` (see [`scripting.md`](scripting.md) for the full template).

| File                          | When it runs                                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| `script_setup.py`             | Once, on the patch after the mod's config file is missing (the setup phase). Return a `str` to prompt the user to configure the mod. |
| `script.py`                   | Every patch, while iterating over the mod (the main hook).                                      |
| `script_initial.py`           | Once, when the app starts up.                                                              |
| `script_after_decompile.py`   | Once, after the game pak has been decompiled.                                                  |
| `script_after_recompile.py`   | Once, after all assets have been compiled.                                                     |
| `script_after_patch.py`       | Once, after the patch finishes.                                                                |
| `script_prelaunch.py`         | Once, right before the game is launched.                                                       |
| `script_uninstall.py`         | During uninstall, for cleanup.                                                                 |
| `script_utility.py`           | Not a lifecycle hook — exposes functions callable from the UI via `"type": "button"` settings (the button's `key` is the function name). |

### `notes.md`

Displays information about a mod on `Details` window.

An image is rendered at the top if the file `preview.jpg` (or `preview.png`) exists.

```markdown
<!-- LANG:EN -->
Normal text supports `inline code` (pink) and https://example.com (orange).

- This is a list item.
- List items support `inline code` too.
- And they support https://example.com as well.

!!: This is an emphasized warning (Red & Large).
!!: It supports `pink code` blocks.
!!: And https://example.com links.
```

![notes](https://github.com/Egezenn/dota2-minify/raw/main/docs/assets/example-notes.jpg)

### `blacklist.txt`

This file is a list of path to files used to override those with blanks.
Supported file types can be found in [`bin/blank-files`](https://github.com/Egezenn/dota2-minify/tree/main/Minify/bin/blank-files).

A list of all the files (from the game pak) can be found in `bin/gamepakcontents.txt` of your installation.

| Modifier | Value               | Purpose                          |
| -------- | ------------------- | -------------------------------- |
|          | `path/to/file`      | Blacklisting a single file       |
| `>>`     | `path/to/directory` | Blacklisting an entire directory |
| `--`     | `path/to/file`      | Exclusion                        |
| `**`     | RegExp pattern      | Blacklisting patterns            |
| `*-`     | RegExp pattern      | Excluding patterns               |
| `#`      | Comment             |                                  |

After that with no blank spaces you put the path to the file you want to override.
`path/to/file`

```plaintext
particles/base_attacks/ranged_goodguy_launch.vpcf_c
>>particles/sprays
**taunt.*\.vsnd_c
```

### Settings-gated blacklist blocks

Like `styling.css`, `blacklist.txt` can be split into blocks that are only applied when a mod setting is enabled. Start a block with a `# @key:<setting_key>` comment; the block is skipped when that setting is `false`. Blocks without a `@key` marker (and settings that are missing or default to `true`) are always applied.

```plaintext
# @key:mute_ambient
sounds/ambient/soundscapes/bats01.vsnd_c

# @key:mute_announcer
>>sounds/vo/announcer
```

### `xml.json`

Modifies Valve's Panorama XML layout files dynamically with a selector/action list. See [`ui-modding.md`](ui-modding.md#xmljson) for the full reference.

### `replacer.json`

This file allows you to replace file(s) with other file(s) inside the game VPK (can be used for skin swappers etc.).

Format: a JSON object mapping `"target"` → `"source"`. The `source` file is extracted from the game pak and copied over the `target` path in the output.

Example:

```json
{
  "panorama/images/spellicons/nevermore_shadowraze1_png.vtex_c": "panorama/images/spellicons/nevermore_shadowraze1_demon_png.vtex_c",
  "panorama/images/spellicons/nevermore_shadowraze2_png.vtex_c": "panorama/images/spellicons/nevermore_shadowraze2_demon_png.vtex_c"
}
```

![example-replacer](https://github.com/Egezenn/dota2-minify/raw/main/docs/assets/example-replacer.jpg)
