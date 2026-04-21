from typing import List

from sensor.dht11_sensor import read_dht
from sensor.bmp180_sensor import read_bmp
from sensor.ldr_sensor import read_ldr
from sensor.pir_sensor import read_pir
from sensor.tilt_sensor import read_tilt


def format_sensor_pages() -> List[List[str]]:
    """
    Đọc dữ liệu từ tất cả cảm biến và trả về danh sách các trang LCD.
    Mỗi trang là [dòng_trên, dòng_dưới], mỗi chuỗi tối đa 16 ký tự.
    """
    pages = []

    # Trang 1 — DHT11: nhiệt độ & độ ẩm
    t, h = read_dht()
    t_str = f"Temp:{t} C" if t is not None else "Temp: ERR"
    h_str = f"Humid:{h} %" if h is not None else "Humid: ERR"
    pages.append([t_str[:16], h_str[:16]])

    # Trang 2 — BMP180: áp suất khí quyển
    p = read_bmp()
    p_str = f"Press:{p:.1f}Pa" if p is not None else "Press: ERR"
    pages.append([p_str[:16], "".ljust(16)])

    # Trang 3 — LDR & PIR: ánh sáng & chuyển động
    ldr_val = read_ldr()
    pir_val = read_pir()
    ldr_str = f"LDR: {ldr_val:.2f}" if ldr_val is not None else "LDR: ERR"
    pir_str = (
        f"PIR: {'Co' if pir_val else 'Khong'}"
        if pir_val is not None
        else "PIR: ERR"
    )
    pages.append([ldr_str[:16], pir_str[:16]])

    # Trang 4 — Tilt: trạng thái nghiêng
    tilt_val = read_tilt()
    tilt_str = (
        f"Tilt: {'Nghieng' if tilt_val else 'Can Bang'}"
        if tilt_val is not None
        else "Tilt: ERR"
    )
    pages.append([tilt_str[:16], "".ljust(16)])

    return pages
