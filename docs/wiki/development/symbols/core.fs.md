# core.fs

Filesystem access

## `open_thing(path, args)`

Opens files or directories in their regsitered applications

<details open><summary>Source</summary>

```python
def open_thing(path: str, args: str = "") -> None:
    "Opens files or directories in their regsitered applications"

    try:
        # If args are provided and target is executable, prefer launching directly
        if args:
            if base.is_win:
                os.startfile(path, arguments=args)
                return
            # POSIX: launch executable directly when possible
            if os.access(path, os.X_OK) and os.path.isfile(path):
                cmd = [path] + shlex.split(args)
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            # Non-executables with args: fall back to opening container directory
            path = os.path.dirname(path) or "."

        # No args path open
        if os.path.isdir(path):
            if base.is_win:
                os.startfile(path)
            elif base.is_mac:
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            if base.is_win:
                os.startfile(path)
            elif base.is_mac:
                # Reveal the file in Finder to avoid missing-app association errors
                subprocess.run(["open", "-R", path])
            else:
                subprocess.run(["xdg-open", path])
    except FileNotFoundError:
        output.add_text("&open_thing_fail", path, msg_type="error")

```

</details>

## `move_path(src, dst)`

Superset of `shutil.move`, `os.rename` to handle permissions for moving and renaming.

<details open><summary>Source</summary>

```python
def move_path(src: str, dst: str) -> None:
    "Superset of `shutil.move`, `os.rename` to handle permissions for moving and renaming."
    try:
        shutil.move(src, dst)
    except PermissionError:
        try:
            paths_to_chmod = []
            if os.path.exists(src):
                paths_to_chmod.append(src)
            if os.path.exists(dst):
                paths_to_chmod.append(dst)

            for path in paths_to_chmod:
                if os.path.isdir(path):
                    for root, _, filenames in os.walk(path):
                        current_dir_mode = os.stat(root).st_mode
                        os.chmod(root, current_dir_mode | stat.S_IWUSR)

                        for filename in filenames:
                            filepath = os.path.join(root, filename)
                            current_file_mode = os.stat(filepath).st_mode
                            os.chmod(filepath, current_file_mode | stat.S_IWUSR)
                else:
                    current_file_mode = os.stat(path).st_mode
                    os.chmod(path, current_file_mode | stat.S_IWUSR)

            return move_path(src, dst)
        except Exception:
            log.write_warning(f"Failed to move {src} -> {dst}")
    except FileNotFoundError:
        output.add_text("&fs_skip_move_not_found", src, msg_type="warning")

```

</details>

## `remove_path()`

Superset of `shutil.rmtree` & `os.remove` to handle permissions. Takes in list of paths. If `if_exists`, silently skip paths that do not exist.

<details open><summary>Source</summary>

```python
def remove_path(*paths: str, if_exists: bool = False) -> None:
    "Superset of `shutil.rmtree` & `os.remove` to handle permissions. Takes in list of paths. If `if_exists`, silently skip paths that do not exist."
    try:
        for path in paths:
            if if_exists and not os.path.exists(path):
                continue
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except FileNotFoundError:
                output.add_text("&skipped_deletion", path, msg_type="warning")

    except PermissionError:
        try:
            for path in paths:
                if if_exists and not os.path.exists(path):
                    continue
                if os.path.isdir(path):
                    for root, _, filenames in os.walk(path):
                        current_dir_mode = os.stat(root).st_mode
                        os.chmod(root, current_dir_mode | stat.S_IWUSR)

                        for filename in filenames:
                            filepath = os.path.join(root, filename)
                            current_file_mode = os.stat(filepath).st_mode
                            os.chmod(filepath, current_file_mode | stat.S_IWUSR)
                else:
                    current_file_mode = os.stat(path).st_mode
                    os.chmod(path, current_file_mode | stat.S_IWUSR)

            # Retry once after granting write permissions (chmod won't unlock
            # handles held by other processes, so never recurse unboundedly)
            for path in paths:
                if if_exists and not os.path.exists(path):
                    continue
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except FileNotFoundError:
                    output.add_text("&skipped_deletion", path, msg_type="warning")
        except Exception:
            log.write_warning(f"Failed to remove paths: {', '.join(paths)}")

```

