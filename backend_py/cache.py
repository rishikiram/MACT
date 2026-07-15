import json
from collections import OrderedDict
from pathlib import Path

CACHE_SIZE = 8
CACHE_DIR = Path(__file__).parent / "cache"
INDEX_FILE = CACHE_DIR / "_index.json"

# LRU index: hash -> True, insertion order tracks recency.
# Actual data lives in CACHE_DIR/{hash}.json. Order is serialized to INDEX_FILE
# so recency (including cache_get hits, not just writes) survives a restart.
_query_cache: "OrderedDict[str, bool]" = OrderedDict()
_loaded_from_disk = False


def _cache_file_path(hash_: str) -> Path:
    return CACHE_DIR / f"{hash_}.json"


def _save_index() -> None:
    with open(INDEX_FILE, "w") as f:
        json.dump(list(_query_cache.keys()), f)


def _load_cache_from_disk() -> None:
    global _loaded_from_disk
    if _loaded_from_disk:
        return
    _loaded_from_disk = True
    if not CACHE_DIR.exists():
        return

    files = {f.stem for f in CACHE_DIR.iterdir() if f.suffix == ".json" and f != INDEX_FILE}

    order = []
    try:
        with open(INDEX_FILE) as f:
            order = [h for h in json.load(f) if h in files]
    except (OSError, json.JSONDecodeError):
        order = []

    # Any cache files not accounted for in the index (e.g. index missing/stale)
    # get appended oldest-first by mtime, so nothing on disk is silently dropped.
    leftover = sorted(files - set(order), key=lambda h: _cache_file_path(h).stat().st_mtime)
    order = leftover + order

    for h in order[:-CACHE_SIZE]:
        _cache_file_path(h).unlink(missing_ok=True)
    for h in order[-CACHE_SIZE:]:
        _query_cache[h] = True

    if _query_cache:
        n = len(_query_cache)
        print(f"[cache] loaded {n} entr{'y' if n == 1 else 'ies'} from disk")
        _save_index()


def cache_get(hash_: str):
    _load_cache_from_disk()
    if hash_ not in _query_cache:
        return None
    try:
        with open(_cache_file_path(hash_)) as f:
            value = json.load(f)
        _query_cache.move_to_end(hash_)
        _save_index()
        return value
    except (OSError, json.JSONDecodeError):
        _query_cache.pop(hash_, None)
        _save_index()
        return None


def cache_set(hash_: str, value) -> None:
    _load_cache_from_disk()
    _query_cache.pop(hash_, None)
    if len(_query_cache) >= CACHE_SIZE:
        oldest, _ = _query_cache.popitem(last=False)
        _cache_file_path(oldest).unlink(missing_ok=True)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_cache_file_path(hash_), "w") as f:
        json.dump(value, f)
    _query_cache[hash_] = True
    _save_index()
