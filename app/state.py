import json
import os
from app.config import STATE_FILE, DATA_DIR

_STATE_CACHE = None


def load_state():
    global _STATE_CACHE

    if _STATE_CACHE is not None:
        return _STATE_CACHE

    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(STATE_FILE):
        _STATE_CACHE = set()
        return _STATE_CACHE

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            _STATE_CACHE = set(json.load(f))
    except Exception:
        _STATE_CACHE = set()

    return _STATE_CACHE


def save_state(hashes):
    global _STATE_CACHE
    _STATE_CACHE = hashes

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(hashes), f, indent=2)


def has_hash(h):
    return h in load_state()


def add_hash(h):
    s = load_state()
    s.add(h)
    save_state(s)
