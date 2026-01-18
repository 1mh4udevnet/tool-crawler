from playwright.sync_api import sync_playwright
import time

TARGET_URL = "https://buavl.net/"

START_PAGE = 1   # trang bắt đầu
END_PAGE = 5     # trang kết thúc


def extract_images(page):
    """
    Lấy toàn bộ link ảnh trên trang hiện tại
    """
    images = set()
    for img in page.query_selector_all("img"):
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if src and src.startswith("http"):
            images.add(src)
    return images


def get_page_signature(page):
    """
    Lấy dấu hiệu để biết trang đã thay đổi hay chưa
    (card đầu tiên)
    """
    card = page.locator("div.card").first
    if card.count() == 0:
        return ""
    return card.inner_text()


def js_click_page(page, page_number):
    """
    Click phân trang bằng JavaScript (CHUẨN SPA)
    """
    print(f"→ Tu dong click TRANG {page_number}")

    old_signature = get_page_signature(page)

    clicked = page.evaluate(
        """(pageNum) => {
            const links = document.querySelectorAll("ul.pagination a.page-link");
            for (const a of links) {
                if (a.textContent.trim() === String(pageNum)) {
                    a.click();
                    return true;
                }
            }
            return false;
        }""",
        page_number
    )

    if not clicked:
        raise RuntimeError(f"Khong tim thay nut trang {page_number}")

    # Chờ nội dung đổi (SPA)
    page.wait_for_function(
        """(oldText) => {
            const card = document.querySelector("div.card");
            return card && card.innerText !== oldText;
        }""",
        old_signature,
        timeout=10000
    )

    time.sleep(0.5)  # chờ render ổn định


def crawl_by_pagination(url):
    all_results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Mo trang: {url}")
        page.goto(url, timeout=60000)
        page.wait_for_selector("div.card", timeout=10000)

        for page_num in range(START_PAGE, END_PAGE + 1):
            print(f"\n=== Dang crawl TRANG {page_num} ===")

            if page_num > 1:
                js_click_page(page, page_num)

            images = extract_images(page)
            print(f"Tim thay {len(images)} anh")

            # in thử 3 ảnh đầu
            for i, img in enumerate(list(images)[:3], start=1):
                print(f"  {i}. {img}")

            all_results[page_num] = images

        browser.close()

    return all_results


if __name__ == "__main__":
    print("=== CRAWLER BUAVL.NET (SPA PAGINATION) ===")
    print(f"START_PAGE = {START_PAGE}")
    print(f"END_PAGE   = {END_PAGE}")

    results = crawl_by_pagination(TARGET_URL)

    total = sum(len(v) for v in results.values())
    print(f"\nTONG CONG ANH LAY DUOC: {total}")

    print("=== DONE ===")
