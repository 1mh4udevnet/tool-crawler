import argparse
import time
import asyncio
import os

from playwright.sync_api import sync_playwright, TimeoutError

from app.config import (
    TARGET_URL,
    HEADLESS,
    PAGE_WAIT,
    PAGE_LOAD_TIMEOUT,
    NEXT_BUTTON_SELECTOR,
)

from app.downloader import download_all
from app.exporter import export_to_json


# =========================
# PLAYWRIGHT FIX (BẮT BUỘC)
# =========================
# Ép Playwright KHÔNG dùng browser nội bộ
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"


def get_chrome_path():
    """Tự động tìm Chrome trên Windows"""
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("❌ Không tìm thấy Google Chrome trên máy")


# =========================
# CRAWL LOGIC
# =========================
def extract_images(page, start_index=1):
    results = []
    stt = start_index

    cards = page.query_selector_all("div.card")
    for card in cards:
        img = card.query_selector("img")
        title_el = card.query_selector("h3.title")

        if not img or not title_el:
            continue

        src = img.get_attribute("src") or img.get_attribute("data-src")
        if not src or not src.startswith("http"):
            continue

        title = title_el.inner_text().strip()

        results.append({
            "stt": stt,
            "title": title,
            "url": src
        })
        stt += 1

    return results


def click_next(page) -> bool:
    try:
        icon = page.locator(NEXT_BUTTON_SELECTOR).first
        btn = icon.locator("..")

        if btn.get_attribute("disabled") is not None:
            return False

        btn.click()
        return True

    except Exception:
        return False


def crawl_pages(start_page, end_page, stop_flag=None):
    all_items = []
    global_stt = 1

    chrome_path = get_chrome_path()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=chrome_path,
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ],
        )

        page = browser.new_page()

        print(f"Mở trang: {TARGET_URL}")
        page.goto(TARGET_URL, timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_load_state("networkidle")

        # 🔥 NHẢY TỚI START_PAGE
        current_page = 1
        while current_page < start_page:
            if stop_flag and stop_flag():
                print("[STOP] Đã dừng khi nhảy trang")
                browser.close()
                return []

            print(f"Đang bỏ qua TRANG {current_page}")
            if not click_next(page):
                print("Không thể nhảy tới trang bắt đầu")
                browser.close()
                return []

            time.sleep(PAGE_WAIT)
            current_page += 1

        # 🔥 BẮT ĐẦU CRAWL
        while current_page <= end_page:
            if stop_flag and stop_flag():
                print("[STOP] Đã dừng crawl")
                break

            print(f"\n=== Đang crawl TRANG {current_page} ===")

            items = extract_images(page, start_index=global_stt)
            print(f"Tìm thấy {len(items)} ảnh")

            all_items.extend(items)
            global_stt += len(items)

            if current_page == end_page:
                break

            if not click_next(page):
                break

            time.sleep(PAGE_WAIT)
            current_page += 1

        browser.close()

    return all_items


def run_crawler(start_page, end_page, stop_flag=None):
    items = crawl_pages(start_page, end_page, stop_flag)

    if stop_flag and stop_flag():
        print("[STOP] Dừng trước khi tải ảnh")
        return

    downloaded_data = asyncio.run(download_all(items))

    if downloaded_data:
        export_to_json(downloaded_data)
    else:
        print("Không có ảnh mới (tất cả đã tồn tại)")


# =========================
# CLI
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawler buavl.net (STT + title + image)"
    )

    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)

    args = parser.parse_args()

    if args.start < 1 or args.start > args.end:
        print("Trang không hợp lệ")
        exit(1)

    run_crawler(args.start, args.end)