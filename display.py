import time
import textwrap
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
    lcd.cursor_pos = (0, 0)
    lcd.write_string(r0.ljust(16)[:16])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(r1.ljust(16)[:16])


def display_text(text, total_duration=3.0):
    pages = _build_pages(text)
    lcd.clear()
    if len(pages) == 1:
        _write_page(*pages[0])
        time.sleep(total_duration)
    else:
        end_time = time.time() + total_duration
        idx = 0
        while time.time() < end_time:
            _write_page(*pages[idx])
            remaining = end_time - time.time()
            time.sleep(min(config.PAGE_FLIP_SEC, max(remaining, 0.05)))
            idx = (idx + 1) % len(pages)
    lcd.clear()


def get_pages(text):
    return _build_pages(text)


def write_direct(r0, r1):
    _write_page(r0, r1)
