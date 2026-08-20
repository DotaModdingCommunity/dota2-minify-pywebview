import json
import os
import shutil

from core import base, constants, fs, log, output, utils


def process_replacer(item: tuple[str, str]) -> None:
    source, target = item
    output.add_detail("&replacing_terminal", source, target)
    dest_path = os.path.join(constants.minify_dota_compile_output_path, target)
    fs.create_dirs(os.path.dirname(dest_path))
    shutil.copy(os.path.join(base.replace_dir, source), dest_path)


def process(
    replacer_file: str,
    folder: str,
    replacer_source_extracts: list[str],
    replacer_targets: list[tuple[str, str]],
) -> None:
    if not os.path.exists(replacer_file):
        return

    try:
        with utils.open_utf8(replacer_file) as file:
            replacements = json.load(file)

        for target, source in replacements.items():
            if target and source:
                replacer_source_extracts.append(source)  # Source (content)
                replacer_targets.append((source, target))  # (Source, Target)
            else:
                log.write_warning(f"Invalid entry in replacer.json for {folder}: {target} -> {source}")
    except Exception as e:
        log.write_warning(f"Failed to parse replacer.json for {folder}: {e}")