</details>

## `create_dirs()`

Recursively creates directories (like mkdir -p).
Supports multiple arguments and avoids crashing on empty paths.

<details open><summary>Source</summary>

```python
def create_dirs(*paths: str) -> None:
    """
    Recursively creates directories (like mkdir -p).
    Supports multiple arguments and avoids crashing on empty paths.
    """
    for path in paths:
        if path:
            os.makedirs(path, exist_ok=True)

```

</details>

## `backup_directory(source, backup)`

Copy entire contents of source into backup. No-op if backup already exists.

<details open><summary>Source</summary>

```python
def backup_directory(source: str, backup: str) -> None:
    """Copy entire contents of source into backup. No-op if backup already exists."""
    if os.path.exists(backup):
        return
    create_dirs(backup)
    for name in os.listdir(source):
        move_path(os.path.join(source, name), os.path.join(backup, name))

```

</details>

## `restore_directory(source, backup)`

Restore contents from backup into source, then remove backup.

<details open><summary>Source</summary>

```python
def restore_directory(source: str, backup: str) -> None:
    """Restore contents from backup into source, then remove backup."""
    if not os.path.exists(backup):
        return
    for name in os.listdir(source):
        remove_path(os.path.join(source, name))
    for name in os.listdir(backup):
        move_path(os.path.join(backup, name), os.path.join(source, name))
    remove_path(backup)

```

</details>

## `download_file(url, target_path, progress_callback, log_level, dedupe_set)`

Downloads a file from url to target_path using requests.
Calls progress_callback(downloaded, total) on each chunk if provided.
On failure, logs with msg_type=log_level (None = silent). If dedupe_set is
provided, the unique error is only logged the first time it is encountered.

<details open><summary>Source</summary>

```python
def download_file(
    url: str,
    target_path: str,
    progress_callback: Callable[[int, int], None] | None = None,
    log_level: str = "error",
    dedupe_set: set | None = None,
) -> bool:
    """
    Downloads a file from url to target_path using requests.
    Calls progress_callback(downloaded, total) on each chunk if provided.
    On failure, logs with msg_type=log_level (None = silent). If dedupe_set is
    provided, the unique error is only logged the first time it is encountered.
    """

    try:
        response = net.get(url, stream=True, timeout=(5, 15))
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        block_size = 8192
        downloaded = 0

        tmp_path = f"{target_path}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tmp_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        os.replace(tmp_path, target_path)
        return True
    except Exception as e:
        if log_level is not None:
            error_key = str(e)
            if dedupe_set is None or error_key not in dedupe_set:
                if dedupe_set is not None:
                    dedupe_set.add(error_key)
                output.add_text("&fs_download_failed", target_path, e, msg_type=log_level)
        return False

```

</details>

## `extract_archive(archive_path, extract_dir, target_file, progress_callback)`

Extracts an archive (zip or tar.gz).
If target_file is provided, extracts only that file (or directory structure leading to it).
progress_callback(fraction, status_text) is invoked with a byte-weighted
fraction in [0, 1] as members are extracted, including increments within
individual large members, when provided.

<details open><summary>Source</summary>

