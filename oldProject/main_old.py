import threading

import actuators
import display
import gokku
from web_app import app
from system_loops import sensor_loop, ir_keyboard_loop


def main():
    print("=" * 50)
    print("  Gokku Smart Hub — Web + Remote + Keyboard")
    print("=" * 50)

    # Thông báo khởi động lên LCD
    display.update_lcd("Gokku System", "Web Online!")

    # Khởi động 3 luồng daemon
    threading.Thread(target=sensor_loop, daemon=True, name="SensorLoop").start()
    threading.Thread(target=ir_keyboard_loop, daemon=True, name="IRKeyboard").start()
    threading.Thread(target=actuators.led_loop, daemon=True, name="LEDLoop").start()

    print("------------------------------------------")
    print("[OK] Web Dashboard: http://<IP_CUA_PI>:5000")
    print("[OK] Remote & Ban Phim: san sang")
    print("------------------------------------------")

    try:
        # Flask chạy ở main thread, reloader tắt để tránh khởi động luồng 2 lần
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\n[SYS] Tat he thong...")
        gokku.say("Sayounara!\nMata aou ne.", duration=2)
        actuators.turn_off()
        display.lcd.clear()
        print("[SYS] Hen gap lai!")


if __name__ == "__main__":
    main()
