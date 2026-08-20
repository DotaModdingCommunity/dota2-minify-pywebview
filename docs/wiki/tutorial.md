## Installation

Minify is available for Windows, Linux and Mac<sup>1</sup>!

You can download the archives from the link below:

https://egezenn.github.io/dota2-minify

<sup>1</sup>: Only through [running from source](development.md).

## Running

Extract the contents of the `.zip` file you've downloaded to someplace you like. You can run the `Minify` executable afterwards.

> [!WARNING]
> On Linux you may have to run `chmod +x ./Minify` to grant execution permissions if nothing happens after running the executable.

Select the mods you'd like, the language you want to use and patch!

You can view information about a mod on their respective `Details` page. You can also look at them through [here](https://egezenn.github.io/dota2-minify/mods.html).

After the sound, Steam may restart while Minify is adjusting your Dota2 launch options. Then you're good to go!

> [!INFO]
> You may see some mods grayed out/untickable. For these, you need the [Workshop DLC](troubleshooting_faq.md?id=workshop-tools-dlc).

## Installing mods

You can find more mods, tooling and skins at our [website](https://egezenn.github.io/dota2-minify/community.html) or [Discord server](https://discord.com/invite/9867CPv7cy).

You can also install mods directly by **dragging and dropping** a mod folder, `.zip`, or `.vpk` file into the Minify window. (`.7z`, `.rar`, `.tar` and `.tgz` archives are not supported.)

## Settings & Dev Tools

The **Settings** panel (gear icon) holds per-mod settings and the global options (UI zoom, language, launch options). Mods that ship a `manifest.json` render their own settings here.

The **Dev Tools** panel (hammer icon) is mostly for bug reports and power users:

- **Create debug zip** — bundles your logs and configs into a single archive for bug reports.
- **File/path openers and compilation utilities** — quick access to the game files, logs, and asset compilation.

Advanced options there (like inspecting the JS runtime) are only visible when running from source with `debug_env` set to `true` in `config/minify_config.json`.
