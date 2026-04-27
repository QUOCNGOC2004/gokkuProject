import time
import threading

import config
from display.lcd_driver import write_page, clear
from display.page_formatter import format_sensor_pages

# --- Trạng thái nội bộ của luồng hiển thị ---
_is_displaying = False
_display_thread: threading.Thread | None = None


def _display_loop() -> None:
    """
    Vòng lặp chạy trong thread riêng:
    - Lấy danh sách trang từ page_formatter
    - Lần lượt ghi từng trang lên LCD
    - Sleep theo config.PAGE_FLIP_SEC (chia nhỏ 0.1s để dừng sớm khi cần)
    - Xóa màn hình khi kết thúc
    """
    global _is_displaying

    pages = format_sensor_pages()

    for i, page in enumerate(pages):
        if not _is_displaying:
            break

        print(f"[LCD Page {i + 1}/{len(pages)}] {page}")
        write_page(page[0], page[1])

        # Chờ theo PAGE_FLIP_SEC, kiểm tra mỗi 0.1s để cho phép dừng sớm
        wait_steps = int(config.PAGE_FLIP_SEC * 10)
        for _ in range(wait_steps):
            if not _is_displaying:
                break
            time.sleep(0.1)

    clear()
    _is_displaying = False


def trigger_sensor_display() -> threading.Thread | None:
    """
    Kích hoạt hiển thị dữ liệu cảm biến trên LCD.
    Khởi động một thread daemon độc lập chạy _display_loop.
    Bỏ qua nếu màn hình đang trong quá trình hiển thị.
    """
    global _is_displaying, _display_thread

    if _is_displaying:
        print("[!] LCD đang xử lý hiển thị, bỏ qua lệnh nhận.")
        return None

    _is_displaying = True
    print("[+] Bắt đầu tạo luồng cập nhật LCD...")
    _display_thread = threading.Thread(target=_display_loop, daemon=True)
    _display_thread.start()
    return _display_thread
