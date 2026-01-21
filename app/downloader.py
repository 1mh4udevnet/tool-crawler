import os
import re
import aiohttp
import asyncio
import hashlib
from urllib.parse import urlparse

from app.config import PICTURE_DIR, MAX_CONCURRENT_DOWNLOAD, DOWNLOAD_TIMEOUT

from app.state import has_hash, add_hash_and_inc_stt


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
    os.makedirs(PICTURE_DIR, exist_ok=True)

    async with session.get(item["url"], timeout=DOWNLOAD_TIMEOUT) as resp:
        if resp.status != 200:
            return None

        content = await resp.read()
        image_hash = compute_hash(content)

        if has_hash(image_hash):
            return None

        # 🔥 LẤY STT TOÀN CỤC
        stt = add_hash_and_inc_stt(image_hash)

        title = safe_filename(item["title"])
        ext = os.path.splitext(urlparse(item["url"]).path)[1] or ".jpg"
        filename = f"{stt:03d}_{title}{ext}"

        path = os.path.join(PICTURE_DIR, filename)

        with open(path, "wb") as f:
            f.write(content)

        return {
            "stt": stt,
            "title": item["title"],
            "local_image_path": path,
            "hash": image_hash,
        }

async def download_all(items):
    results = []

    timeout = aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)   # ✅ thêm
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_DOWNLOAD)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout
    ) as session:
        tasks = [download_one(session, item) for item in items]
        completed = await asyncio.gather(*tasks)

    for r in completed:
        if r:
            results.append(r)

    return results