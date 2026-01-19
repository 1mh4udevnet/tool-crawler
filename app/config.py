import os
import sys

if getattr(sys, "frozen", False):
    # chạy từ file .exe (dist/)
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # chạy python ui.py
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
DATA_FILE = os.path.join(DATA_DIR, "data.json")

DOWNLOAD_DIR = os.path.join(BASE_DIR, "picturedownload")

# crawler
TARGET_URL = "https://buavl.net/"
HEADLESS = True
PAGE_WAIT = 2
PAGE_LOAD_TIMEOUT = 60000
NEXT_BUTTON_SELECTOR = "i.fas.fa-chevron-right"

# downloader
MAX_CONCURRENT_DOWNLOAD = 5
DOWNLOAD_TIMEOUT = 30
