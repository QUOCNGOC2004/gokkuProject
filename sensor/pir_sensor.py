from gpiozero import MotionSensor
import config

try:
    pir = MotionSensor(config.PIR_PIN)
except Exception as e:
    print(f"[-] Không thể khởi tạo cảm biến chuyển động PIR: {e}")
    pir = None

def read_pir():
    """Trả về True nếu phát hiện chuyển động, False nếu không, hoặc None nếu lỗi"""
    try:
        if pir is None:
            return None
        return pir.motion_detected
    except Exception as e:
        print(f"[-] Lỗi đọc tính hiệu PIR: {e}")
        return None
