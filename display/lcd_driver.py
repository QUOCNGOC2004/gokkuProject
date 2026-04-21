from RPLCD.i2c import CharLCD
import config

# --- Khởi tạo phần cứng LCD ---
lcd = None
try:
    lcd = CharLCD(
        "PCF8574",
        config.I2C_ADDR,
        port=1,
        charmap="A00",
        cols=16,
        rows=2,
    )
    print("[HW] LCD I2C sẵn sàng.")
except Exception as e:
    print(f"[HW] Không thể khởi tạo LCD I2C: {e}")


def write_page(line0: str, line1: str) -> None:
    """Ghi 2 dòng lên màn hình LCD. Cắt chuỗi ở 16 ký tự nếu cần."""
    if lcd is None:
        return
    try:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line0[:16])
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line1[:16])
    except Exception as e:
        print(f"[!] Lỗi ghi dữ liệu LCD: {e}")


def clear() -> None:
    """Xóa màn hình LCD."""
    if lcd is None:
        return
    try:
        lcd.clear()
    except Exception as e:
        print(f"[!] Lỗi xóa LCD: {e}")
