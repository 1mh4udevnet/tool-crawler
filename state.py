from playwright.sync_api import sync_playwright
import time

TARGET_URL = "https://buavl.net/"


def extract_images(page):
    """
    Lấy link ảnh trên trang hiện tại
    """
    images = set()
    for img in page.query_selector_all("img"):
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if src and src.startswith("http"):
            images.add(src)
    return images


def get_page_signature(page):
    """
    Dùng card đầu tiên làm dấu hiệu để biết trang đã đổi hay chưa
    """
    card = page.locator("div.card").first
    if card.count() == 0:
        return ""
    return card.inner_text()


def js_click_page(page, page_number):
    """
    Click phân trang bằng JavaScript (ổn định cho SPA)
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


def crawl_pages(start_page, end_page):
    """
    Crawl từ trang start_page → end_page
    """
    page_image_count = {}
    total_images = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Mo trang: {TARGET_URL}")
        page.goto(TARGET_URL, timeout=60000)
        page.wait_for_selector("div.card", timeout=10000)

        for page_num in range(start_page, end_page + 1):
            print(f"\n=== Dang crawl TRANG {page_num} ===")

            if page_num > 1:
                js_click_page(page, page_num)

            images = extract_images(page)
            count = len(images)

            page_image_count[page_num] = count
            total_images += count

            print(f"So anh trang {page_num}: {count}")

        browser.close()

    return page_image_count, total_images


if __name__ == "__main__":
    print("=== CRAWLER BUAVL.NET (NHAP TRANG THU CONG) ===")

    start_page = int(input("Nhap trang bat dau: "))
    end_page = int(input("Nhap trang ket thuc: "))

    if start_page > end_page:
        print("Loi: trang bat dau phai <= trang ket thuc")
        exit(1)

    page_counts, total = crawl_pages(start_page, end_page)

    print("\n=== KET QUA ===")
    for page, count in page_counts.items():
        print(f"Trang {page}: {count} anh")

    print(f"\nTONG SO ANH: {total}")
    print("=== DONE ===")
