from gpiozero import DigitalInputDevice
import config

try:
    # DigitalInputDevice sẽ cung cấp is_active cho high/low
    tilt = DigitalInputDevice(config.TILT_PIN)
except Exception as e:
    print(f"[-] Không thể khởi tạo cảm biến độ nghiêng Tilt: {e}")
    tilt = None

def read_tilt():
    """Trả về True nếu nghiêng (kích hoạt), False nếu cân bằng, hoặc None nếu lỗi"""
    try:
        if tilt is None:
            return None
        return tilt.is_active
    except Exception as e:
        print(f"[-] Lỗi đọc tín hiệu cảm biến Tilt: {e}")
        return None
