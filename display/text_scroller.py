import time
import textwrap
import threading
from typing import List, Tuple

import config
from display.lcd_driver import write_page, clear


def build_pages(text: str) -> List[Tuple[str, str]]:
    """
    Tách văn bản dài thành danh sách trang (line0, line1).
    Mỗi dòng tối đa 16 ký tự.
    """
    lines: List[str] = []
    for raw in text.replace("\n", "  ").split("  "):
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


def show_status(line0: str, line1: str = "") -> None:
    """Hiển thị thông báo ngắn tức thì lên LCD (không block)."""
    write_page(line0[:16], line1[:16])


def scroll_text(text: str, total_duration: float) -> None:
    """
    Cuộn nhiều trang văn bản trên LCD trong total_duration giây.
    Blocking — nên gọi từ thread riêng.
    """
    pages = build_pages(text)
    clear()

    if not pages:
        return

    if len(pages) == 1:
        write_page(pages[0][0], pages[0][1])
        time.sleep(total_duration)
    else:
        end_time = time.time() + total_duration
        idx = 0
        while time.time() < end_time:
            write_page(pages[idx][0], pages[idx][1])
            remaining = end_time - time.time()
            time.sleep(min(config.PAGE_FLIP_SEC, max(remaining, 0.05)))
            idx = (idx + 1) % len(pages)

    clear()


def scroll_in_thread(text: str, total_duration: float | None = None) -> None:
    """
    Wrapper non-blocking: chạy scroll_text trong daemon thread riêng.
    Nếu total_duration=None thì tự tính dựa theo độ dài văn bản.
    """
    if total_duration is None:
        total_duration = max(5.0, (len(text) / 32.0) * 5.0) + 4.0

    threading.Thread(
        target=scroll_text,
        args=(text, total_duration),
        daemon=True,
    ).start()
