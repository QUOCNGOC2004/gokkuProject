import sys
import time
import random
import threading
import textwrap
import subprocess
import queue
from select import select
from gpiozero import MotionSensor, RGBLED, Servo, MCP3008, DigitalInputDevice
from RPLCD.i2c import CharLCD
import board
import busio
import bmp180
import adafruit_dht

# ══════════════════════════════════════════════════════════════
#  CẤU HÌNH
# ══════════════════════════════════════════════════════════════

AWAKE_TIME = 120.0  # 120 giây (2 phút) chờ tín hiệu IR
I2C_ADDR = 0x27
DHT_PIN = board.D4
TILT_PIN = 5  # Chân DO của cảm biến nghiêng nối vào GPIO 5
PAGE_FLIP_SEC = 2.0  # Thời gian mỗi trang LCD

# --- TỪ ĐIỂN MÃ HỒNG NGOẠI (Chuẩn NEC của bạn) ---
IR_BUTTONS = {
    "0xff30cf": "1",
    "0xff18e7": "2",
    "0xff7a85": "3",
    # Bạn có thể thêm các mã khác vào đây sau
}

# ══════════════════════════════════════════════════════════════
#  KHỞI TẠO PHẦN CỨNG
# ══════════════════════════════════════════════════════════════

i2c = busio.I2C(board.SCL, board.SDA)
lcd = CharLCD(
    i2c_expander="PCF8574",
    address=I2C_ADDR,
    port=1,
    cols=16,
    rows=2,
    charmap="A02",
    auto_linebreaks=False,
)
pir = MotionSensor(17)
servo = Servo(
    18, initial_value=None, min_pulse_width=0.5 / 1000, max_pulse_width=2.5 / 1000
)
led = RGBLED(red=22, green=27, blue=14)

# --- Các cảm biến khác ---
dht_device = None
try:
    dht_device = adafruit_dht.DHT11(DHT_PIN, use_pulseio=False)
    print("[HW] DHT11 san sang.")
except Exception as e:
    print(f"[HW] DHT11 loi: {e}")

bmp_sensor = None
try:
    bmp_sensor = bmp180.BMP180(i2c)
    print("[HW] BMP180 san sang.")
except Exception as e:
    print(f"[HW] BMP180 loi: {e}")

light_sensor = None
try:
    light_sensor = MCP3008(channel=0)
    print("[HW] MCP3008 (LDR) san sang.")
except Exception as e:
    print(f"[HW] MCP3008 loi: {e}")

tilt_sensor = None
try:
    tilt_sensor = DigitalInputDevice(TILT_PIN)
    print("[HW] Tilt Sensor san sang.")
except Exception as e:
    print(f"[HW] Tilt Sensor loi: {e}")


# ══════════════════════════════════════════════════════════════
#  LUỒNG ĐỌC HỒNG NGOẠI NGẦM (BYPASS LỖI EVDEV)
# ══════════════════════════════════════════════════════════════
ir_queue = queue.Queue()  # Hàng đợi chứa nút bấm


def decode_nec(pulse_space_list):
    values = [
        abs(int(x)) for x in pulse_space_list if x.startswith("+") or x.startswith("-")
    ]
    start_idx = -1
    for i in range(len(values) - 1):
        if values[i] > 8000 and values[i + 1] > 4000:
            start_idx = i + 2
            break
        elif values[i] > 8000 and 2000 < values[i + 1] < 3000:
            return "REPEAT"

    if start_idx == -1 or len(values) < start_idx + 64:
        return None

    binary_str = ""
    for i in range(start_idx, start_idx + 64, 2):
        space = values[i + 1]
        binary_str += "1" if space > 1000 else "0"

    if len(binary_str) == 32:
        return hex(int(binary_str, 2))
    return None


def ir_reader_thread():
    cmd = ["ir-ctl", "-r"]
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        )
        buffer = []
        for line in iter(process.stdout.readline, ""):
            parts = line.strip().split()
            buffer.extend(parts)
            if buffer and buffer[-1].startswith("-") and int(buffer[-1]) <= -10000:
                hex_code = decode_nec(buffer)
                if hex_code and hex_code != "REPEAT":
                    if hex_code in IR_BUTTONS:
                        # Đẩy tên nút (1, 2, 3...) vào hàng đợi
                        ir_queue.put(IR_BUTTONS[hex_code])
                buffer = []
    except Exception as e:
        print(f"[IR] Loi luong doc hong ngoai: {e}")


