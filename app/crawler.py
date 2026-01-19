import argparse
import time
import asyncio
from playwright.sync_api import sync_playwright, TimeoutError

from app.config import (
    TARGET_URL,
    HEADLESS,
    PAGE_WAIT,
    PAGE_LOAD_TIMEOUT,
    NEXT_BUTTON_SELECTOR,
    DATA_FILE,          # ✅ thêm
)

from app.downloader import download_all
from app.exporter import export_to_json


# =========================
# LẤY ẢNH + TITLE (h3.title) + STT
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


# =========================
# CLICK TRANG TIẾP THEO
# =========================
def click_next(page) -> bool:
    try:
        icon = page.locator(NEXT_BUTTON_SELECTOR).first
        btn = icon.locator("..")

        if btn.get_attribute("disabled") is not None:
            return False

        btn.click()
        return True

    except TimeoutError:
        return False
    except Exception:
        return False


# =========================
# CRAWL THEO TRANG
# =========================
def crawl_pages(start_page: int, end_page: int):
    all_items = []
    global_stt = 1

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            channel="chrome"     # ✅ thêm 1 dòng (rất quan trọng cho exe)
        )
        page = browser.new_page()

        print(f"Mo trang: {TARGET_URL}")
        page.goto(TARGET_URL, timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_load_state("networkidle")

        current_page = 1

        while True:
            print(f"\n=== Dang crawl TRANG {current_page} ===")

            items = extract_images(page, start_index=global_stt)
            print(f"Tim thay {len(items)} anh")

            if start_page <= current_page <= end_page:
                all_items.extend(items)
                global_stt += len(items)

            if current_page >= end_page:
                break

            if not click_next(page):
                break

            time.sleep(PAGE_WAIT)
            current_page += 1

        browser.close()

    return all_items


# =========================
# LOGIC CHÍNH
# =========================
def run_crawler(start_page: int, end_page: int):
    items = crawl_pages(start_page, end_page)
    print(f"\nTong cong crawl duoc: {len(items)} anh")

    downloaded_data = asyncio.run(download_all(items))

    if downloaded_data:
        # ✅ dùng path tuyệt đối từ config
        export_to_json(downloaded_data, filename=DATA_FILE)
    else:
        print("Khong co anh moi (tat ca da ton tai)")


# =========================
# CLI
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Crawler buavl.net (STT + title + hash)"
    )

    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)

    args = parser.parse_args()

    if args.start < 1 or args.start > args.end:
        print("Trang khong hop le")
        exit(1)

    run_crawler(args.start, args.end)
