import os
import shutil

import helper
import vpk
from core import base, fs, log, mods_shared, output
from patch import manifest_utils, vpk_utils

RENAME_CATEGORIES = ["trees", "river", "shaders", "herofx", "ranged-attack", "hero-items", "optimization"]


def _set_progress(pct: float, status: str) -> None:
    try:
        from ui import modal_shared

        modal_shared.set_progress(82 + pct * 10, status)
    except Exception:
        pass


def run(mod_list: list[str], current_mod: str | None = None) -> None:
    # Shared storage for identified mods
    pfx_high_priority = {}  # mod_name: [vpk_paths]
    pfx_normal = {}  # mod_name: [vpk_paths]
    map_vpk_paths = []

    # List of all active VPK-based mods (for pak65 metadata)
    # Contract: append VPK mod names here when they are identified as active.
    # Currently populated by: .vpk mods via line 43, normal-priority D2PFX via line 75.
    # High-priority D2PFX mods (pak67) intentionally excluded — they write their own metadata.
    all_active_vpk_mods = []

    for mod_name in mod_list:
        # Check if mod is active
        if current_mod is not None:
            if mod_name != current_mod:
                continue
        elif not mods_shared.get_state(mod_name):
            continue

        mod_path = os.path.join(base.mods_dir, mod_name)

        # 1. Identify Standard VPK mods (for pak65 metadata reconstruction)
        if mod_name.endswith(".vpk"):
            all_active_vpk_mods.append(mod_name)
            continue

        if not os.path.isdir(mod_path):
            continue

        # 2. Identify D2PFX mods via manifest/modcfg
        cfg = manifest_utils.get_mod(mod_path)
        if not cfg:
            continue

        browser_info = cfg.get("browser", {})

        is_d2pfx = browser_info.get("browser") == "d2pfx"

        if not is_d2pfx:
            continue

        # It's a D2PFX mod - find all VPKs once
        vpk_files = []
        for root, _, files in os.walk(mod_path):
            for f in files:
                if f.endswith(".vpk"):
                    vpk_files.append(os.path.join(root, f))

        if not vpk_files:
            continue

        cat = browser_info.get("category")
        if cat == "terrains":
            map_vpk_paths.extend(vpk_files)
        elif cat in RENAME_CATEGORIES:
            pfx_high_priority[mod_name] = vpk_files
        else:
            pfx_normal[mod_name] = vpk_files
            all_active_vpk_mods.append(mod_name)

    # --- BUILD EXECUTION ---

    _set_progress(0, "&status_processing_d2pfx")

    # 1. Maps (dota.vpk)
    if map_vpk_paths:
        if len(map_vpk_paths) > 1:
            log.write_warning(
                f"Multiple terrain mods detected ({len(map_vpk_paths)}). Only the last terrain mod will be applied."
            )
        output.add_section("&merging_vpks")
        maps_output_dir = os.path.join(helper.get_output_path(), "maps")
        fs.create_dirs(maps_output_dir)
        # Just copy the last found map VPK
        shutil.copy2(map_vpk_paths[-1], os.path.join(maps_output_dir, "dota.vpk"))
        output.add_text("&created_vpk_terminal", "maps/dota.vpk", msg_type="success")
    else:
        dota_vpk_path = os.path.join(helper.get_output_path(), "maps", "dota.vpk")
        if os.path.exists(dota_vpk_path):
            fs.remove_path(dota_vpk_path)

    _set_progress(0.15, "&status_merging_normal")

    # 2. Normal Priority (pak65)
    if pfx_normal:
        output.add_section("&merging_vpks")
        fs.remove_path(base.merge_dir)
        fs.create_dirs(base.merge_dir)

        pak65_path = os.path.join(helper.get_output_path(), "pak65_dir.vpk")
        # Extract existing pak65 (from build.py) to merge D2PFX on top
        if os.path.exists(pak65_path):
            try:
                vpk_utils.dump(vpk.open(pak65_path), base.merge_dir)
            except Exception:
                log.write_warning("Failed to extract existing pak65 — merging D2PFX mods only")

        for mod_name, vpk_paths in pfx_normal.items():
            for path in vpk_paths:
                try:
                    vpk_utils.dump(vpk.open(path), base.merge_dir)
                    output.add_detail("&merged_mod", mod_name)
                except Exception:
                    log.write_warning(f"Failed to merge mod: {mod_name}")

        vpk_utils.dump_metadata(base.merge_dir, vpk_mods=all_active_vpk_mods)
        vpk.new(base.merge_dir).save(pak65_path)
        output.add_text("&created_vpk_terminal", "pak65_dir.vpk", msg_type="success")
        fs.remove_path(base.merge_dir)

    _set_progress(0.6, "&status_merging_high")

    # 3. High Priority (pak67)
    if pfx_high_priority:
        output.add_section("&merging_vpks")
        fs.remove_path(base.merge_dir)
        fs.create_dirs(base.merge_dir)

        for mod_name, vpk_paths in pfx_high_priority.items():
            for path in vpk_paths:
                try:
                    vpk_utils.dump(vpk.open(path), base.merge_dir)
                    output.add_detail("&merged_mod", mod_name)
                except Exception:
                    log.write_warning(f"Failed to merge mod: {mod_name}")

        vpk_utils.dump_metadata(base.merge_dir)
        with open(os.path.join(base.merge_dir, "minify_d2pfx_mods.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(pfx_high_priority))
        vpk.new(base.merge_dir).save(os.path.join(helper.get_output_path(), "pak67_dir.vpk"))
        output.add_text("&created_vpk_terminal", "pak67_dir.vpk", msg_type="success")
        fs.remove_path(base.merge_dir)
    else:
        pak67_path = os.path.join(helper.get_output_path(), "pak67_dir.vpk")
        if os.path.exists(pak67_path):
            fs.remove_path(pak67_path)
