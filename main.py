import time
import queue
from sensor.ir_receiver import start_ir_thread, ir_queue
from display_manager import trigger_sensor_display

def main():
    
    # 1. Khởi tạo luồng bắt tín hiệu Remote IR
    start_ir_thread()
    
    try:
        # Vòng lặp chính đọc lệnh từ queue
        while True:
            try:
                # timeout = 1 để mỗi giây luồng chính có thể xử lý việc khác hoặc cho phép thoát KeyboardInterrupt dễ dàng
                button_pressed = ir_queue.get(timeout=1.0)
                print(f"[*] Nhận tín hiệu Remote: {button_pressed}")
                
                # Khi bấm phím 1
                if button_pressed == "1":
                    trigger_sensor_display()
            except queue.Empty:
                pass
            
    except KeyboardInterrupt:
        print("\n[!] Dọn dẹp ứng dụng, đang thoát...")
    except Exception as e:
        print(f"\n[!] Lỗi chưa xác định trên luồng chính: {e}")

if __name__ == "__main__":
    main()
