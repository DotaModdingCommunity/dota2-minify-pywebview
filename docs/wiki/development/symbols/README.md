# Minify API Symbols Index

> [!NOTE]
> Module-level variables and constants are only dumped for [core.base](/development/symbols/core.base) and [core.constants](/development/symbols/core.constants). Other modules only contain functions and classes to keep the documentation focused.

- [cli](/development/symbols/cli)
- [conditions](/development/symbols/conditions) - Checks for various things
- [helper](/development/symbols/helper) - Dangling random functions
- [core.base](/development/symbols/core.base) - Variables that almost never change
- [core.config](/development/symbols/core.config) - JSON(C) config files
- [core.constants](/development/symbols/core.constants) - Variables that depend on 3rd parties
- [core.fs](/development/symbols/core.fs) - Filesystem access
- [core.log](/development/symbols/core.log) - Crashlogs, warnings and debug zip creation
- [core.migrations](/development/symbols/core.migrations)
- [core.mods_shared](/development/symbols/core.mods_shared) - Shared mod scanning logic
- [core.net](/development/symbols/core.net) - Network request helpers with offline simulation support
- [core.output](/development/symbols/core.output) - Agnostic output interface
- [core.steam](/development/symbols/core.steam) - Module to find steam root and library that Dota2 is in (always accounts the Windows' executable path to find if used through an emulation layer).
- [core.utils](/development/symbols/core.utils)
- [ui.actions](/development/symbols/ui.actions) - All JS-facing application logic.
- [ui.announcements](/development/symbols/ui.announcements) - Unix timestamp based announcement system internals
- [ui.dialogs](/development/symbols/ui.dialogs) - Native file dialog helpers for mod scripts and internal use.
- [ui.fonts](/development/symbols/ui.fonts)
- [ui.localization](/development/symbols/ui.localization) - Dynamic localization handling
- [ui.modal_shared](/development/symbols/ui.modal_shared) - Unified modal internals.
- [ui.modals](/development/symbols/ui.modals) - Modal types
- [ui.output_bridge](/development/symbols/ui.output_bridge) - Bridge between core/output.py and the pywebview window.
- [ui.web_window](/development/symbols/ui.web_window) - pywebview window launcher (replaces DearPyGui window).
