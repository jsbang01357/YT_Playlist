import json
from datetime import datetime
from pathlib import Path


DAILY_QUOTA_LIMIT = 10_000
PROJECT_ROOT = Path(__file__).resolve().parent.parent
QUOTA_USAGE_PATH = PROJECT_ROOT / "data" / "quota_usage.json"


def today_key():
    return datetime.now().date().isoformat()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def default_usage():
    return {
        "days": {}
    }


def load_usage():
    if not QUOTA_USAGE_PATH.exists():
        return default_usage()

    with QUOTA_USAGE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_usage(data):
    QUOTA_USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUOTA_USAGE_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def get_day_usage(date_key=None):
    key = date_key or today_key()
    data = load_usage()
    day = data.get("days", {}).get(key, {"total_units": 0, "events": []})
    total_units = int(day.get("total_units", 0))
    remaining_units = max(DAILY_QUOTA_LIMIT - total_units, 0)
    return {
        "date": key,
        "limit": DAILY_QUOTA_LIMIT,
        "used": total_units,
        "remaining": remaining_units,
        "usage_ratio": total_units / DAILY_QUOTA_LIMIT,
        "events": day.get("events", [])
    }


def record_quota(method, units, detail=""):
    key = today_key()
    data = load_usage()
    days = data.setdefault("days", {})
    day = days.setdefault(key, {"total_units": 0, "events": []})

    event = {
        "time": now_iso(),
        "method": method,
        "units": units,
        "detail": detail
    }
    day["total_units"] = int(day.get("total_units", 0)) + units
    day.setdefault("events", []).append(event)
    day["events"] = day["events"][-500:]

    save_usage(data)
    return get_day_usage(key)


def estimate_playlist_create(video_count):
    return 50 + (50 * video_count)


def estimate_video_add(video_count):
    return 50 * video_count


def estimate_playlist_list(item_count):
    return max((item_count + 49) // 50, 1)
