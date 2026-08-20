import json
import os
import subprocess


# Keys that were part of the old DearPyGui UI and removed in the pywebview migration
_LEGACY_DPG_KEYS = {
    "button_patch",
    "button_select_mods",
    "button_uninstall",
    "clean_lang_dirs",
    "script_no_main",
    "details_button_label_var",
    "extraction_of_failed",
    "failed_steam_close",
    "language_select",
    "launch_option",
    "mod_selection_window_var",
    "refreshed_mod_list",
    "start_text_1_var",
    "start_text_2_var",
    "start_text_3_var",
    "start_text_4_var",
    "start_text_5_var",
    "waiting_steam_to_close",
    "downloaded_cli_terminal",
    "downloading_cli_terminal",
    "downloading_ripgrep_terminal",
    "extracted",
    "extracted_cli_terminal",
    "failed_download",
    "failed_download_retrying_terminal",
    "failed_merge",
}


def get_git_tracked_source_files(root_dir):
    # NOTE: uses `git ls-files` so it cannot see untracked files. The Svelte/TS frontend
    # (Minify/ui/web) is intentionally left untracked (AUDIT B0.5/E5 decision), so unused-key
    # detection stays blind to it until the frontend is committed.
    result = subprocess.run(["git", "ls-files", "Minify"], capture_output=True, text=True, check=True, cwd=root_dir)
    files = result.stdout.splitlines()
    source_files = [os.path.join(root_dir, f) for f in files if f.endswith((".py", ".svelte", ".ts"))]

    # The frontend i18n keys live in untracked Svelte/TS sources, so also scan them on disk
    web_src = os.path.join(root_dir, "Minify", "ui", "web", "src")
    for dirpath, _dirnames, filenames in os.walk(web_src):
        for name in filenames:
            if name.endswith((".svelte", ".ts")):
                source_files.append(os.path.join(dirpath, name))

    # Untracked Python modules (e.g. the in-progress pywebview UI backend) are also scanned on disk
    for dirpath, _dirnames, filenames in os.walk(os.path.join(root_dir, "Minify")):
        for name in filenames:
            if name.endswith(".py") and os.path.join(dirpath, name) not in source_files:
                source_files.append(os.path.join(dirpath, name))
    return source_files


def test_unused_localization_keys():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    loc_path = os.path.join(root_dir, "Minify", "bin", "localization.json")

    assert os.path.exists(loc_path), f"localization.json not found at {loc_path}"

    with open(loc_path, "r", encoding="utf-8") as f:
        loc_data = json.load(f)

    keys = list(loc_data.keys())
    source_files = get_git_tracked_source_files(root_dir)

    file_contents = {}
    for filepath in source_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                file_contents[filepath] = f.read()
        except Exception:
            try:
                with open(filepath, "r", encoding="latin-1") as f:
                    file_contents[filepath] = f.read()
            except Exception:
                pass

    unused_keys = []
    for key in keys:
        if key in _LEGACY_DPG_KEYS:
            continue
        is_used = False
        amp_key = f"&{key}"

        for content in file_contents.values():
            if amp_key in content:
                is_used = True
                break
            if f'"{key}"' in content or f"'{key}'" in content:
                is_used = True
                break
            if "start_text_" in key and "start_text_{i}_var" in content:
                is_used = True
                break

        if not is_used:
            unused_keys.append(key)

    assert len(unused_keys) == 0, f"Unused localization keys found: {unused_keys}"
