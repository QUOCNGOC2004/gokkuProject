import time
import threading
from gpiozero import Servo

import config

# --- Cấu hình pulse width cho servo SG90 / MG996R ---
_MIN_PULSE = 0.5 / 1000  # 0.5ms
_MAX_PULSE = 2.5 / 1000  # 2.5ms

# --- Khởi tạo phần cứng servo ---
_servo: Servo | None = None
try:
    _servo = Servo(
        config.SERVO_PIN,
        initial_value=None,  # Không giật khi khởi động
        min_pulse_width=_MIN_PULSE,
        max_pulse_width=_MAX_PULSE,
    )
    print("[HW] Servo sẵn sàng.")
except Exception as e:
    print(f"[HW] Servo lỗi khởi tạo: {e}")

# --- Trạng thái nội bộ ---
_current_angle: int = 0  # Góc hiện tại (0–180)
_servo_lock = threading.Lock()


def angle_to_value(angle: int) -> float:
    """Chuyển góc (0–180°) → giá trị gpiozero Servo (-1.0 → 1.0)."""
    angle = max(0, min(180, int(angle)))
    return (angle / 90.0) - 1.0


def move_to(target_angle: int) -> None:
    """
    Quay servo đến góc target_angle (0–180°).
    Thread-safe, blocking.
    Sau khi đến đích sẽ detach (value=None) để chống rung/giật.
    """
    global _current_angle

    with _servo_lock:
        if _servo is None:
            return

        start = _current_angle
        end = max(0, min(180, int(target_angle)))

        if start == end:
            return

        step = 1 if start < end else -1
        for angle in range(start, end + step, step):
            _servo.value = angle_to_value(angle)
            # time.sleep(0.005)

        # Detach khi đến đích để ngăn rung/giật khi đứng im
        _servo.value = None
        _current_angle = end


def get_angle() -> int:
    """Trả về góc hiện tại của servo."""
    return _current_angle


def reset() -> None:
    """Detach servo ngay lập tức (dùng khi shutdown)."""
    if _servo:
        _servo.value = None
