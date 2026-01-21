import json
import os
from app.config import DATA_FILE, INFO_DIR


def export_to_json(items):
    os.makedirs(INFO_DIR, exist_ok=True)

    # load cũ
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                old_items = json.load(f)
                if not isinstance(old_items, list):
                    old_items = []
        except Exception:
            old_items = []
    else:
        old_items = []

    # append + sort
    old_items.extend(items)
    old_items.sort(key=lambda x: x.get("stt", 0))

    # ghi lại
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(old_items, f, ensure_ascii=False, indent=2)

    print(f"[OK] Đã ghi {len(items)} item ")
