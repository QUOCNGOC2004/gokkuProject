import time
import random
import threading
from gpiozero import RGBLED, Servo
import config

servo = Servo(
    config.SERVO_PIN,
    initial_value=None,
    min_pulse_width=0.5 / 1000,
    max_pulse_width=2.5 / 1000,
)
led = RGBLED(red=config.LED_R, green=config.LED_G, blue=config.LED_B)

BLINK_COLORS = [
    (1, 0, 0.5),
    (0, 1, 0.5),
    (0.5, 0, 1),
    (1, 0.5, 0),
    (0, 0.5, 1),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 0),
    (1, 0, 1),
    (0, 1, 1),
]

_led_color = (0.0, 0.0, 0.0)   # tuple float 0.0–1.0
_is_blinking = False
_blink_speed = 0.5              # giây
_led_state_on = False
_led_lock = threading.Lock()


def set_led_rgb(r: int, g: int, b: int):
    """Nhận màu từ Web (0–255), lưu vào trạng thái chung."""
    global _led_color
    with _led_lock:
        _led_color = (r / 255.0, g / 255.0, b / 255.0)


def set_blink(state: bool, speed: float = 0.5):
    """Bật/tắt nhấp nháy và đặt tốc độ (giây)."""
    global _is_blinking, _blink_speed
    with _led_lock:
        _is_blinking = state
        _blink_speed = max(0.05, speed)


def get_led_state():
    """Trả về dict trạng thái LED để Flask đọc."""
    with _led_lock:
        return {
            "color": _led_color,
            "is_blinking": _is_blinking,
            "blink_speed": _blink_speed,
        }


def led_loop():
    """
    Luồng ngầm quản lý LED nhấp nháy.
    Chạy bằng: threading.Thread(target=actuators.led_loop, daemon=True).start()
    """
    global _led_state_on
    last_blink_time = time.time()
    while True:
        now = time.time()
        with _led_lock:
            blinking = _is_blinking
            speed = _blink_speed
            color = _led_color

        if blinking:
            if now - last_blink_time >= speed:
                _led_state_on = not _led_state_on
                last_blink_time = now
                led.color = color if _led_state_on else (0, 0, 0)
        else:
            led.color = color

        time.sleep(0.05)


_servo_angle = 0        # góc hiện tại (0–180)
_servo_lock = threading.Lock()


def servo_to_value(angle: int) -> float:
    """Chuyển góc độ (0–180) sang giá trị Servo gpiozero (-1.0–1.0)."""
    angle = max(0, min(180, int(angle)))
    return (angle / 90.0) - 1.0


def servo_to_angle(target_angle: int):
    """
    Quay servo đến góc target_angle (0–180°) một cách chậm rãi.
    Thread-safe, blocking (gọi từ thread riêng khi cần).
    """
    global _servo_angle
    with _servo_lock:
        start = _servo_angle
        end = max(0, min(180, int(target_angle)))
        if start == end:
            return

        step = 1 if start < end else -1
        for angle in range(start, end + step, step):
            servo.value = servo_to_value(angle)

        time.sleep(0.2)
        servo.value = None   # detach
        _servo_angle = end


def get_servo_angle() -> int:
    return _servo_angle


def blink_short(flashes=4):
    for _ in range(flashes):
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.12)
        led.off()
        time.sleep(0.08)


def flash_long(duration=5):
    end = time.time() + duration
    while time.time() < end:
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.18)
    led.off()


def action_wave(times=3):
    for _ in range(times):
        servo.max()
        time.sleep(0.45)
        servo.min()
        time.sleep(0.45)
    servo.value = None


def turn_off():
    led.off()
    servo.value = None