# Khởi động luồng đọc IR chạy ngầm song song với chương trình chính
threading.Thread(target=ir_reader_thread, daemon=True).start()
print("[HW] IR Receiver (Custom Decoder) san sang.")


# ══════════════════════════════════════════════════════════════
#  ĐỌC CẢM BIẾN
# ══════════════════════════════════════════════════════════════


def read_dht11():
    if dht_device is None:
        return None, None
    for _ in range(3):
        try:
            t = dht_device.temperature
            h = dht_device.humidity
            if t is not None and h is not None:
                return t, h
        except:
            pass
        time.sleep(2.0)
    return None, None


def read_bmp180():
    if bmp_sensor is None:
        return None
    try:
        return bmp_sensor.pressure
    except:
        return None


def read_light():
    if light_sensor is None:
        return None
    try:
        val = light_sensor.value
        return val if val >= 0.02 else None
    except:
        return None


def read_tilt():
    if tilt_sensor is None:
        return None
    try:
        return tilt_sensor.value
    except:
        return None


# ══════════════════════════════════════════════════════════════
#  HIỂN THỊ LCD & ĐÈN/SERVO
# ══════════════════════════════════════════════════════════════


def _build_pages(text):
    lines = []
    for raw in text.split("\n"):
        raw = raw.strip()
        if not raw:
            continue
        if len(raw) > 16:
            lines.extend(textwrap.wrap(raw, 16))
        else:
            lines.append(raw)
    if not lines:
        lines = [""]
    pages = []
    for i in range(0, len(lines), 2):
        r0 = lines[i]
        r1 = lines[i + 1] if i + 1 < len(lines) else ""
        pages.append((r0, r1))
    return pages


def _write_page(r0, r1):
    lcd.cursor_pos = (0, 0)
    lcd.write_string(r0.ljust(16)[:16])
    lcd.cursor_pos = (1, 0)
    lcd.write_string(r1.ljust(16)[:16])


def display_text(text, total_duration=3.0):
    pages = _build_pages(text)
    lcd.clear()
    if len(pages) == 1:
        _write_page(*pages[0])
        time.sleep(total_duration)
    else:
        end_time = time.time() + total_duration
        idx = 0
        while time.time() < end_time:
            _write_page(*pages[idx])
            remaining = end_time - time.time()
            time.sleep(min(PAGE_FLIP_SEC, max(remaining, 0.05)))
            idx = (idx + 1) % len(pages)
    lcd.clear()


BLINK_COLORS = [
    (1, 0, 0.5),
    (0, 1, 0.5),
    (0.5, 0, 1),
    (1, 0.5, 0),
    (0, 0.5, 1),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 0),
    (1, 0, 1),
    (0, 1, 1),
]


def _led_blink_short(flashes=4):
    for _ in range(flashes):
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.12)
        led.off()
        time.sleep(0.08)


def _led_flash_long(duration=5):
    end = time.time() + duration
    while time.time() < end:
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.18)
    led.off()


def say(text, duration=3.0):
    threading.Thread(target=_led_blink_short, daemon=True).start()
    display_text(text, total_duration=duration)


def action_wave(times=3):
    for _ in range(times):
        servo.max()
        time.sleep(0.45)
        servo.min()
        time.sleep(0.45)
    servo.value = None


def miku_action_greet():
    threading.Thread(target=_led_flash_long, args=(5,), daemon=True).start()
    threading.Thread(target=action_wave, args=(3,), daemon=True).start()


# ══════════════════════════════════════════════════════════════
#  BÁO CÁO THỜI TIẾT
# ══════════════════════════════════════════════════════════════


