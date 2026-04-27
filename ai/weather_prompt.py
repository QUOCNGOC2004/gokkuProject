import threading

from ai.gemini_client import ask
from display.text_scroller import show_status, scroll_in_thread
from display.display_controller import trigger_sensor_display
from sensor.dht11_sensor import read_dht
from sensor.bmp180_sensor import read_bmp
from sensor.ldr_sensor import read_ldr
from sensor.pir_sensor import read_pir
from sensor.tilt_sensor import read_tilt

# Cờ chống gọi AI chồng chéo khi đang xử lý
_ai_running = False


def _build_prompt() -> str:
    """Đọc tất cả cảm biến và tạo prompt gửi Gemini."""
    t, h = read_dht()
    p = read_bmp()
    ldr = read_ldr()
    pir = read_pir()
    tilt = read_tilt()

    t_str = f"{t:.1f} C" if t is not None else "khong do duoc"
    h_str = f"{h:.0f} %" if h is not None else "khong do duoc"
    p_str = f"{p:.1f} Pa" if p is not None else "khong do duoc"
    ldr_str = f"{ldr * 100:.0f} %" if ldr is not None else "khong do duoc"
    pir_str = "Co nguoi" if pir else "Khong co nguoi"
    tilt_str = "Bi nghieng" if tilt else "Can bang"

    return f"""
Bạn là một trợ lý thông minh viết nội dung để hiển thị lên màn hình LCD 16x2.
Dữ liệu cảm biến hiện tại:
- Nhiệt độ: {t_str}
- Độ ẩm: {h_str}
- Áp suất: {p_str}
- Độ sáng môi trường: {ldr_str}
- Cảm biến chuyển động (PIR): {pir_str}
- Cảm biến nghiêng: {tilt_str}

Quy tắc bắt buộc:
1. Viết HOÀN TOÀN bằng tiếng Việt KHÔNG DẤU (không unicode, không ký tự đặc biệt).
2. Báo cáo chính xác TẤT CẢ các giá trị đo được (không bỏ qua cảm biến nào).
3. Đánh giá tổng thể thời tiết / môi trường dựa trên số liệu.
4. Kết thúc bằng 1 lời khuyên phù hợp với thời tiết / môi trường.
5. Viết liền mạch, không xuất hiện các ký tự đặc biệt, hashtag hay emoji.
"""


def _weather_task() -> None:
    """Toàn bộ tác vụ AI chạy trong daemon thread riêng — không block main thread."""
    global _ai_running

    show_status("Dang suy nghi..", "Cho ti nha...")

    prompt = _build_prompt()
    response = ask(prompt)

    if response:
        print(f"[AI] Nhan duoc {len(response)} ky tu, bat dau cuon LCD...")
        t = scroll_in_thread(response)
        if t:
            t.join()
    else:
        print("[AI] Fallback: hien du lieu cam bien tho.")
        t = trigger_sensor_display()
        if t:
            t.join()

    _ai_running = False


def show_weather() -> None:
    """
    Nut 1: Khoi dong _weather_task trong daemon thread rieng.
    - Main thread KHONG bi block trong khi cho Gemini.
    - Neu dang co tac vu AI chay → bo qua de chong xung dot.
    """
    global _ai_running

    if _ai_running:
        print("[AI] Dang xu ly, bo qua lenh.")
        return

    _ai_running = True
    threading.Thread(target=_weather_task, daemon=True).start()
