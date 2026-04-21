from bmp180 import bmp180
import config

try:
    # Mặc định thư viện sử dụng I2C (SMBus) địa chỉ 0x77
    bmp = bmp180(0x77)
except Exception as e:
    print(f"[-] Không thể khởi tạo BMP180: {e}")
    bmp = None

def read_bmp():
    """Đọc áp suất và nhiệt độ từ BMP180, trả về (pressure, temperature) hoặc (None, None)"""
    try:
        if bmp is None:
            return None, None
        
        # Hàm lấy giá trị phụ thuộc vào thư viện bmp180 (thường có get_pressure, get_temp)
        pressure = bmp.get_pressure()
        temperature = bmp.get_temp()
        return pressure, temperature
    except Exception as e:
        print(f"[-] Lỗi đọc BMP180 (Cảm biến có thể bị tháo rời): {e}")
        return None, None