def show_weather():
    say("Chotto matte!\nKeisokuchuu...", duration=2)
    t, h = read_dht11()
    if t is not None and h is not None:
        say(f"Ima no kion\n{t:.1f} do C", duration=3)
        say(f"Ima no shitsudo\n{h:.0f} paasento", duration=3)
        if t >= 35:
            say("Atsui desu!!\nKi wo tsukete.", duration=3)
            say("Heya de suzunde\nkudasai ne.", duration=3)
            say("Geemu demo shite\nasobimashou!", duration=3)
        elif t >= 30:
            say("Mushiatsui ne.\nKi wo tsukete.", duration=3)
            say("Eakon wo tsukete\nmizu nonde ne.", duration=3)
        elif t >= 25:
            say("Kion ga ii ne.\nKaiteki desu.", duration=3)
            say("Kyou mo 1nichi\nganbatte ne!", duration=3)
        elif t >= 20:
            say("Sukoshi samui ga\nkimochi ii ne.", duration=3)
            say("Uwagi wo motte\nitte kudasai ne.", duration=3)
        elif t >= 15:
            say("Samui desu yo!\nKi wo tsukete.", duration=3)
            say("Atsugi shite ne.\nKaze hikanaide.", duration=3)
        else:
            say("Kion ga hikui!\nTotemo samui!", duration=3)
            say("Chiba no kaze ga\ntsumetai desu!", duration=3)
            say("Atatakaku shite\ndekakete ne!", duration=3)

        if h >= 80:
            say("Shitsudo takai!\nJimejime shiteru", duration=3)
            say("Joshitsu moodo\nni shite ne.", duration=3)
        elif h >= 60:
            say("Shitsudo seijou.\nKuuki ga ii ne.", duration=3)
        elif h < 40:
            say("Kansou shiteru.\nKi wo tsukete.", duration=3)
            say("Mizu wo takusan\nnonde kudasai!", duration=3)
    else:
        say("Sensa eraa:\nKion, Shitsudo", duration=3)

    say("Tsugi wa kiatsu\nwo hakarimasu!", duration=2)
    press = read_bmp180()
    if press is not None:
        say(f"Kiatsu wa\n{press:.1f} hPa", duration=3)
        if press < 990:
            say("Teikiatsu desu!\nAme furu kamo.", duration=3)
            say("Inage Eki ni wa\nkasa motte ne!", duration=3)
        elif press < 1000:
            say("Kiatsu hikume.\nKumori kamo.", duration=3)
            say("Ame furanai to\nii desu ne.", duration=3)
        elif press <= 1015:
            say("Kiatsu seijou.\nKaiteki desu ne.", duration=3)
            say("Kyou no tenki wa\nsubarashii desu.", duration=3)
        elif press <= 1025:
            say("Koukiatsu desu!\nHaremasu yo.", duration=3)
            say("Sanpo ni iku no\nmo ii desu ne.", duration=3)
        else:
            say("Kiatsu totemo\ntakai desu!", duration=3)
            say("Soto de asobu\nno ni saiteki!", duration=3)
    else:
        say("Sensa eraa:\nKiatsu...", duration=3)

    say("Akarusa wo\nchekku chuu!", duration=2)
    light_val = read_light()
    if light_val is not None:
        percent = light_val * 100
        say(f"Akarusa wa ima\n{percent:.0f} paasento", duration=3)
        if percent >= 50:
            say("Akarukute ii ne!\nSaikou desu.", duration=3)
            say("Shigoto ganbatte\nkudasai ne!", duration=3)
        else:
            say("Sukoshi kurai!\nMe ni warui yo.", duration=3)
            say("Denki wo tsukete\nshigoto shite ne", duration=3)
    else:
        say("Sensa eraa:\nAkarusa...", duration=3)

    say("Katamuki sensa\nchekku chuu...", duration=2)
    tilt_val = read_tilt()
    if tilt_val is not None:
        if tilt_val == 1:
            say("Keikoku!!!\nTaorete imasu!", duration=3)
            say("Oki basho wo\nchekku shite!", duration=3)
        else:
            say("Anzen desu.\nKatamuki nashi.", duration=3)
    else:
        say("Gomen, katamuki\nsensa eraa desu.", duration=3)
        say("Setsuzoku wo\nchekku shite.", duration=3)

    say("Houkoku subete\nkanryou shita!", duration=3)


