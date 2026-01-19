import json
import os
from app.config import STATE_FILE, DATA_DIR


def load_state():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(STATE_FILE):
        return set()

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
            return set()
    except Exception:
        return set()


def save_state(hashes):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(hashes), f, indent=2)


def has_hash(h):
    """
    ✅ CHỈ CHECK TRONG FILE state.json
    - File không tồn tại → chưa có
    - File rỗng → chưa có
    """
    return h in load_state()


def add_hash(h):
    s = load_state()
    s.add(h)
    save_state(s)
