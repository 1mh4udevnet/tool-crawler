from playwright.sync_api import sync_playwright
import time

TARGET_URL = "https://buavl.net/"


def extract_images(page):
    """Lấy link ảnh trên trang hiện tại"""
    images = set()
    for img in page.query_selector_all("img"):
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if src and src.startswith("http"):
            images.add(src)
    return images


def get_page_signature(page):
    """Dùng card đầu tiên làm dấu hiệu nhận biết trang đã đổi"""
    card = page.locator("div.card").first
    if card.count() == 0:
        return ""
    return card.inner_text()


def has_next_button(page):
    """Kiểm tra có nút NEXT (>) và chưa bị disabled"""
    next_btn = page.locator(
        "div.pagination button.page-btn >> i.fas.fa-chevron-right"
    ).locator("xpath=..")  # quay về button

    if next_btn.count() == 0:
        return False

    return not next_btn.first.is_disabled()


def click_next(page):
    """Click nút NEXT (>) và chờ nội dung đổi"""
    old_signature = get_page_signature(page)

    next_btn = page.locator(
        "div.pagination button.page-btn >> i.fas.fa-chevron-right"
    ).locator("xpath=..")

    if next_btn.count() == 0 or next_btn.first.is_disabled():
        return False

    next_btn.first.click()

    # chờ nội dung đổi (SPA)
    page.wait_for_function(
        """(oldText) => {
            const card = document.querySelector("div.card");
            return card && card.innerText !== oldText;
        }""",
        arg=old_signature,
        timeout=8000
    )

    time.sleep(0.5)
    return True


def crawl_pages(start_page, end_page):
    page_counts = {}
    total_images = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Mo trang: {TARGET_URL}")
        page.goto(TARGET_URL, timeout=60000)
        page.wait_for_selector("div.card", timeout=10000)

        current_page = 1

        # nhảy tới trang bắt đầu
        while current_page < start_page:
            if not click_next(page):
                print("Khong the nhay toi trang bat dau (het trang)")
                browser.close()
                return page_counts, total_images
            current_page += 1

        # crawl từ start → end
        while current_page <= end_page:
            print(f"\n=== Dang crawl TRANG {current_page} ===")

            images = extract_images(page)
            count = len(images)

            page_counts[current_page] = count
            total_images += count

            print(f"So anh: {count}")

            if current_page == end_page:
                break

            if not has_next_button(page):
                print("Khong con nut > (het trang)")
                break

            if not click_next(page):
                print("Click > that bai")
                break

            current_page += 1

        browser.close()

    return page_counts, total_images


if __name__ == "__main__":
    print("=== CRAWLER BUAVL.NET (MAP pagination.page-btn) ===")

    start_page = int(input("Nhap trang bat dau: "))
    end_page = int(input("Nhap trang ket thuc: "))

    if start_page > end_page:
        print("Trang bat dau phai <= trang ket thuc")
        exit(1)

    page_counts, total = crawl_pages(start_page, end_page)

    print("\n=== KET QUA ===")
    for p, c in page_counts.items():
        print(f"Trang {p}: {c} anh")

    print(f"\nTONG SO ANH: {total}")
    print("=== DONE ===")
