# ui.modals

Modal types

## `Announcements()`

*No documentation available.*

<details open><summary>Source</summary>

```python
class Announcements:
    @staticmethod
    def show(announcement: dict[str, Any]) -> None:
        threading.Thread(target=Announcements._thread, args=(announcement,), daemon=True).start()

    @staticmethod
    def _thread(announcement: dict[str, Any]) -> None:
        answer = modal_shared.show(
            title="Announcement",
            messages=[announcement.get("text", "")],
            buttons=["Ignore", "OK"],
        )
        if answer is None:
            return
        announcements.handle_announcement_action(announcement, answer)

    @staticmethod
    def check():
        for ann in announcements.get_pending_announcements():
            Announcements.show(ann)

```

</details>

## `Uninstall()`

*No documentation available.*

<details open><summary>Source</summary>

```python
class Uninstall:
    @staticmethod
    def show():
        threading.Thread(target=Uninstall._thread, daemon=True).start()

    @staticmethod
    def _thread():
        answer = modal_shared.show(
            title="Uninstall",
            messages=["Remove all mods?"],
            buttons=["Cancel", "Confirm"],
        )
        if answer == "Confirm":
            from patch.unins import uninstall as _uninstall_mods

            def _run_uninstall():
                try:
                    _uninstall_mods()
                except Exception:
                    from core import log

                    log.write_crashlog(header="Uninstall failed")

            threading.Thread(target=_run_uninstall, daemon=True).start()

```

</details>

## `WorkshopTools()`

*No documentation available.*

<details open><summary>Source</summary>

```python
class WorkshopTools:
    @staticmethod
    def show():
        threading.Thread(target=WorkshopTools._thread, daemon=True).start()

    @staticmethod
    def _thread():
        config.set("workshop_modal_shown", True)
        if base.is_linux or base.is_mac:
            answer = modal_shared.show(
                title="Workshop Tools Not Found",
                messages=[
                    "Dota 2 Workshop Tools are not installed.",
                    "Some mods require them and have been disabled.",
                    "Click OK to go to the related wiki section.",
                ],
                buttons=["No", "OK"],
            )
            if answer == "OK":
                webbrowser.open(
                    "https://egezenn.github.io/dota2-minify/wiki/#/troubleshooting_faq?id=workshop-tools-dlc"
                )
        else:
            modal_shared.show(
                title="Workshop Tools Not Found",
                messages=[
                    "Dota 2 Workshop Tools are not installed.",
                    "Some mods require them and have been disabled.",
                    "Install them from Steam: Library \u2192 Tools \u2192 Dota 2 Workshop Tools",
                ],
                buttons=["OK"],
            )

```

</details>

## `Update()`

*No documentation available.*

<details open><summary>Source</summary>

