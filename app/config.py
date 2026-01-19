import os
import sys

# =========================
# BASE DIR (python + exe)
# =========================
if getattr(sys, "frozen", False):
    # chạy từ file .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # chạy python ui.py
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# =========================
# DATA STRUCTURE (MỚI)
# =========================
DATA_DIR = os.path.join(BASE_DIR, "data")

INFO_DIR = os.path.join(DATA_DIR, "info")
PICTURE_DIR = os.path.join(DATA_DIR, "picture")

STATE_FILE = os.path.join(INFO_DIR, "state.json")
DATA_FILE = os.path.join(INFO_DIR, "data.json")

DOWNLOAD_DIR = PICTURE_DIR   # giữ tương thích code cũ

# tạo thư mục nếu chưa có
os.makedirs(INFO_DIR, exist_ok=True)
os.makedirs(PICTURE_DIR, exist_ok=True)

# =========================
# CRAWLER
# =========================
TARGET_URL = "https://buavl.net/"
HEADLESS = True
PAGE_WAIT = 2
PAGE_LOAD_TIMEOUT = 60000
NEXT_BUTTON_SELECTOR = "i.fas.fa-chevron-right"

# =========================
# DOWNLOADER
# =========================
MAX_CONCURRENT_DOWNLOAD = 5
DOWNLOAD_TIMEOUT = 30