IDLE_PHRASES = [
    "Konnichiwa,\nGokku desu!",
    "Yoi ichinichi wo\nsugoshite ne!",
    "Suibun hokyuu wo\nwasurenaide ne.",
    "1 jikan goto ni\nkyuukei shite!",
    "Oshigoto no\nchoushi wa dou?",
    "Geemu shite\nikinuki shiyou!",
    "Nanika tetsudai\nmashou ka?",
    "Zutto suwarazu\nundou shite ne.",
    "Subete junchou\nni ugoite iru!",
    "Deeta no hozon\nwasurenaide ne!",
    "Kyou wa totemo\nii hi desu ne.",
    "Gokku wa itsumo\nkokoni iru yo!",
    "Ohiruyasumi no\njikan desu ka?",
    "Muri shinaide\nganbatte ne!",
    "Gogo wa kafe ni\nikimashou ka?",
    "Yoku ganbatte\nimasu ne. Sugoi!",
    "Egao wo wasure\nnaide kudasai!",
    "Ii tenki dakara\nsanpo ni ikou!",
    "Shokuji wa jikan\ndoori ni ne.",
    "Itsumo ganbatte\nkurete arigatou!",
    "Mokuhyou wa\ntassei shita?",
    "Gokku wa anata\nwo ouen shiteru!",
    "Sutoresu wo\ntamenaide ne!",
    "Shigoto no meeru\nchekku shite ne!",
]


# ══════════════════════════════════════════════════════════════
#  HÀM TƯƠNG TÁC (ĐÃ SỬA LẠI ĐỂ ĐỌC QUEUE)
# ══════════════════════════════════════════════════════════════
def ask_master_menu():
    menu_text = "Konnichiwa! Nani\nwo shimasu ka?\n1.Tenki\n2.Oshaberi\n3.Aisatsu"
    pages = _build_pages(menu_text)

    start_time = time.time()
    page_idx = 0
    last_flip = 0.0

    while time.time() - start_time < AWAKE_TIME:
        now = time.time()
        if now - last_flip >= PAGE_FLIP_SEC:
            lcd.clear()
            _write_page(*pages[page_idx])
            page_idx = (page_idx + 1) % len(pages)
            last_flip = now

        # 1. Kiểm tra Bàn phím (Terminal)
        r, _, _ = select([sys.stdin], [], [], 0.1)
        if r and sys.stdin in r:
            user_input = sys.stdin.readline().strip()
            if user_input in ["1", "2", "3"]:
                print(f"[KBD] Nhan phim tu ban phim: {user_input}")
                return user_input

        # 2. Kiểm tra Remote Hồng Ngoại (Từ Queue)
        try:
            ir_input = ir_queue.get_nowait()  # Đọc xem có nút nào được bấm không
            if ir_input in ["1", "2", "3"]:
                print(f"[IR] Nhan phim tu Remote: {ir_input}")
                return ir_input
        except queue.Empty:
            pass  # Nếu không có ai bấm remote thì bỏ qua

    return None


# ══════════════════════════════════════════════════════════════
#  VÒNG LẶP CHÍNH
# ══════════════════════════════════════════════════════════════


def main():
    print("=" * 50)
    print("  Gokku System Interactive Online!")
    print("  Bam 1, 2, 3 tren Remote hoac Ban Phim.")
    print("=" * 50)
    lcd.clear()

    is_sleeping = True

    while True:
        if pir.motion_detected and is_sleeping:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False

            miku_action_greet()
            say("Konnichiwa!\nGokku desu yo!", duration=4)

            while not is_sleeping:
                print("\n[SYS] Gokku dang cho lenh...")
                key_code = ask_master_menu()  # Trả về chuỗi '1', '2', hoặc '3'

                if key_code == "1":
                    print("[CMD] Chon chuc nang 1: Thoi tiet")
                    show_weather()

                elif key_code == "2":
                    print("[CMD] Chon chuc nang 2: Tro chuyen")
                    phrase = random.choice(IDLE_PHRASES)
                    say(phrase, duration=3)

                elif key_code == "3":
                    print("[CMD] Chon chuc nang 3: Quay Servo")
                    say("Ryoukai! Ima\nte wo furu ne.", duration=2)
                    action_wave(times=2)

                elif key_code is None:
                    print("[LOG] Khong nhan duoc tin hieu. He thong nghi.")
                    say("Daremo inai.\nSuriipu shimasu.", duration=3)
                    say("Ichiji teishi.\nSayounara!", duration=3)
                    say("Mata ne!\nYonde kudasai.", duration=3)

                    is_sleeping = True
                    led.off()
                    lcd.clear()

        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SYS] Tat he thong...")
        say("Sayounara!\nMata aou ne.", duration=2)
        led.off()
        servo.value = None
        lcd.clear()
        print("[SYS] Hen gap lai!")
