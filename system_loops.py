import sys
import time
import random
import queue
from select import select

import config
import display
import actuators
import sensors
import ir_receiver
import gokku
import shared_state

def _run_gokku_action(key_code: str):
    """
    Thực thi hành động Gokku theo mã phím 1/2/3.
    """
    if key_code == "1":
        shared_state.mark_busy(shared_state.led_busy, shared_state.lcd_busy)
        try:
            gokku.show_weather()
        finally:
            shared_state.mark_free(shared_state.led_busy, shared_state.lcd_busy)

    elif key_code == "2":
        shared_state.mark_busy(shared_state.led_busy, shared_state.lcd_busy)
        try:
            gokku.ai_oshaberi()
        finally:
            shared_state.mark_free(shared_state.led_busy, shared_state.lcd_busy)

    elif key_code == "3":
        shared_state.mark_busy(shared_state.led_busy, shared_state.lcd_busy, shared_state.servo_busy)
        try:
            gokku.say("Ryoukai! Ima\nte wo furu ne.", duration=2)
            actuators.action_wave(times=2)
        finally:
            shared_state.mark_free(shared_state.led_busy, shared_state.lcd_busy, shared_state.servo_busy)


def sensor_loop():
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
    """Hiện menu menu trên LCD, chờ input từ remote/bàn phím."""
    menu_text = "Konnichiwa! Nani\nwo shimasu ka?\n1.Tenki\n2.Oshaberi\n3.Aisatsu"
    pages = display.get_pages(menu_text)

    start_time = time.time()
    page_idx = 0
    last_flip = 0.0

    while time.time() - start_time < config.AWAKE_TIME:
        now = time.time()
        if now - last_flip >= config.PAGE_FLIP_SEC:
            display.lcd.clear()
            display.write_direct(*pages[page_idx])
            page_idx = (page_idx + 1) % len(pages)
            last_flip = now

        # Bàn phím số
        r, _, _ = select([sys.stdin], [], [], 0.1)
        if r and sys.stdin in r:
            user_input = sys.stdin.readline().strip()
            if user_input in ["1", "2", "3"]:
                return user_input

        # Remote Hồng Ngoại
        try:
            ir_input = ir_receiver.ir_queue.get_nowait()
            if ir_input in ["1", "2", "3"]:
                return ir_input
        except queue.Empty:
            pass

    return None


def ir_keyboard_loop():
    """
    Luồng ngầm xử lý remote + bàn phím.
    """
    print("[SYS] Gokku dang cho lenh (remote + ban phim)...")
    ir_receiver.start_ir_thread()
    is_sleeping = True

    while True:
        if sensors.pir.motion_detected and is_sleeping:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False

            shared_state.mark_busy(shared_state.led_busy, shared_state.servo_busy, shared_state.lcd_busy)
            try:
                gokku.miku_action_greet()
                gokku.say("Konnichiwa!\nGokku desu yo!", duration=4)
            finally:
                shared_state.mark_free(shared_state.led_busy, shared_state.servo_busy, shared_state.lcd_busy)

            while not is_sleeping:
                print("\n[SYS] Gokku dang cho lenh...")
                key_code = ask_master_menu()

                if key_code in ["1", "2", "3"]:
                    _run_gokku_action(key_code)

                elif key_code is None:
                    print("[LOG] Khong nhan duoc tin hieu. He thong nghi.")
                    shared_state.mark_busy(shared_state.led_busy, shared_state.lcd_busy)
                    try:
                        gokku.say("Daremo inai.\nSuriipu shimasu.", duration=3)
                    finally:
                        shared_state.mark_free(shared_state.led_busy, shared_state.lcd_busy)
                    is_sleeping = True
                    actuators.turn_off()
                    display.lcd.clear()

        time.sleep(0.1)
