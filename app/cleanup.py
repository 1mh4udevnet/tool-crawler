import os
import json
from app.config import DATA_FILE
from app.state import remove_hash


def delete_image_and_related(image_path):
    if not os.path.exists(image_path):
        return False

    # ===== LOAD DATA =====
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    removed_hash = None
    new_data = []

    for item in data:
        if item.get("local_image_path") == image_path:
            removed_hash = item.get("hash")
        else:
            new_data.append(item)

    # ===== XÓA FILE ẢNH =====
    os.remove(image_path)

    # ===== GHI LẠI DATA =====
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    # ===== CẬP NHẬT STATE (CHUẨN) =====
    if removed_hash:
        remove_hash(removed_hash)

    return True
