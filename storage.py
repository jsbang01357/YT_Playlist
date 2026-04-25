import json
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path("data")
PLAYLIST_CACHE_PATH = DATA_DIR / "playlists.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path, data):
    ensure_data_dir()
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_playlist_cache(playlists):
    payload = {
        "last_synced_at": now_iso(),
        "playlists": playlists
    }
    write_json(PLAYLIST_CACHE_PATH, payload)
    return payload


def load_playlist_cache():
    return read_json(PLAYLIST_CACHE_PATH, {"last_synced_at": None, "playlists": []})


def save_playlist_videos(playlist_id, title, videos):
    payload = {
        "playlist_id": playlist_id,
        "title": title,
        "fetched_at": now_iso(),
        "videos": videos
    }
    write_json(DATA_DIR / f"playlist_{playlist_id}.json", payload)
    return payload
