"Crashlogs, warnings and debug zip creation"

import os
import threading
import time
import traceback
import zipfile
from types import TracebackType
from typing import Any

from core import base, output, utils

_log_lock = threading.Lock()


def write_crashlog(
    exc_type: type[BaseException] | None = None,
    exc_value: BaseException | None = None,
    exc_traceback: TracebackType | None = None,
    header: str | None = None,
    handled: bool = True,
) -> None:

    path = base.log_crashlog if handled else base.log_unhandled
    with _log_lock:
        with utils.open_utf8R(path, "a") as file:
            if handled:
                if header:
                    file.write(message := f"{header}\n\n{traceback.format_exc()}")
                else:
                    file.write(message := traceback.format_exc())
            else:
                file.write(message := f"{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}")

            if message and not handled:
                lines = message.rstrip().splitlines()
                output.add_text(lines[0], msg_type="error")
                if len(lines) > 1:
                    output.add_text("\n".join(lines[1:]), msg_type="detail")
    if base.FROZEN:
        create_debug_zip()


def write_warning(header: str | None = None, *args: Any, show_traceback: bool = True) -> None:

    with _log_lock:
        if not os.path.exists(base.log_warnings):
            with utils.open_utf8R(base.log_warnings, "w") as file:
                pass

        exc = traceback.format_exc()
        if "NoneType: None" in exc and header is None:
            return

        file_message = ""
        with utils.open_utf8R(base.log_warnings, "a") as file:
            if "NoneType: None" not in exc:
                if header:
                    file_message = f"{header}\n\n{exc}"
                else:
                    file_message = exc
            else:
                file_message = f"{header}"

            file.write(f"{file_message}\n{'-' * 50}\n\n")

    console_message = file_message if show_traceback else header
    if console_message:
        if show_traceback and header and "NoneType: None" not in exc:
            # Keep the terminal readable: context line as the warning, the
            # raw traceback as dimmed detail (the full text still lands in
            # warnings.txt above).
            output.add_text(header, *args, msg_type="warning")
            output.add_text(exc.rstrip(), msg_type="detail")
        else:
            output.add_text(console_message, *args, msg_type="warning")


def create_debug_zip():
    from core import fs

    with utils.try_pass():
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        zip_filename = f"minify_debug_{timestamp}.zip"

        files_to_include = [
            base.main_config_file_dir,
            base.mods_config_dir,
        ]

        if os.path.exists(base.logs_dir):
            for file in os.listdir(base.logs_dir):
                files_to_include.append(os.path.join(base.logs_dir, file))

        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files_to_include:
                if os.path.exists(file_path):
                    zipf.write(file_path)

        with utils.try_pass():
            output.add_text("&heeeeeeeeeeeeeelp", zip_filename)
        fs.open_thing(".")
