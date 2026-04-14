import threading

# TRẠNG THÁI CẢM BIẾN DÙNG CHUNG
sensor_data = {
    "temp": "Dang tai...",
    "hum": "Dang tai...",
    "press": "Dang tai...",
    "light": "Dang tai...",
    "tilt": "Binh thuong",
    "pir": "Khong co",
    "lcd_line1": "Khoi dong...",
    "lcd_line2": "He thong...",
}

# TRẠNG THÁI BẬN CỦA TỪNG MODULE ACTUATOR
led_busy = threading.Event()
servo_busy = threading.Event()
lcd_busy = threading.Event()

def mark_busy(*modules):
    """Đánh dấu các module là đang bận (gọi trước khi remote thực thi)."""
    for m in modules:
        m.set()

def mark_free(*modules):
    """Đánh dấu các module là rảnh (gọi sau khi remote hoàn tất)."""
    for m in modules:
        m.clear()
