from gpiozero import RGBLED
import config

# --- Khởi tạo phần cứng RGB LED ---
led: RGBLED | None = None
try:
    led = RGBLED(
        red=config.LED_R,
        green=config.LED_G,
        blue=config.LED_B,
    )
    print("[HW] RGB LED sẵn sàng.")
except Exception as e:
    print(f"[HW] RGB LED lỗi khởi tạo: {e}")


# Bảng màu chuẩn (giá trị 0.0–1.0)
COLORS = {
    "RED":   (1.0, 0.0, 0.0),
    "GREEN": (0.0, 1.0, 0.0),
    "BLUE":  (0.0, 0.0, 1.0),
    "OFF":   (0.0, 0.0, 0.0),
}


def set_color(r: float, g: float, b: float) -> None:
    """Đặt màu LED theo giá trị 0.0–1.0."""
    if led is None:
        return
    try:
        led.color = (r, g, b)
    except Exception as e:
        print(f"[!] Lỗi set màu LED: {e}")


def turn_off() -> None:
    """Tắt LED."""
    if led is None:
        return
    try:
        led.off()
    except Exception as e:
        print(f"[!] Lỗi tắt LED: {e}")