```python
def extract_archive(
    archive_path: str,
    extract_dir: str = ".",
    target_file: str | None = None,
    progress_callback: Callable[[float, str], None] | None = None,
) -> bool:
    """
    Extracts an archive (zip or tar.gz).
    If target_file is provided, extracts only that file (or directory structure leading to it).
    progress_callback(fraction, status_text) is invoked with a byte-weighted
    fraction in [0, 1] as members are extracted, including increments within
    individual large members, when provided.
    """

    try:
        if archive_path.endswith(".zip"):
            with zipfile.ZipFile(archive_path) as zip_ref:
                extract_dir_abs = os.path.abspath(extract_dir)
                members = zip_ref.infolist()
                if target_file:
                    members = [m for m in members if m.filename == target_file]
                    if not members:
                        raise KeyError(target_file)
                total = sum(m.file_size for m in members if not m.is_dir()) or 1
                done = 0
                for member in members:
                    member_path = os.path.abspath(os.path.join(extract_dir_abs, member.filename))
                    if os.path.commonpath([extract_dir_abs, member_path]) != extract_dir_abs:
                        continue
                    if member.is_dir():
                        os.makedirs(member_path, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(member_path), exist_ok=True)
                    with zip_ref.open(member) as src, open(member_path, "wb") as dst:
                        while True:
                            chunk = src.read(1024 * 256)
                            if not chunk:
                                break
                            dst.write(chunk)
                            done += len(chunk)
                            if progress_callback:
                                progress_callback(min(1.0, done / total), member.filename)
                    mode = (member.external_attr >> 16) & 0o777
                    if mode:
                        os.chmod(member_path, mode)
        elif archive_path.endswith((".tar.gz", ".tgz")):
            with tarfile.open(archive_path, "r:gz") as tar:
                extract_dir_abs = os.path.abspath(extract_dir)
                safe_members = []
                for member in tar.getmembers():
                    member_path = os.path.abspath(os.path.join(extract_dir_abs, member.name))
                    if os.path.commonpath([extract_dir_abs, member_path]) == extract_dir_abs:
                        safe_members.append(member)

                if target_file:
                    try:
                        member = tar.getmember(target_file)
                        if member in safe_members:
                            if hasattr(tarfile, "data_filter"):
                                tar.extract(member, path=extract_dir, filter="data")
                            else:
                                tar.extract(member, path=extract_dir)
                    except KeyError:
                        pass
                else:
                    if hasattr(tarfile, "data_filter"):
                        tar.extractall(path=extract_dir, members=safe_members, filter="data")
                    else:
                        tar.extractall(path=extract_dir, members=safe_members)
        else:
            output.add_text("&fs_unsupported_archive", archive_path, msg_type="error")
            return False
        return True
    except Exception as e:
        output.add_text("&fs_extraction_failed", e, msg_type="error")
        return False

```

</details>

## `copy_file(src, dst, progress_callback)`

Copies a single file with optional byte-weighted progress reporting.
progress_callback(fraction, status_text) is invoked as chunks are written.

<details open><summary>Source</summary>

```python
def copy_file(
    src: str,
    dst: str,
    progress_callback: Callable[[float, str], None] | None = None,
) -> bool:
    """
    Copies a single file with optional byte-weighted progress reporting.
    progress_callback(fraction, status_text) is invoked as chunks are written.
    """
    tmp = f"{dst}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        total = os.path.getsize(src) or 1
        done = 0
        with open(src, "rb") as src_file, open(tmp, "wb") as dst_file:
            while True:
                chunk = src_file.read(1024 * 256)
                if not chunk:
                    break
                dst_file.write(chunk)
                done += len(chunk)
                if progress_callback:
                    progress_callback(min(1.0, done / total), os.path.basename(dst))
        os.replace(tmp, dst)
        return True
    except Exception as e:
        output.add_text("&fs_copy_failed", src, e, msg_type="error")
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        return False

```

</details>

## `get_file_type(path)`

Identifies the file type. It first checks magic bytes (e.g., '.png', '.jpg', '.webm'),
and falls back to extracting the extension from the first dot in the filename if no known magic bytes are found.

<details open><summary>Source</summary>

```python
def get_file_type(path: str) -> str | None:
    """
    Identifies the file type. It first checks magic bytes (e.g., '.png', '.jpg', '.webm'),
    and falls back to extracting the extension from the first dot in the filename if no known magic bytes are found.
    """
    # can be extended by just handing it to a module
    with utils.try_pass():
        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            header = f.read(16)

            # PNG: 89 50 4E 47 0D 0A 1A 0A
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ".png"

            # JPEG: FF D8 FF (Start of Image + specific marker)
            if header.startswith(b"\xff\xd8\xff"):
                return ".jpg"

            # WEBP: RIFF....WEBP
            if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                return ".webp"

            # WEBM/MKV: 1A 45 DF A3 (EBML)
            if header.startswith(b"\x1a\x45\xdf\xa3"):
                return ".webm"

            # MP4: ....ftyp
            if header[4:8] == b"ftyp":
                return ".mp4"

            # GIF
            if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
                return ".gif"

    # Fallback: return extension from the first dot or the filename itself if no dot exists
    basename = os.path.basename(path)
    dot_index = basename.find(".")
    if dot_index != -1:
        return basename[dot_index:]

    return basename

```

</details>
