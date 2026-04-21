import time
import threading
from RPLCD.i2c import CharLCD
import config

# Import các hàm đọc từ package sensor
from sensor.dht11_sensor import read_dht
from sensor.bmp180_sensor import read_bmp
from sensor.ldr_sensor import read_ldr
from sensor.pir_sensor import read_pir
from sensor.tilt_sensor import read_tilt

try:
    lcd = CharLCD("PCF8574", config.I2C_ADDR, port=1, charmap="A00", cols=16, rows=2)
except Exception as e:
    print(f"[-] Không thể khởi tạo màn hình LCD I2C: {e}")
    lcd = None

# Trạng thái luồng
_is_displaying = False
_display_thread = None


def format_sensor_data():
    pages = []

    # 1. DHT11
    t, h = read_dht()
    t_str = f"Temp:{t} C" if t is not None else "Temp: ERR"
    h_str = f"Humid:{h} %" if h is not None else "Humid: ERR"
    pages.append([t_str[:16], h_str[:16]])

    # 2. BMP180
    p, t2 = read_bmp()
    p_str = f"Press:{p:.1f}Pa" if p is not None else "Press: ERR"
    t2_str = f"BMP_Tp:{t2:.1f} C" if t2 is not None else "BMP_Tp: ERR"
    pages.append([p_str[:16], t2_str[:16]])

    # 3. LDR & PIR
    ldr_val = read_ldr()
    pir_val = read_pir()
    ldr_str = f"LDR: {ldr_val:.2f}" if ldr_val is not None else "LDR: ERR"
    pir_str = (
        f"PIR: {'Co' if pir_val else 'Khong'}" if pir_val is not None else "PIR: ERR"
    )
    pages.append([ldr_str[:16], pir_str[:16]])

    # 4. TILT
    tilt_val = read_tilt()
    tilt_str = (
        f"Tilt: {'Nghieng' if tilt_val else 'Can Bang'}"
        if tilt_val is not None
        else "Tilt: ERR"
    )
    pages.append([tilt_str[:16], "".ljust(16)])

    return pages


def _display_loop():
    """
    Vòng lặp luồng: in lần lượt từng trang, sleep để lật trang theo config. PAGE_FLIP_SEC
    """
    global _is_displaying

    pages = format_sensor_data()

    for i, page in enumerate(pages):
        if not _is_displaying:
            break

        print(f"[LCD Page {i+1}/{len(pages)}] {page}")

        if lcd:
            try:
                lcd.clear()
                lcd.cursor_pos = (0, 0)
                lcd.write_string(page[0])
                lcd.cursor_pos = (1, 0)
                lcd.write_string(page[1])
            except Exception as e:
                print(f"[!] Lỗi ghi dữ liệu LCD I2C: {e}")

        # Sleep chia thành các chu kỳ nhỏ 0.1s để có thể dừng sớm nếu cần
        wait_steps = int(config.PAGE_FLIP_SEC * 10)
        for _ in range(wait_steps):
            if not _is_displaying:
                break
            time.sleep(0.1)

    # Sau khi chạy hết các trang, clear LCD
    if lcd:
        lcd.clear()

    # Giải phóng ngắt cờ hiển thị
    _is_displaying = False


def trigger_sensor_display():
    """
    Gắn vào callback của mắt IR. Hàm này khởi động 1 con thread chạy _display_loop
    một cách độc lập nhằm không chặn luồng hiện tại.
    """
    global _is_displaying, _display_thread

    # Chặn nếu màn hình vẫn đang cuộn để chống click nhiều lần
    if _is_displaying:
        print("[!] LCD đang xử lý hiển thị, bỏ qua lệnh nhận.")
        return

    _is_displaying = True
    print("[+] Bắt đầu tạo luồng cập nhật LCD...")
    _display_thread = threading.Thread(target=_display_loop, daemon=True)
    _display_thread.start()
