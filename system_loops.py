import time
import queue

import config
import display
import actuators
import sensors
import ir_receiver
import gokku
import shared_state

# Sentinel trả về khi chế độ điều khiển thay đổi từ bên trong menu
_MODE_CHANGED = "MODE_CHANGED"

# --- TRẠNG THÁI LED CYCLE ---
_led_cycle_state = 0      # 0=OFF  1=RED  2=GREEN  3=BLUE
_last_button3_time = 0.0  # Timestamp lần bấm nút 3 gần nhất (debounce)

_LED_COLORS = [
    (0,   0,   0),    # 0: OFF
    (255, 0,   0),    # 1: RED
    (0,   255, 0),    # 2: GREEN
    (0,   0,   255),  # 3: BLUE
]
_LED_LABELS = ["OFF", "DO (RED)", "XANH LA (GREEN)", "XANH DUONG (BLUE)"]


def _handle_led_cycle():
    """
    Nút 3: chu kỳ màu LED OFF → RED → GREEN → BLUE → OFF.
    Chỉ hoạt động ở Remote Mode, có debounce 1 giây.
    """
    global _led_cycle_state, _last_button3_time
    if not shared_state.remote_control_mode:
        return  # Web Mode: nút 3 bị khóa
    now = time.time()
    if now - _last_button3_time < 1.0:
        return  # Debounce: bỏ qua nếu bấm quá nhanh
    _last_button3_time = now
    _led_cycle_state = (_led_cycle_state + 1) % 4
    r, g, b = _LED_COLORS[_led_cycle_state]
    actuators.set_blink(False)       # Tắt chế độ nhấp nháy trước khi đặt màu
    actuators.set_led_rgb(r, g, b)
    print(f"[LED] Mau: {_LED_LABELS[_led_cycle_state]}")


def _handle_toggle_mode():
    """
    Nút 4: chuyển Remote Mode ↔ Web Mode.
    Hoạt động ở mọi trạng thái (ngủ, menu, đang chờ).
    """
    shared_state.remote_control_mode = not shared_state.remote_control_mode
    if shared_state.remote_control_mode:
        display.update_lcd("Remote Mode", "Web Locked")
        print("[MODE] -> Remote Mode (Web bi khoa)")
    else:
        actuators.turn_off()         # Tắt LED + detach servo trước khi trả quyền web
        display.update_lcd("Web Mode", "Remote Locked")
        print("[MODE] -> Web Mode (Remote bi khoa)")


def _run_gokku_action(key_code: str):
    """
    Thực thi hành động Gokku theo mã phím 1/2.
    Tự động bỏ qua nếu không ở Remote Mode.
    """
    if not shared_state.remote_control_mode:
        return  # Web Mode: bỏ qua lệnh remote

    if key_code == "1":
        gokku.show_weather()

    elif key_code == "2":
        gokku.say("Ryoukai! Ima\nte wo furu ne.", duration=2)
        actuators.action_wave(times=2)


def sensor_loop():
    """Luồng daemon: đọc 5 cảm biến mỗi 2 giây, ghi vào shared_state."""
    while True:
        try:
            t, h = sensors.read_dht11()
            if t is not None:
                shared_state.sensor_data["temp"] = f"{t:.1f} C"
            if h is not None:
                shared_state.sensor_data["hum"] = f"{h:.0f} %"
        except Exception:
            pass

        try:
            press = sensors.read_bmp180()
            if press is not None:
                shared_state.sensor_data["press"] = f"{press:.1f} hPa"
        except Exception:
            pass

        try:
            light_val = sensors.read_light()
            if light_val is not None:
                shared_state.sensor_data["light"] = f"{light_val * 100:.0f} %"
        except Exception:
            pass

        try:
            tilt_val = sensors.read_tilt()
            if tilt_val is not None:
                shared_state.sensor_data["tilt"] = "BI DO!" if tilt_val == 1 else "An toan"
        except Exception:
            pass

        try:
            shared_state.sensor_data["pir"] = "Co nguoi!" if sensors.pir.motion_detected else "Khong"
        except Exception:
            pass

        time.sleep(2.0)


def ask_master_menu():
    """
    Hiện menu trên LCD, chờ input từ remote hồng ngoại.
    Trả về: "1" | "2" | _MODE_CHANGED | None (timeout)
    """
    menu_text = "Konnichiwa! Nani\nwo shimasu ka?\n1.Tenki\n2.Aisatsu"
    pages = display.get_pages(menu_text)

    start_time = time.time()
    page_idx = 0
    last_flip = 0.0

    while time.time() - start_time < config.AWAKE_TIME:
        # Thoát ngay nếu mode đã chuyển sang Web (do nút 4 từ bên ngoài)
        if not shared_state.remote_control_mode:
            return _MODE_CHANGED

        now = time.time()
        if now - last_flip >= config.PAGE_FLIP_SEC:
            display.lcd.clear()
            display.write_direct(*pages[page_idx])
            page_idx = (page_idx + 1) % len(pages)
            last_flip = now

        # Đọc Remote Hồng Ngoại
        try:
            ir_input = ir_receiver.ir_queue.get_nowait()
            if ir_input in ["1", "2"]:
                return ir_input
            elif ir_input == "3":
                _handle_led_cycle()
            elif ir_input == "4":
                _handle_toggle_mode()
                return _MODE_CHANGED    # Thoát menu ngay sau khi đổi mode
        except queue.Empty:
            pass

        time.sleep(0.1)

    return None


def ir_keyboard_loop():
    """
    Luồng daemon: xử lý Remote Hồng Ngoại + PIR.

    Máy trạng thái:
      - Sleeping (is_sleeping=True) : chờ PIR phát hiện người.
      - Awake   (is_sleeping=False) : hiển thị menu, nhận lệnh, thực thi.
    Nút 4 hoạt động ở cả 2 trạng thái.
    """
    print("[SYS] Gokku dang cho lenh (Remote Mode)...")
    ir_receiver.start_ir_thread()
    is_sleeping = True

    while True:
        # ── NÚT 4: luôn hoạt động kể cả khi ngủ ──────────────────────────
        try:
            ir_input = ir_receiver.ir_queue.get_nowait()
            if ir_input == "4":
                _handle_toggle_mode()
                is_sleeping = True      # Reset về sleeping sau mỗi lần đổi mode
        except queue.Empty:
            pass

        # ── PIR + MENU: chỉ chạy khi ở Remote Mode ───────────────────────
        if sensors.pir.motion_detected and is_sleeping and shared_state.remote_control_mode:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False

            gokku.gokku_action_greet()
            gokku.say("Konnichiwa!\nGokku desu yo!", duration=4)

            while not is_sleeping:
                print("\n[SYS] Gokku dang cho lenh...")
                key_code = ask_master_menu()

                if key_code in ["1", "2"]:
                    _run_gokku_action(key_code)

                elif key_code is None:
                    # Timeout 120s: không có ai tương tác → ngủ
                    print("[LOG] Khong nhan duoc tin hieu. He thong nghi.")
                    gokku.say("Daremo inai.\nSuriipu shimasu.", duration=3)
                    is_sleeping = True
                    actuators.turn_off()
                    display.lcd.clear()

                elif key_code == _MODE_CHANGED:
                    # Nút 4 bấm trong lúc đang ở menu → thoát về sleeping
                    print("[MODE] Thoat menu do doi mode.")
                    is_sleeping = True
                    # LCD đã được cập nhật bởi _handle_toggle_mode()

        time.sleep(0.1)
