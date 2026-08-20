import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

from core import base, config, constants, fs, log, output, utils


def process(blacklist_txt: str, folder: str, blank_file_extensions: list[str]) -> None:
    with utils.open_utf8(blacklist_txt) as file:
        source = file.read()

    settings = config.get_mod_config(folder)
    blocks = re.split(r"(?=#\s*@key:\w+)", source)
    enabled = []
    for block in blocks:
        match = re.search(r"@key:(\w+)", block)
        key = match.group(1) if match else None
        if key is None or settings.get(key, True):
            enabled.append(block)

    lines = "".join(enabled).splitlines()
    blacklist_data = []
    blacklist_data_exclusions = set()
    blank_exts = tuple(blank_file_extensions)

    for index, line in enumerate(lines):
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        elif line.startswith((">>", "**")):
            blacklist_data.extend(process_dir(index, line, folder))

        elif line.startswith("*-"):
            blacklist_data_exclusions.update(process_dir(index, line, folder))

        elif line.startswith("--"):
            blacklist_data_exclusions.add(line[2:])

        else:
            if line.endswith(blank_exts):
                blacklist_data.append(line)
            else:
                log.write_warning(
                    f"[Invalid Extension] '{line}' in 'mods/{folder}/blacklist.txt' [line: {index + 1}] does not end in one of the valid extensions -> {blank_file_extensions}"
                )

    blacklist_data_set = set(blacklist_data)
    for exclusion in blacklist_data_exclusions:
        if exclusion not in blacklist_data_set:
            output.add_text(
                f"[Unnecessary Exclusion] '{exclusion}' in '{folder}' is not necessary, the mod doesn't include this file.",
                msg_type="warning",
            )

    blacklist_data = [item for item in blacklist_data if item not in blacklist_data_exclusions]

    def copy_blank_file(line: str) -> None:
        line = line.strip()
        path, extension = os.path.splitext(line)

        fs.create_dirs(os.path.join(constants.minify_dota_compile_output_path, os.path.dirname(path)))

        try:
            shutil.copy(
                os.path.join(base.blank_files_dir, f"blank{extension}"),
                os.path.join(
                    constants.minify_dota_compile_output_path,
                    path + extension,
                ),
            )
        except FileNotFoundError:
            log.write_warning(
                f"[Invalid Extension] '{line}' in 'mods/{os.path.basename(folder)}/blacklist.txt' does not end in one of the valid extensions -> {blank_file_extensions}"
            )

    with ThreadPoolExecutor() as executor:
        list(executor.map(copy_blank_file, blacklist_data))


def process_dir(index: int, line: str, folder: str) -> list[str]:
    data = []

    line = line[2:] if line.startswith("**") or line.startswith("*-") else line
    line = line + "/" if line.startswith(">>") else line
    line = line[2:] if line.startswith(">>") else line

    lines = subprocess.run(
        [
            constants.rg_exec_path,
            "--no-filename",
            "--no-line-number",
            "--color=never",
            line,
            os.path.join(base.bin_dir, "gamepakcontents.txt"),
        ],
        capture_output=True,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW if base.is_win else 0,
    )
    if lines.returncode == 2:
        log.write_warning(
            f"[Ripgrep Error] rg exited with code 2 searching '{line}' in gamepakcontents.txt -> mods/{folder}/blacklist.txt [line: {index + 1}]"
        )
        return []
    data = lines.stdout.splitlines()

    if not data:
        log.write_warning(
            f"[Directory Not Found] Could not find '{line}' in pak01_dir.vpk -> mods/{folder}/blacklist.txt [line: {index + 1}]"
        )

    return data
