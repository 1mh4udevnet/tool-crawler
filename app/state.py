import json
import os
from app.config import STATE_FILE, INFO_DIR


def load_state():
    os.makedirs(INFO_DIR, exist_ok=True)

    if not os.path.exists(STATE_FILE):
        return {
            "hashes": set(),
            "last_stt": 0
        }

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            return {
                "hashes": set(data.get("hashes", [])),
                "last_stt": data.get("last_stt", 0)
            }
    except Exception:
        return {
            "hashes": set(),
            "last_stt": 0
        }


def save_state(state):
    os.makedirs(INFO_DIR, exist_ok=True)

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "hashes": list(state["hashes"]),
                "last_stt": state["last_stt"]
            },
            f,
            ensure_ascii=False,
            indent=2
        )


def has_hash(h):
    state = load_state()
    return h in state["hashes"]


def add_hash_and_inc_stt(h):
    state = load_state()
    state["hashes"].add(h)
    state["last_stt"] += 1
    save_state(state)
    return state["last_stt"]


def get_last_stt():
    return load_state()["last_stt"]

def remove_hash(h):
    state = load_state()

    hashes = state.get("hashes", [])
    if h in hashes:
        hashes.remove(h)

    state["hashes"] = hashes
    save_state(state)