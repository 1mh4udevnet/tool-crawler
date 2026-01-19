import json
import os
from app.config import DATA_FILE, DATA_DIR


def export_to_json(items, filename=None):
    os.makedirs(DATA_DIR, exist_ok=True)

    if filename is None:
        path = DATA_FILE
    else:
        # ✅ nếu filename là path tuyệt đối → dùng luôn
        if os.path.isabs(filename):
            path = filename
        else:
            path = os.path.join(DATA_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
