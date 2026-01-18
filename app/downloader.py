import os
import re
import aiohttp
import asyncio
import hashlib
from urllib.parse import urlparse

from app.config import DOWNLOAD_DIR, MAX_CONCURRENT_DOWNLOAD, DOWNLOAD_TIMEOUT
from app.state import has_hash, add_hash


def safe_filename(text, max_len=100):
    text = re.sub(r"[\\/:*?\"<>|]", "", text)
    return text.strip()[:max_len]


def filename_from_item(item):
    title = safe_filename(item["title"])
    ext = os.path.splitext(urlparse(item["url"]).path)[1] or ".jpg"
    return f"{item['stt']:03d}_{title}{ext}"


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def download_one(session, item):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    async with session.get(item["url"], timeout=DOWNLOAD_TIMEOUT) as resp:
        if resp.status != 200:
            return None

        content = await resp.read()
        image_hash = compute_hash(content)

        # 👉 ĐÃ TỒN TẠI → KHÔNG TẢI
        if has_hash(image_hash):
            return None

        filename = filename_from_item(item)
        path = os.path.join(DOWNLOAD_DIR, filename)

        with open(path, "wb") as f:
            f.write(content)

        add_hash(image_hash)

        return {
            "stt": item["stt"],
            "title": item["title"],
            "local_image_path": path
        }


async def download_all(items):
    results = []

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOAD)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [download_one(session, item) for item in items]
        completed = await asyncio.gather(*tasks)

    for r in completed:
        if r:
            results.append(r)

    return results