```python
class Update:
    @staticmethod
    def show(version: str, url: str | None = None) -> None:
        threading.Thread(target=Update._thread, args=(version, url), daemon=True).start()

    @staticmethod
    def is_portable() -> bool:
        if not base.FROZEN:
            return True
        return not os.path.exists(os.path.join(os.path.dirname(sys.executable), "unins000.exe"))

    @staticmethod
    def perform_update(url: str | None) -> None:
        if base.is_win and url and not Update.is_portable():
            threading.Thread(target=Update._download_thread, args=(url,), daemon=True).start()
        elif base.is_mac and url:
            threading.Thread(target=Update._posix_download_thread, args=(url, "-macos.zip"), daemon=True).start()
        elif base.is_linux and url:
            threading.Thread(target=Update._posix_download_thread, args=(url, "-linux.zip"), daemon=True).start()
        else:
            webbrowser.open(base.github_io)
            fs.open_thing(".")

    @staticmethod
    def _thread(version: str, url: str | None) -> None:
        answer = modal_shared.show(
            title="Update available",
            messages=["New update is available!", f"Version {version} is available. Would you like to update?"],
            buttons=["No", "Skip update", "Yes"],
        )
        if answer == "Yes":
            Update.perform_update(url)
        elif answer == "Skip update":
            config.set("ignore_update", version)

    @staticmethod
    def _download_with_progress(url: str, dest_path: str, label: str, post_download: Any = None) -> None:
        modal_shared.show_progress(["&status_downloading_update", label])
        response = net.get(url, stream=True, timeout=30)
        response.raise_for_status()
        total_length = response.headers.get("content-length")

        downloaded = 0
        last_report_time = 0
        with open(dest_path, "wb") as f:
            if total_length is None:
                f.write(response.content)
                modal_shared.set_progress(1.0, "&status_download_complete")
            else:
                total_length = int(total_length)
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded += len(chunk)
                        f.write(chunk)
                        current_time = time.time()
                        if current_time - last_report_time >= 0.1:
                            progress = downloaded / total_length
                            modal_shared.set_progress(
                                progress, "&status_progress_mb", f"{downloaded / (1024 * 1024):.1f}", f"{total_length / (1024 * 1024):.1f}"
                            )
                            last_report_time = current_time
        modal_shared.set_progress(1.0, label)
        if post_download:
            post_download(dest_path)

    @staticmethod
    def _download_thread(url: str) -> None:
        try:
            temp_dir = tempfile.gettempdir()
            installer_name = url.split("/")[-1]
            installer_path = os.path.join(temp_dir, installer_name)

            Update._download_with_progress(url, installer_path, "&status_launching_installer", post_download=lambda p: None)
            time.sleep(0.5)
            modal_shared.hide_progress()
            os.startfile(installer_path)
            os._exit(0)
        except Exception as e:
            log.write_warning(f"Update download failed: {e}")
            modal_shared.hide_progress()
            modal_shared.show("Error", ["Update failed to download.", str(e)], ["OK"])
            webbrowser.open(base.github_io)
            fs.open_thing(".")

    @staticmethod
    def _posix_download_thread(url: str, suffix: str) -> None:
        """Download POSIX zip release and extract alongside current app."""
        try:
            temp_dir = tempfile.gettempdir()
            zip_name = url.split("/")[-1]
            zip_path = os.path.join(temp_dir, zip_name)

            def _extract(_dest: str) -> None:
                time.sleep(0.3)
                app_dir = os.path.dirname(sys.executable) if base.FROZEN else os.getcwd()
                parent_dir = os.path.dirname(app_dir)
                extract_dir = os.path.join(parent_dir, f"Minify-{zip_name.replace(suffix, '')}")
                fs.create_dirs(extract_dir)
                modal_shared.set_progress(1.0, "&status_extracting_to", os.path.basename(extract_dir))
                fs.extract_archive(zip_path, extract_dir)
                modal_shared.hide_progress()
                fs.open_thing(extract_dir)
                modal_shared.show(
                    "Update Downloaded",
                    [
                        f"Extracted to: {extract_dir}",
                        "Close Minify and launch the new version from the extracted folder.",
                    ],
                    ["OK"],
                )

            Update._download_with_progress(url, zip_path, "&status_download_complete", post_download=_extract)
        except Exception as e:
            log.write_warning(f"Update download failed: {e}")
            modal_shared.hide_progress()
            modal_shared.show("Error", ["Update failed to download.", str(e)], ["OK"])
            webbrowser.open(base.github_io)
            fs.open_thing(".")

    @staticmethod
    def check():
        if not base.FROZEN and not config.get("debug_env", False):
            log.write_warning("Update check skipped: not frozen")
            return

        def _check():
            try:
                if config.get("debug_env", False):
                    api_url = "http://localhost:8000/releases_mock.json"
                else:
                    api_url = f"https://api.github.com/repos/{base.OWNER}/{base.REPO}/releases"

                response = net.get(api_url, timeout=15)
                response.raise_for_status()
                releases = response.json()

                if base.is_win:
                    suffix = ".exe"
                elif base.is_mac:
                    suffix = "-macos.zip"
                else:
                    suffix = "-linux.zip"
                download_url = None
                tag_name = None

                opt_in = config.get("opt_into_rcs", False)
                debug = config.get("debug_env", False)
                for release in releases:
                    if release["prerelease"] and not re.search(r"rc\d+$", base.VERSION) and not opt_in and not debug:
                        continue
                    for asset in release.get("assets", []):
                        if asset["name"].endswith(suffix):
                            download_url = asset["browser_download_url"]
                            tag_name = release["tag_name"]
                            break
                    if download_url:
                        break

                if download_url and tag_name:
                    match = re.match(r"^Minify-v(.+)", tag_name)
                    remote_version = match.group(1) if match else tag_name
                    from packaging.version import Version

                    if Version(base.VERSION) < Version(remote_version):
                        if config.get("ignore_update") == remote_version and not debug:
                            return
                        Update.show(remote_version, download_url)
            except Exception as e:
                log.write_warning(f"Update check failed: {e}")
                modal_shared.show("Update check failed", ["Couldn't check for updates.", str(e)], ["OK"])

        threading.Thread(target=_check, daemon=True).start()

```

</details>
