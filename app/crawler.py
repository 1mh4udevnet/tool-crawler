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
    """
    Trích xuất ảnh thông minh (Deep Scanning)
    Quét tất cả các thẻ <img> và các thuộc tính tiềm năng.
    """
    # Đợi một chút để ảnh lazy-load kịp hiện diện trong DOM
    time.sleep(1)
    
    results = []
    stt = start_index
    imgs = page.query_selector_all("img")
    base_url = page.url

    for img in imgs:
        # Lấy TẤT CẢ thuộc tính của thẻ img để tìm link ảnh
        all_attrs = page.evaluate('''(el) => {
            let attrs = {};
            for (let i = 0; i < el.attributes.length; i++) {
                attrs[el.attributes[i].name] = el.attributes[i].value;
            }
            return attrs;
        }''', img)

        src = None
        # Ưu tiên các thuộc tính phổ biến
        for attr in ["data-src", "data-original", "data-lazy-src", "srcset", "src", "data-lazy"]:
            if attr in all_attrs and all_attrs[attr]:
                val = all_attrs[attr]
                if val.strip().startswith("http") or val.strip().startswith("/") or val.strip().startswith("//"):
                    src = val
                    break
        
        # Nếu vẫn không thấy, quét sạch toàn bộ thuộc tính tìm link ảnh
        if not src:
            for attr_name, attr_val in all_attrs.items():
                if isinstance(attr_val, str) and (attr_val.endswith((".jpg", ".png", ".jpeg", ".gif", ".webp")) or "http" in attr_val):
                    src = attr_val
                    break

        if not src:
            continue
            
        # Xử lý srcset
        if " " in src and "," in src:
            src = src.split(",")[0].split(" ")[0]
        elif " " in src:
            src = src.split(" ")[0]

        # Bộ lọc rác thông minh
        img_id = (all_attrs.get("id") or "").lower()
        img_class = (all_attrs.get("class") or "").lower()
        alt_text = (all_attrs.get("alt") or "").lower()
        
        # Chỉ chặn rác hệ thống thực sự (icon nhỏ, avatar mặc định)
        is_junk = any(kw in (img_id + img_class + alt_text + src.lower()) 
                     for kw in ["favicon", "icon-", "tracker", "ads-", "advertisement"])

        if is_junk:
            continue

        # Lọc kích thước (Nới lỏng để không mất ảnh meme)
        try:
            width = int(all_attrs.get("width") or 0)
            height = int(all_attrs.get("height") or 0)
            if (width > 0 and width < 60) or (height > 0 and height < 60):
                continue
        except: pass

        # Chuẩn hóa URL
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            from urllib.parse import urljoin
            src = urljoin(base_url, src)
        elif not src.startswith("http"):
            continue

        title = all_attrs.get("alt") or all_attrs.get("title") or f"Image_{stt}"
        title = title.strip()[:100]

        results.append({
            "stt": stt,
            "title": title,
            "url": src
        })
        stt += 1

    # Loại bỏ link trùng lặp
    seen_urls = set()
    unique_results = []
    for item in results:
        if item["url"] not in seen_urls:
            unique_results.append(item)
            seen_urls.add(item["url"])
            
    return unique_results


def click_next_or_scroll(page) -> bool:
    """
    Thông minh: Tìm nút Tiếp, Xem thêm hoặc Cuộn xuống nếu không có nút.
    """
    try:
        # 1. Tìm các nút có chữ "Tiếp", "Next", "Xem thêm", "More"
        selectors = [
            "text='Trang tiếp'", "text='Trang sau'", "text='Next'", 
            "text='Xem thêm'", "text='Load more'", "text='More'",
            "span.next-icon", "button.load-more", "i.fas.fa-chevron-right", "i.fa-chevron-right"
        ]
        
        for sel in selectors:
            btn = page.query_selector(sel)
            if btn and btn.is_visible() and btn.is_enabled():
                btn.click()
                print(f"[Smart] Chuyển trang tiếp theo")
                return True

        # 2. Nếu không có nút, thử cuộn xuống (Progressive Scroll)
        print("[Smart] Không thấy nút, đang thử cuộn trang bậc thang...")
        previous_height = page.evaluate("document.body.scrollHeight")
        
        # Cuộn 3 lần, mỗi lần một đoạn để kích hoạt lazy-load
        for i in range(1, 4):
            scroll_to = (previous_height // 3) * i
            page.evaluate(f"window.scrollTo(0, {scroll_to})")
            time.sleep(1)
        
        # Đợi thêm một chút để nội dung mới nạp hẳn
        time.sleep(2)
        
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height > previous_height:
            print("[Smart] Đã nạp thành công nội dung mới.")
            return True
            
        return False

    except Exception as e:
        print(f"[Smart] Lỗi khi chuyển nội dung: {e}")
        return False


def crawl_pages(start_page, end_page, target_url=TARGET_URL, stop_flag=None, progress_callback=None):
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

        print(f"Mở trang: {target_url}")
        page.goto(target_url, timeout=PAGE_LOAD_TIMEOUT)
        page.wait_for_load_state("networkidle")

        # 🔥 NHẢY TỚI START_PAGE
        current_page = 1
        while current_page < start_page:
            if stop_flag and stop_flag():
                print("[STOP] Đã dừng khi nhảy trang")
                browser.close()
                return []

            print(f"Đang bỏ qua TRANG {current_page}")
            if not click_next_or_scroll(page):
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

            # Report progress
            if progress_callback:
                progress_callback(current_page, f"Đang crawl trang {current_page}/{end_page}")

            items = extract_images(page, start_index=global_stt)
            print(f"Tìm thấy {len(items)} ảnh")

            all_items.extend(items)
            global_stt += len(items)

            if current_page == end_page:
                break

            if not click_next_or_scroll(page):
                print("[!] Không thấy trang tiếp theo hoặc không thể cuộn thêm.")
                break

            time.sleep(PAGE_WAIT)
            current_page += 1

        browser.close()

    return all_items


def run_crawler(start_page, end_page, target_url=TARGET_URL, stop_flag=None, progress_callback=None):
    items = crawl_pages(start_page, end_page, target_url=target_url, stop_flag=stop_flag, progress_callback=progress_callback)

    if stop_flag and stop_flag():
        print("[STOP] Dừng trước khi tải ảnh")
        return

    # Report downloading phase
    if progress_callback:
        progress_callback(end_page, "Tải ảnh...")

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