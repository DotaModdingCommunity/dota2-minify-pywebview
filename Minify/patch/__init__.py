"The universe"

import os
import re
import shutil
import subprocess
import webbrowser
from concurrent.futures import ThreadPoolExecutor

import jsonc
import vpk

# isort: split

import conditions
import helper
from core import base, config, constants, fs, log, mods_shared, output, steam, utils

from patch import blacklist, manifest_utils, replacer, styling, vpk_utils, xml_utils

dota_version_changed = False


def _remove_staged_mod_files(mod_path: str, dest_root: str) -> None:
    if not mod_path or not os.path.exists(mod_path):
        return
    for item_name in os.listdir(mod_path):
        fs.remove_path(os.path.join(dest_root, item_name))


def patcher(mod: str | None = None, pakname: str | None = None) -> bool:
    """Run the patch. Returns True when the patch completed, False when it aborted early
    (e.g. Dota running, missing binaries, setup flow cancelled, conflicts detected)."""
    global dota_version_changed
    from ui import actions, localization, modal_shared, output_bridge

    with actions.interactive_lock():
        output.clean()

        if conditions.is_dota_running("&close_dota_terminal", "warning"):
            loc = localization.localization_dict
            if base.HEADLESS:
                output.add_text(
                    loc.get("close_dota_modal_msg", "Please close Dota 2 before patching."), msg_type="error"
                )
                return False
            modal_shared.show(
                title=loc.get("close_dota_modal_title", "Dota 2 is running"),
                messages=[loc.get("close_dota_modal_msg", "Please close Dota 2 before patching.")],
                buttons=["OK"],
            )
            return False

        if not conditions.check_binaries():
            conditions.resolve_dependencies(progress_callback=modal_shared.set_progress)
            if not conditions.check_binaries():
                output.add_text("&deps_dl_fail_msg1", msg_type="error")
                output.add_text("&deps_dl_fail_msg2", msg_type="error")
                if not base.HEADLESS:
                    modal_shared.show(
                        title="&deps_dl_fail_title",
                        messages=[
                            "&deps_dl_fail_msg1",
                            "&deps_dl_fail_msg2",
                            "&deps_dl_fail_msg3",
                            "&deps_dl_fail_msg4",
                        ],
                        buttons=["OK"],
                    )
                return False

        dota_pak_contents = None
        core_pak_contents = None

        try:
            # Wipe previous run's partial output up-front: extract/dump skip
            # existing files, so leftovers from a failed run would otherwise be
            # silently packed into the next pak.
            fs.remove_path(
                constants.minify_dota_compile_input_path,
                constants.minify_dota_compile_output_path,
                base.build_dir,
                base.replace_dir,
                base.merge_dir,
                if_exists=True,
            )

            fs.create_dirs(
                base.cache_dir,
                base.build_dir,
                base.replace_dir,
                base.merge_dir,
                constants.minify_dota_compile_input_path,
                constants.minify_dota_tools_required_path,
            )

            # Wipe logs up-front so D2PFX-sync warnings below are not destroyed
            for item in os.listdir(base.logs_dir):
                fs.remove_path(os.path.join(base.logs_dir, item))

            # ── Mod Setup Phase ────────────────────────────────────────────
            # Runs before the D2PFX downloads so the interactive setup prompt
            # is not delayed behind potentially long network downloads.
            setup_mod_list = list(constants.mods_with_order) if mod is None else [mod]
            setup_pending = []
            for folder in setup_mod_list:
                mod_path = os.path.join(base.mods_dir, folder)
                mod_cfg = manifest_utils.get_mod(mod_path)
                always = mod_cfg.get("always", False)
                if not (always or mods_shared.get_state(folder)):
                    continue

                # Check if per-mod config file exists
                config_file = os.path.join(base.config_dir, f"{folder} config.json")
                if os.path.exists(config_file):
                    continue

                # Custom check via script_setup.py
                setup_script = os.path.join(mod_path, "script_setup.py")
                if os.path.exists(setup_script):
                    try:
                        msg = helper.exec_script(setup_script, folder, "setup", terminal_output=False)
                        if msg:
                            setup_pending.append((folder, msg))
                    except Exception:
                        log.write_warning(f"Setup script failed for {folder}")
                # Mods exposing settings (manifest.json) but no setup script still
                # need a prompt so their settings get collected before first use.
                elif mod_cfg.get("settings"):
                    setup_pending.append((folder, "Configure this mod's settings."))

            if setup_pending:
                try:
                    result = modal_shared.show_setup_flow(setup_pending)
                    if result == "cancel":
                        return False
                except AssertionError:
                    # CLI mode — no GUI, fall back to logging
                    output.add_text("&setup_required_for", msg_type="warning")
                    for mod, msg in setup_pending:
                        note = f"  {mod}: {msg}" if msg else f"  {mod}"
                        output.add_detail(note)

            # Download enabled D2PFX mods before mod_list is captured
            # so they are included in the main patching loop
            if mod is None:
                d2pfx_modconf = config.get("modconf", {})
                pending_downloads = []
                for d2pfx_name, d2pfx_entry in d2pfx_modconf.items():
                    if isinstance(d2pfx_entry, dict):
                        if not d2pfx_entry.get("enabled", False):
                            continue
                        mod_url = d2pfx_entry.get("url", "")
                        is_zip = d2pfx_entry.get("is_zip", False)
                    elif not d2pfx_entry:
                        continue
                    else:
                        continue

                    if not mod_url:
                        continue

                    mod_path = os.path.join(base.mods_dir, utils.sanitize_win_path(d2pfx_name))
                    if os.path.isdir(mod_path):
                        continue
                    pending_downloads.append((d2pfx_name, mod_url, is_zip))

                if pending_downloads:
                    output.add_section("&starting_d2pfx")
                    modal_shared.set_progress(0, "&status_processing_d2pfx")

                downloaded_count = 0
                for i, (d2pfx_name, mod_url, is_zip) in enumerate(pending_downloads):
                    modal_shared.set_progress(i / len(pending_downloads), "&status_processing_d2pfx")
                    mod_path = os.path.join(base.mods_dir, utils.sanitize_win_path(d2pfx_name))
                    temp_dir = ""
                    try:
                        temp_dir = os.path.join(base.cache_dir, "d2pfx_dl", utils.sanitize_win_path(d2pfx_name))
                        fs.create_dirs(temp_dir)
                        mod_dest = os.path.join(temp_dir, os.path.basename(mod_url))
                        if fs.download_file(mod_url, mod_dest):
                            if is_zip:
                                if not fs.extract_archive(mod_dest, temp_dir):
                                    continue
                                fs.remove_path(mod_dest)

                            fs.create_dirs(mod_path)
                            for item_name in os.listdir(temp_dir):
                                src = os.path.join(temp_dir, item_name)
                                dst = os.path.join(mod_path, item_name)
                                if os.path.isdir(src):
                                    shutil.copytree(src, dst, dirs_exist_ok=True)
                                else:
                                    shutil.copy2(src, dst)
                            fs.remove_path(os.path.join(base.cache_dir, "d2pfx_dl"))

                            manifest_path = os.path.join(mod_path, "manifest.json")
                            if not os.path.exists(manifest_path):
                                config.write_json_file(
                                    manifest_path,
                                    {
                                        "browser": {"browser": "d2pfx", "name": d2pfx_name},
                                        "visual": True,
                                        "order": 2,
                                    },
                                )
                            output.add_detail("&d2pfx_mod_downloaded", d2pfx_name)
                            downloaded_count += 1
                    except Exception:
                        log.write_warning(f"Failed to download D2PFX mod: {d2pfx_name}")
                        fs.remove_path(temp_dir)
                        fs.remove_path(mod_path)

                if downloaded_count:
                    output.add_text("&d2pfx_downloaded_all", downloaded_count, msg_type="success")

                # Re-sync D2PFX states from modconf, in case config was overwritten
                mods_shared.set_state_batch(
                    {
                        name: entry["enabled"]
                        for name, entry in d2pfx_modconf.items()
                        if isinstance(entry, dict) and isinstance(entry.get("enabled"), bool)
                    }
                )

                mods_shared.scan_mods(force=True)

            mod_list = list(constants.mods_with_order) if mod is None else [mod]

            mods_shared.enforce_locale_mod_states()

            blank_file_extensions = helper.get_blank_file_extensions()  # list of extensions in bin/blank-files

            current_dota_version = ""
            if os.path.exists(constants.dota_steam_inf_path):
                with utils.open_utf8(constants.dota_steam_inf_path) as f:
                    current_dota_version = f.read()

            cached_dota_version = ""
            if os.path.exists(base.dota_steam_inf_cache):
                with utils.open_utf8(base.dota_steam_inf_cache) as f:
                    cached_dota_version = f.read()

            dota_version_changed = current_dota_version != cached_dota_version

            if dota_version_changed and current_dota_version:
                with utils.open_utf8(base.dota_steam_inf_cache, "w") as f:
                    f.write(current_dota_version)

            dota_pak_contents = vpk.open(constants.dota_game_pak_path)
            core_pak_contents = None
            dota_extracts = []
            core_extracts = []
            styling_dictionary = {}
            xml_modifications = {}
            replacer_source_extracts = []
            replacer_targets = []

            # Snapshot mod states once so dependency resolution is immune to toggles mid-patch
            mods_with_order_snapshot = list(mods_shared.mods_with_order)
            state_snapshot = {cb: mods_shared.get_state(cb) for cb in mods_with_order_snapshot}
            dependency_checkbox_states = [state_snapshot.get(cb, False) for cb in mods_with_order_snapshot]
            dependencies_resolved = False
            dependency_iterations = 0

            if mod is not None:
                dependencies_resolved = True  # skip dependency resolution for single-mod mode

            while not dependencies_resolved and dependency_iterations < 100:
                dependency_iterations += 1
                for dependency_dict in constants.mod_dependencies_list:
                    for dependant, dependencies in dependency_dict.items():
                        if state_snapshot.get(dependant, False):
                            dependency_list = dependencies if isinstance(dependencies, list) else [dependencies]
                            for dependency in dependency_list:
                                try:
                                    if not conditions.workshop_installed:
                                        workshop = False
                                        for method_path in conditions.workshop_required_methods:
                                            if os.path.exists(os.path.join(base.mods_dir, dependency, method_path)):
                                                workshop = True
                                                break
                                        state_snapshot[dependency] = not workshop
                                        if not workshop:
                                            log.write_warning(f"Auto-enabled dependency {dependency} for {dependant}")
                                    elif not state_snapshot.get(dependency, False):
                                        state_snapshot[dependency] = True
                                        log.write_warning(f"Auto-enabled dependency {dependency} for {dependant}")
                                except Exception:
                                    log.write_warning(
                                        f"Mod dependency {dependency} for {dependant} couldn't be resolved, might be that the mod doesn't exist."
                                    )
                new_states = [state_snapshot.get(cb, False) for cb in mods_with_order_snapshot]
                if dependency_checkbox_states == new_states:
                    dependencies_resolved = True
                dependency_checkbox_states = new_states

            # Apply resolved dependency states back to mods_shared
            mods_shared.set_state_batch(state_snapshot)

            conflicts_found = {}
            for conflict_dict in constants.mod_conflicts_list:
                for conflict_mod, conflicts in conflict_dict.items():
                    if conflict_mod in mod_list and mods_shared.get_state(conflict_mod):
                        active_conflicts = [c for c in conflicts if mods_shared.get_state(c)]
                        if active_conflicts:
                            conflicts_found[conflict_mod] = active_conflicts

            if conflicts_found:
                output.add_text("&conflicts_detected", msg_type="error")
                for conflict_mod, active_conflicts in conflicts_found.items():
                    output.add_text("&conflict_line", conflict_mod, ", ".join(active_conflicts), msg_type="error")
                return False

            modal_shared.set_progress(5, "&status_resolving_deps")
            game_contents_file_init = False
            processed = 0
            for folder in mod_list:
                mod_path = os.path.join(base.mods_dir, folder)
                mod_cfg = manifest_utils.get_mod(mod_path)

                if mod is None:
                    always = mod_cfg.get("always", False)
                else:
                    always = False

                # ---------------------------------- STEP 1 ---------------------------------- #
                # ---------------- Colect mod data and extract necessary files --------------- #
                # ---------------------------------------------------------------------------- #
                staged_sources = []
                try:
                    if mod is not None or always or mods_shared.get_state(folder):
                        blacklist_txt = os.path.join(mod_path, "blacklist.txt")
                        styling_css = os.path.join(mod_path, "styling.css")
                        xml_mod_file = xml_utils.get_xml_mod_file(mod_path)
                        files_uncompiled_dir = os.path.join(mod_path, "files_uncompiled")
                        if conditions.workshop_installed:
                            staged_sources.append((files_uncompiled_dir, constants.minify_dota_compile_input_path))
                        script_file = os.path.join(mod_path, "script.py")
                        replacer_file = os.path.join(mod_path, "replacer.json")
                        files_dir = os.path.join(mod_path, "files")
                        staged_sources.append((files_dir, constants.minify_dota_compile_output_path))

                        output.add_text("&installing_terminal", folder)
                        helper.exec_script(script_file, folder, "loop")
                        if conditions.workshop_installed:
                            if os.path.exists(files_uncompiled_dir):
                                shutil.copytree(
                                    files_uncompiled_dir,
                                    constants.minify_dota_compile_input_path,
                                    dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns("*.gitkeep"),
                                )
                        if os.path.exists(files_dir):
                            shutil.copytree(
                                files_dir,
                                constants.minify_dota_compile_output_path,
                                dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("*.gitkeep"),
                            )

                        if conditions.workshop_installed and xml_mod_file and os.path.exists(xml_mod_file):
                            with utils.open_utf8(xml_mod_file) as file:
                                mod_xml = jsonc.load(file)
                            for path, mods in mod_xml.items():
                                xml_modifications.setdefault(path, []).extend(mods)
                                compiled = path.replace(".xml", ".vxml_c")
                                dota_extracts.append(compiled)

                        if not game_contents_file_init:
                            gamepakcontents_path = os.path.join(base.bin_dir, "gamepakcontents.txt")
                            if dota_version_changed or not os.path.exists(gamepakcontents_path):
                                with utils.open_utf8(gamepakcontents_path, "w") as file:
                                    for filepath in dota_pak_contents:
                                        file.write(filepath + "\n")
                            game_contents_file_init = True

                        # ------------------------------- blacklist.txt ------------------------------ #
                        if os.path.exists(blacklist_txt):
                            blacklist.process(blacklist_txt, folder, blank_file_extensions)

                        # --------------------------------- styling.css --------------------------------- #
                        styling_mode = mod_cfg.get("styling_mode", "direct")
                        if styling_mode == "disabled":
                            pass
                        elif styling_mode == "source":
                            if conditions.workshop_installed:
                                if not os.path.exists(styling_css):
                                    log.write_warning(
                                        f"styling.css required for {folder} (styling_mode: source), but file is missing"
                                    )
                                else:
                                    with utils.open_utf8(styling_css) as f:
                                        source = f.read()
                                    settings = config.get_mod_config(folder)
                                    blocks = re.split(r"(?=/\*\s*@key:\w+\s*\*/)", source)
                                    enabled = []
                                    for block in blocks:
                                        m = re.search(r"@key:(\w+)", block)
                                        key = m.group(1) if m else None
                                        if key is None or settings.get(key, True):
                                            enabled.append(block)
                                    styling.parse_styling_content(
                                        "".join(enabled),
                                        mod_cfg,
                                        folder,
                                        settings,
                                        styling_dictionary,
                                        core_extracts,
                                        dota_extracts,
                                    )
                        elif conditions.workshop_installed and os.path.exists(styling_css):
                            styling.parse_styling_file(
                                styling_css,
                                mod_cfg,
                                folder,
                                config.get_mod_config(folder),
                                styling_dictionary,
                                core_extracts,
                                dota_extracts,
                            )

                        # replacer.json
                        replacer.process(replacer_file, folder, replacer_source_extracts, replacer_targets)

                except Exception:
                    log.write_warning(f"Mod {folder} failed in extraction loop")
                    for src_dir, dest_root in staged_sources:
                        _remove_staged_mod_files(src_dir, dest_root)

                processed += 1
                mod_progress = 5 + (processed / max(len(mod_list), 1)) * 10
                modal_shared.set_progress(round(mod_progress), "&status_processing_mods", processed, len(mod_list))

            modal_shared.set_progress(15, "&status_collecting_data")
            if conditions.workshop_installed:
                output.add_section("&starting_extraction")
                if core_extracts:
                    core_pak_contents = vpk.open(constants.dota_core_pak_path)
                    vpk_utils.extract(core_pak_contents, list(core_extracts), force=dota_version_changed)
                vpk_utils.extract(dota_pak_contents, list(dota_extracts), force=dota_version_changed)
                output.add_text("&extracted_terminal", len(set(dota_extracts) | set(core_extracts)), msg_type="success")
                modal_shared.set_progress(35, "&status_extracting")
                # ---------------------------------- STEP 2 ---------------------------------- #
                # ------------------- Decompile all files in "build" folder ------------------ #
                # ---------------------------------------------------------------------------- #
                output.add_section("&decompiling_terminal")

                # prevent gameinfo confusion
                dummy_gameinfo = os.path.join(base.build_dir, "gameinfo.gi")
                dota_gameinfo_path = os.path.join(
                    steam.LIBRARY, "steamapps", "common", "dota 2 beta", "game", "dota", "gameinfo.gi"
                )
                if os.path.exists(dota_gameinfo_path):
                    shutil.copy(dota_gameinfo_path, dummy_gameinfo)

                with open(base.log_s2v, "w", encoding="utf-8") as file:
                    try:
                        res = subprocess.run(
                            [
                                constants.s2v_exec_path,
                                "--input",
                                base.build_dir,
                                "--recursive",
                                "--vpk_decompile",
                                "--output",
                                base.build_dir,
                            ],
                            stdout=file,
                            stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NO_WINDOW if base.is_win else 0,
                            timeout=1200,
                        )
                    except subprocess.TimeoutExpired:
                        log.write_warning(f"Source2Viewer timed out after 20 minutes. See {base.log_s2v} for details.")
                        raise RuntimeError(f"Source2Viewer timed out after 20 minutes. See {base.log_s2v} for details.")
                    if res.returncode != 0:
                        log.write_warning(
                            f"Source2Viewer exited with code {res.returncode}. See {base.log_s2v} for details."
                        )
                        raise RuntimeError(
                            f"Source2Viewer exited with code {res.returncode}. See {base.log_s2v} for details."
                        )

                fs.remove_path(dummy_gameinfo)

                with ThreadPoolExecutor() as executor:
                    futures = []
                    for path, mods in xml_modifications.items():
                        fpath = os.path.join(base.build_dir, path)
                        futures.append(executor.submit(xml_utils.apply_modifications, fpath, mods))
                    first_exc = None
                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            if first_exc is None:
                                first_exc = e
                            log.write_warning("XML modification failed — continuing")
                    if first_exc:
                        raise first_exc
                helper.bulk_exec_script("after_decompile")
                modal_shared.set_progress(55, "&status_decompiling")
                # ---------------------------------- STEP 3 ---------------------------------- #
                # ---------------------------- CSS resourcecompile --------------------------- #
                # ---------------------------------------------------------------------------- #
                output.add_section("&compiling_resource_terminal")
                styles_by_file = {}
                for path, style in styling_dictionary.values():
                    sanitized_path = path[1:] if path.startswith("!") else path
                    css_file_path = os.path.join(base.build_dir, f"{sanitized_path}.css")
                    if css_file_path not in styles_by_file:
                        styles_by_file[css_file_path] = []
                    styles_by_file[css_file_path].append(style)

                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(styling.apply_styles_to_file, item) for item in styles_by_file.items()]
                    first_exc = None
                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            if first_exc is None:
                                first_exc = e
                            log.write_warning("Style application failed — continuing")
                    if first_exc:
                        raise first_exc

                shutil.copytree(
                    base.build_dir,
                    constants.minify_dota_compile_input_path,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("*.vcss_c", "*.vxml_c"),
                )

                helper.run_resource_compiler()
            helper.bulk_exec_script("after_recompile")

            if replacer_source_extracts:
                vpk_utils.extract(dota_pak_contents, replacer_source_extracts, base.replace_dir)
                with ThreadPoolExecutor() as executor:
                    futures = [executor.submit(replacer.process_replacer, t) for t in replacer_targets]
                    first_exc = None
                    for future in futures:
                        try:
                            future.result()
                        except Exception as e:
                            if first_exc is None:
                                first_exc = e
                            log.write_warning("Replacer failed — continuing")
                    if first_exc:
                        raise first_exc

            # Release VPK handles before cleanup to avoid Windows file-lock issues
            core_pak_contents = dota_pak_contents = None

            modal_shared.set_progress(65, "&status_compiling_resources")
            # ---------------------------------- STEP 4 ---------------------------------- #
            # -------- Create VPK from game folder and save into Minify directory -------- #
            # ---------------------------------------------------------------------------- #
            vpk_utils.dump_metadata(constants.minify_dota_compile_output_path, mod_name=mod)

            fs.create_dirs(helper.get_output_path())
            native_mods = vpk.new(constants.minify_dota_compile_output_path)
            output.add_section("&compiling_terminal")
            pakname = "pak66" if pakname is None else pakname
            native_mods.save(os.path.join(helper.get_output_path(), f"{pakname}_dir.vpk"))
            output.add_text("&created_vpk_terminal", f"{pakname}_dir.vpk", msg_type="success")
            modal_shared.set_progress(75, "&status_creating_vpk")

            # ---------------------------------- STEP 5 ---------------------------------- #
            # -------------------------- Merge VPKs into pak65 --------------------------- #
            # ---------------------------------------------------------------------------- #

            # Check if there are any VPK mods selected
            vpk_mods_to_merge = []
            for mod_name in mod_list:
                if mod_name.endswith(".vpk") and (mod is not None or mods_shared.get_state(mod_name)):
                    vpk_mods_to_merge.append(mod_name)

            # Only create pak65 if there are VPK mods to merge
            if vpk_mods_to_merge:
                output.add_section("&merging_vpks")

                successfully_merged = []
                for mod_name in vpk_mods_to_merge:
                    mod_path = os.path.join(base.mods_dir, mod_name)
                    mod_vpk = None
                    try:
                        mod_vpk = vpk.open(mod_path)
                        vpk_utils.dump(mod_vpk, base.merge_dir)
                        output.add_detail("&merged_mod", mod_name)
                        successfully_merged.append(mod_name)
                    except Exception:
                        log.write_warning(f"Failed to merge mod: {mod_name}")
                    finally:
                        if mod_vpk is not None:
                            del mod_vpk

                vpk_utils.dump_metadata(base.merge_dir, vpk_mods=successfully_merged)

                output.add_text("&creating_merged_vpk")
                merged_mods = vpk.new(base.merge_dir)
                merged_mods.save(os.path.join(helper.get_output_path(), "pak65_dir.vpk"))

                output.add_text("&success_merged_vpk", msg_type="success")
            else:
                # No VPK mods selected - remove pak65 if it exists from previous patches
                pak65_path = os.path.join(helper.get_output_path(), "pak65_dir.vpk")
                if os.path.exists(pak65_path):
                    fs.remove_path(pak65_path)

            modal_shared.set_progress(82, "&status_merging_mods")
            # ---------------------------------- STEP 6 ---------------------------------- #
            # --------------------------- Run Browser Hooks ------------------------------ #
            # ---------------------------------------------------------------------------- #
            try:
                from browsers.d2pfx.build_hook import run

                run(mod_list, mod)
            except ImportError:
                pass

            modal_shared.set_progress(92, "&status_finalizing")
            # ---------------------------------- STEP 7 ---------------------------------- #
            # -------------------------- Clean paths and inform -------------------------- #
            # ---------------------------------------------------------------------------- #

            modal_shared.set_progress(94, "&status_cleaning_up")
            fs.remove_path(
                constants.minify_dota_compile_input_path,
                constants.minify_dota_compile_output_path,
                base.build_dir,
                base.replace_dir,
                base.merge_dir,
                if_exists=True,
            )

            modal_shared.set_progress(98, "&status_running_scripts")
            helper.bulk_exec_script("after_patch", False)

            modal_shared.set_progress(100, "&status_done")
            output.add_separator()
            output.add_text("&success_terminal", msg_type="success")

            if steam.add_conditional_patch_to_launch_options():
                output.add_text("&added_conditional_patch_launch", msg_type="success")

            if steam.add_prelaunch_to_launch_options():
                output.add_text("&added_prelaunch_launch", msg_type="success")

            if os.path.exists(base.log_warnings) and os.path.getsize(base.log_warnings) != 0:
                output.add_text("&minify_encountered_errors_terminal", msg_type="warning")
            print("\a")  # ponytail: terminal bell replaces playsound3 dep

            if config.get("launch_dota_after_patch", False):
                if base.is_win or not steam.steam_executable_path or not os.path.exists(steam.steam_executable_path):
                    webbrowser.open(f"steam://rungameid/{base.STEAM_DOTA_ID}")
                else:
                    # POSIX: the steam:// URI handler may be unregistered on minimal WMs
                    subprocess.Popen(
                        [steam.steam_executable_path, "-applaunch", str(base.STEAM_DOTA_ID)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
            if config.get("kill_self_after_patch", False):
                output_bridge.close()

            return True

        except Exception:
            output.add_separator()
            output.add_text("&failure_terminal", msg_type="error")
            output.add_text("&check_logs_terminal", msg_type="warning")
            print("\a")
            raise
