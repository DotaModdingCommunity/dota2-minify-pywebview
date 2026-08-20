import gzip
import io
import json
import os
import time
from typing import Any

from core import base, config, fs, log, net, output

# D2PFX Browser Constants
BASE_URL = "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/data/"
ASSETS_URL = "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/main/assets/files/"
VIDEO_PREVIEWS_URL = "https://raw.githubusercontent.com/h6rd/Dota2PornFxWeb/main/assets/previews/"
CACHE_DIR = os.path.join(base.cache_dir, "browsers", "d2pfx")
PREVIEWS_CACHE_DIR = os.path.join(CACHE_DIR, "previews")
BLACKLIST = [
    "guides",
    "item-sounds",
    "news",
    "optimization",
    "tools",
    "sites",
    "packs",
    "huds",  # https://github.com/Egezenn/dota2-minify/issues/143
    "fonts",
]


class DataManager:
    cache_dir: str
    previews_dir: str
    metadata: dict[str, Any] | None
    constants: dict[str, Any] | None
    _loading: bool
    _load_error: str | None

    def __init__(self) -> None:
        self.cache_dir = CACHE_DIR
        self.previews_dir = PREVIEWS_CACHE_DIR
        fs.create_dirs(self.cache_dir, self.previews_dir)
        self.metadata = None
        self.constants = None
        self._loading = False
        self._load_error = None

    def is_loaded(self) -> bool:
        return bool(self.metadata)

    def is_loading(self) -> bool:
        return self._loading

    def get_load_error(self) -> str | None:
        return self._load_error

    def fetch_gz_json(self, filename: str, force_refresh: bool = False) -> Any:
        local_path = os.path.join(self.cache_dir, filename.replace(".gz", ""))
        gz_url = f"{BASE_URL}data/{filename}"

        if not force_refresh and os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        try:
            response = net.get(gz_url, timeout=10)
            if response.status_code == 200:
                with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as f:
                    data = json.load(f)
                    with open(local_path, "w", encoding="utf-8") as out:
                        json.dump(data, out, indent=2)
                    return data
        except Exception as e:
            log.write_warning(f"Error fetching {filename}: {e}")
            output.add_text("&connection_error", msg_type="warning")

        return None

    def refresh(self) -> bool:
        self.metadata = self.fetch_gz_json("mods.json.gz", force_refresh=True)
        self.constants = self.fetch_gz_json("constants.json.gz", force_refresh=True)
        if self.metadata is not None:
            config.set("d2pfx_last_refresh", int(time.time()))
        return self.metadata is not None

    def _needs_refresh(self) -> bool:
        if not config.get("d2pfx_auto_refresh_catalogue", True):
            return False
        last_refresh = config.get("d2pfx_last_refresh", 0)
        return (time.time() - last_refresh) > 86400

    def load(self) -> bool:
        self._loading = True
        self._load_error = None
        try:
            if self._needs_refresh():
                self.refresh()

            self.metadata = self.fetch_gz_json("mods.json.gz")
            self.constants = self.fetch_gz_json("constants.json.gz")
            if self.metadata is None:
                self._load_error = "Failed to fetch D2PFX catalogue data"
            return self.metadata is not None
        except Exception as e:
            self._load_error = str(e)
            return False
        finally:
            self._loading = False

    def get_categories(self) -> list[str]:
        if not self.metadata:
            return []
        mods_data = self.metadata.get("modsData", {})
        return sorted([c for c in mods_data.keys() if c.lower() not in BLACKLIST])

    def get_category_name(self, cat_id: str) -> str:
        if not self.constants:
            return cat_id.capitalize()
        return self.constants.get(cat_id, cat_id.capitalize())

    def get_category_description(self, cat_id: str) -> str:
        if not self.constants:
            return ""
        return self.constants.get(f"{cat_id}-desc", "")

    def get_mods(self, cat_id: str) -> list[dict[str, Any]]:
        if not self.metadata:
            return []
        data = self.metadata.get("modsData", {}).get(cat_id, [])

        flattened = []

        def _flatten(item: Any) -> None:
            if isinstance(item, list):
                for sub in item:
                    _flatten(sub)
            elif isinstance(item, dict):
                if "groups" in item:
                    _flatten(item["groups"])
                elif "mods" in item:
                    _flatten(item["mods"])
                elif "name" in item:  # It's a mod
                    # Extract authors and senders from links
                    links = item.get("links", [])
                    for key, types in [("author", ("author", "modded")), ("sender", ("sender",))]:
                        vals = [l.get("name") or l.get("url") for l in links if l.get("type") in types]
                        vals = [x for x in vals if x]
                        item[key] = vals[0] if len(vals) == 1 else (vals or None)

                    flattened.append(item)
                else:
                    # Check if it's a dict that might contain groups/mods
                    for val in item.values():
                        if isinstance(val, (dict, list)):
                            _flatten(val)

        _flatten(data)
        return flattened

    def get_preview_url(self, cat_id: str, filename: str) -> str:
        if filename and filename.endswith(".webp"):
            filename = filename.replace(".webp", ".jpg")
        if filename and filename.endswith((".mp4", ".webm")):
            return f"{VIDEO_PREVIEWS_URL}{cat_id}/{filename}"
        return f"{BASE_URL}previews/{cat_id}/{filename}"

    def get_file_url(self, cat_id: str, filename: str) -> str:
        return f"{ASSETS_URL}{cat_id}/{filename}"
