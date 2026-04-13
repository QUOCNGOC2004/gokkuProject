import time
import textwrap
import threading
from RPLCD.i2c import CharLCD
import config

# Khởi tạo LCD
lcd = CharLCD(
    i2c_expander="PCF8574",
    address=config.I2C_ADDR,
    port=1,
    cols=16,
    rows=2,
    charmap="A02",
    auto_linebreaks=False,
)

# ============================================================
# TRẠNG THÁI LCD (dùng chung với Flask Web)
# ============================================================
lcd_line1 = "Khoi dong..."
lcd_line2 = "He thong..."
_lcd_lock = threading.Lock()


def update_lcd(line1: str, line2: str = ""):
    """
    Cập nhật 2 dòng LCD vật lý VÀ cập nhật biến trạng thái
    để Flask có thể đọc và hiển thị lên web.
    Thread-safe.
    """
    global lcd_line1, lcd_line2
    with _lcd_lock:
        lcd_line1 = line1
        lcd_line2 = line2
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line1.ljust(16)[:16])
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2.ljust(16)[:16])


def get_lcd_state():
    """Trả về dict trạng thái LCD để Flask đọc."""
    with _lcd_lock:
        return {"lcd_line1": lcd_line1, "lcd_line2": lcd_line2}


# ============================================================
# CÁC HÀM GỐC (giữ nguyên, thêm cập nhật state)
# ============================================================
def _build_pages(text):
    lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        if len(raw) > 16:
            lines.extend(textwrap.wrap(raw, 16))
        else:
            lines.append(raw)
    if not lines:
        lines = [""]

    pages = []
    for i in range(0, len(lines), 2):
        r0 = lines[i]
        r1 = lines[i + 1] if i + 1 < len(lines) else ""
        pages.append((r0, r1))
    return pages


def _write_page(r0, r1):
    """Ghi trực tiếp ra LCD (không cập nhật state — dùng nội bộ)."""
    lcd.cursor_pos = (0, 0)
    lcd.write_string(r0.ljust(16)[:16])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(r1.ljust(16)[:16])


def display_text(text, total_duration=3.0):
    """
    Hiển thị nhiều trang trên LCD trong total_duration giây.
    Cập nhật trạng thái state ở mỗi lần flip trang.
    """
    global lcd_line1, lcd_line2
    pages = _build_pages(text)
    with _lcd_lock:
        lcd.clear()

    if len(pages) == 1:
        with _lcd_lock:
            lcd_line1, lcd_line2 = pages[0][0], pages[0][1]
            _write_page(*pages[0])
        time.sleep(total_duration)
    else:
        end_time = time.time() + total_duration
        idx = 0
        while time.time() < end_time:
            with _lcd_lock:
                lcd_line1, lcd_line2 = pages[idx][0], pages[idx][1]
                _write_page(*pages[idx])
            remaining = end_time - time.time()
            time.sleep(min(config.PAGE_FLIP_SEC, max(remaining, 0.05)))
            idx = (idx + 1) % len(pages)

    with _lcd_lock:
        lcd.clear()
        lcd_line1 = ""
        lcd_line2 = ""


def get_pages(text):
    return _build_pages(text)


def write_direct(r0, r1):
    """Ghi trực tiếp 2 dòng (dùng cho menu ask_master_menu)."""
    global lcd_line1, lcd_line2
    with _lcd_lock:
        lcd_line1 = r0
        lcd_line2 = r1
        _write_page(r0, r1)
