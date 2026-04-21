import time
import adafruit_dht
import config

# Cố gắng khởi tạo DHT11, nếu cảm biến bị thiếu sẽ bắt lỗi
try:
    dht_device = adafruit_dht.DHT11(config.DHT_PIN)
except Exception as e:
    print(f"[-] Không thể khởi tạo DHT11: {e}")
    dht_device = None

def read_dht():
    """Đọc nhiệt độ và độ ẩm, trả về (temperature, humidity) hoặc (None, None)"""
    try:
        if dht_device is None:
            return None, None
        
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        return temperature, humidity
    except RuntimeError as error:
        # Lỗi đọc (ví dụ: miss tín hiệu) là bình thường với DHT, in ra lỗi nhưng không crash phần khác
        print(f"[!] DHT11 đọc lỗi (tạm thời): {error.args[0]}")
        return None, None
    except Exception as e:
        print(f"[-] Lỗi DHT11 (cảm biến có thể đã mất kết nối): {e}")
        return None, None
