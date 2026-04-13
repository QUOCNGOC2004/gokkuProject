import sys
import time
import random
from select import select
import queue

import config
import display
import actuators
import sensors
import ir_receiver
import gokku


def ask_master_menu():
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

        # Bàn phím
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


def main():
    print("=" * 50)
    print("  Gokku System Interactive Online!")
    print("  Bam 1, 2, 3 tren Remote hoac Ban Phim.")
    print("=" * 50)

    display.lcd.clear()
    ir_receiver.start_ir_thread()
    is_sleeping = True

    while True:
        if sensors.pir.motion_detected and is_sleeping:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False
            gokku.miku_action_greet()
            gokku.say("Konnichiwa!\nGokku desu yo!", duration=4)

            while not is_sleeping:
                print("\n[SYS] Gokku dang cho lenh...")
                key_code = ask_master_menu()

                if key_code == "1":
                    gokku.show_weather()
                elif key_code == "2":
                    gokku.say(random.choice(gokku.IDLE_PHRASES), duration=3)
                elif key_code == "3":
                    gokku.say("Ryoukai! Ima\nte wo furu ne.", duration=2)
                    actuators.action_wave(times=2)
                elif key_code is None:
                    print("[LOG] Khong nhan duoc tin hieu. He thong nghi.")
                    gokku.say("Daremo inai.\nSuriipu shimasu.", duration=3)
                    is_sleeping = True
                    actuators.turn_off()
                    display.lcd.clear()

        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SYS] Tat he thong...")
        gokku.say("Sayounara!\nMata aou ne.", duration=2)
        actuators.turn_off()
        display.lcd.clear()
        print("[SYS] Hen gap lai!")
