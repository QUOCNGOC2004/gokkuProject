import time
import queue
from sensor.ir_receiver import start_ir_thread, ir_queue
from display import trigger_sensor_display
from servo import trigger_sweep, home, reset


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

                # Nút 1 → Hiển thị cảm biến lên LCD
                if button_pressed == "1":
                    trigger_sensor_display()

                # Nút 2 → Servo quay 0° → 180° → 0°
                elif button_pressed == "2":
                    trigger_sweep()

            except queue.Empty:
                pass

    except KeyboardInterrupt:
        print("\n[!] Dọn dẹp ứng dụng, đang thoát...")
        reset()   # Detach servo trước khi thoát
    except Exception as e:
        print(f"\n[!] Lỗi chưa xác định trên luồng chính: {e}")
        reset()


if __name__ == "__main__":
    main()
