import threading

from servo.servo_driver import move_to, get_angle

# --- Trạng thái điều phối ---
_is_running = False
_action_thread: threading.Thread | None = None
_lock = threading.Lock()


def _sweep_action() -> None:
    """
    Chuỗi hành động quay servo khi bấm nút 2:
    1. Quay từ 0° → 180°
    2. Quay ngược 180° → 0°
    3. Detach tự động do servo_driver.move_to() xử lý
    """
    global _is_running

    print("[Servo] Bắt đầu quay 0° → 180°...")
    move_to(180)

    print("[Servo] Quay ngược 180° → 0°...")
    move_to(0)

    print("[Servo] Hoàn thành, servo đã detach.")
    with _lock:
        _is_running = False


def trigger_sweep() -> None:
    """
    Kích hoạt chuỗi quay 0→180→0 trong một thread daemon riêng.
    Bỏ qua nếu servo đang chạy để tránh xung đột.
    """
    global _is_running, _action_thread

    with _lock:
        if _is_running:
            print("[Servo] Đang chạy, bỏ qua lệnh.")
            return
        _is_running = True

    print("[Servo] Khởi động luồng quay servo...")
    _action_thread = threading.Thread(target=_sweep_action, daemon=True)
    _action_thread.start()


def home() -> None:
    """
    Ép servo về 0° khi khởi động chương trình.
    Nếu đã ở 0° thì bỏ qua.
    """
    if get_angle() != 0:
        print(f"[Servo] Đưa về vị trí 0° (đang ở {get_angle()}°)...")
        move_to(0)
    else:
        print("[Servo] Đã ở vị trí 0°, bỏ qua home.")
