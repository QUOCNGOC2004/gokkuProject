import board
import busio

# --- CẤU HÌNH CHUNG ---
AWAKE_TIME = 120.0
PAGE_FLIP_SEC = 2.0

# --- CẤU HÌNH CHÂN GPIO ---
I2C_ADDR = 0x27
DHT_PIN = board.D4
TILT_PIN = 5
PIR_PIN = 17
SERVO_PIN = 18
LED_R = 22
LED_G = 27
LED_B = 14
LDR_CHANNEL = 0

# --- KHỞI TẠO CHUNG ---
# Khởi tạo I2C bus chung cho cả LCD và BMP180
i2c_bus = busio.I2C(board.SCL, board.SDA)

# --- MÃ HỒNG NGOẠI ---
IR_BUTTONS = {
    "0xff30cf": "1",
    "0xff18e7": "2",
    "0xff7a85": "3",
}
