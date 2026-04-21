import time
import queue
from sensor.ir_receiver import start_ir_thread, ir_queue
from display import show_status, scroll_in_thread
from ai import show_weather
from servo import trigger_sweep, home, reset
from led import cycle_next, turn_off as led_off


def main():

    # 1. Ép servo về 0° khi khởi động (đề phòng còn dở góc từ lần trước)
    home()

    # 2. Khởi tạo luồng bắt tín hiệu Remote IR
    start_ir_thread()

    try:
        # Vòng lặp chính đọc lệnh từ queue
        while True:
            try:
                # timeout = 1s để KeyboardInterrupt có thể ngắt dễ dàng
                button_pressed = ir_queue.get(timeout=1.0)
                print(f"[*] Nhận tín hiệu Remote: {button_pressed}")

                # Nút 1 → Gọi Gemini AI đọc thời tiết, fallback sang dữ liệu thô nếu lỗi
                if button_pressed == "1":
                    show_weather()

                # Nút 2 → Servo quay 0° → 180° → 0°
                elif button_pressed == "2":
                    trigger_sweep()

                # Nút 3 → Xoay vòng LED: RED → GREEN → BLUE → OFF
                elif button_pressed == "3":
                    cycle_next()

            except queue.Empty:
                pass

    except KeyboardInterrupt:
        print("\n[!] Dọn dẹp ứng dụng, đang thoát...")
        reset()    # Detach servo
        led_off()  # Tắt LED
    except Exception as e:
        print(f"\n[!] Lỗi chưa xác định trên luồng chính: {e}")
        reset()
        led_off()


if __name__ == "__main__":
    main()
