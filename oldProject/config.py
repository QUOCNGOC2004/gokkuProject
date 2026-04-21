import board
import busio
import os
from dotenv import load_dotenv

load_dotenv()

# --- CẤU HÌNH CHUNG ---
AWAKE_TIME = 120.0
PAGE_FLIP_SEC = 2.0

# --- GEMINI AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


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
    "0xffa25d": "CH-",        "0xff629d": "CH",        "0xffe21d": "CH+",
    "0xff22dd": "PREV",       "0xff02fd": "NEXT",      "0xffc23d": "PLAY/PAUSE",
    "0xffe01f": "VOL-",       "0xffa857": "VOL+",      "0xff906f": "EQ",
    "0xff6897": "0",          "0xff9867": "100+",      "0xffb04f": "200+",
    "0xff30cf": "1",          "0xff18e7": "2",         "0xff7a85": "3",
    "0xff10ef": "4",          # Nút 4 → Toggle Remote/Web Mode
    "0xff38c7": "5",          "0xff5aa5": "6",
    "0xff42bd": "7",          "0xff4ab5": "8",         "0xff52ad": "9",
}
