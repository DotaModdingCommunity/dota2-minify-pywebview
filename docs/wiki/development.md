## Development Guide

Welcome to the `dota2-minify` development guide! We're excited to see what you'll build. This page will help you get your environment set up and introduce you to the core concepts of modding with Minify.

If you have any questions or just want to share your progress, join us on [Discord](https://discord.com/invite/9867CPv7cy), [Telegram](https://t.me/dota2minify), or [GitHub Discussions](https://github.com/Egezenn/dota2-minify/discussions)!

## Running from the source

Prerequisites are `git`, `python`, `uv` and Node.js (for the frontend). On non-Windows systems you'll also need `wine` to run the Workshop Tools executables (Linux/macOS), and on Linux the pywebview GTK backend packages (see the README).

```shell
git clone https://github.com/Egezenn/dota2-minify
cd dota2-minify
uv sync

# build the Svelte frontend once (required before launching the GUI)
cd Minify/ui/web
npm ci
npm run build
cd ../..

uv run python -m Minify
```

The CLI works the same way: `uv run python -m Minify patch --help`.

## Creating mods

Minify has a programmatical approach to most modifications to keep everything minimal and simple. If there isn't a method available for your needs, you can always upload your mod files in `mods/<mod_name>/files` to be directly included into the pak minify is going to create or include a python script to accomodate specific behavior.

| Modifications to file                                                   | Restart required for changes | Workshop requirement |
| ----------------------------------------------------------------------- | ---------------------------- | -------------------- |
| [`files`](development/mod-structure.md#files-and-files_uncompiled-directories) | No                           | No<sup>1</sup>       |
| [`manifest.json`](development/mod-structure.md#manifestjson)            | Yes<sup>2</sup>              | -                    |
| [`notes.md`](development/mod-structure.md#notesmd)                      | Yes                          | -                    |
| `preview.jpg` \| `preview.png`                                          | Yes                          | -                    |
| [`blacklist.txt`](development/mod-structure.md#blacklisttxt)            | No                           | No                   |
| [`replacer.json`](development/mod-structure.md#replacerjson)            | No                           | No                   |
| [`script.py`](development/scripting.md#scriptpy)                        | No<sup>3</sup>               | No                   |
| [`styling.css`](development/ui-modding.md#stylingcss)                   | No                           | Yes                  |
| [`xml.json`](development/ui-modding.md#xmljson)                         | No                           | Yes                  |

<sup>1</sup>: [Uncompiled files](development/mod-structure.md#files-and-files_uncompiled-directories).  
<sup>2</sup>: The build engine pulls `always` and `dependencies` dynamically each time a patch is started. However, keys that define the mod's presence or configuration in the UI (like `order`, `visual`, and `settings` structure) are only loaded during the initial scan; changing these requires clicking **Refresh** in the Settings menu or restarting the application to re-render the components.  
<sup>3</sup>: Initial scripts(`script_initial.py`).

### Mod files and explanations

For a detailed breakdown of modification types and how to use them, refer to the following sections:

- [Mod Structure](development/mod-structure.md)
- [Scripting](development/scripting.md)
- [UI Modding (Panorama)](development/ui-modding.md)

### Compilation

For instructions, refer to the [workflow](https://github.com/Egezenn/dota2-minify/blob/main/.github/workflows/release.yml).
