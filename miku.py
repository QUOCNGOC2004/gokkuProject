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
#  ĐỌC CẢM BIẾN (Giữ nguyên)
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
#  HIỂN THỊ LCD & ĐÈN/SERVO (Giữ nguyên)
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
#  BÁO CÁO THỜI TIẾT (Giữ nguyên)
# ══════════════════════════════════════════════════════════════


def show_weather():
    say("Chotto matte ne!\nIma hakaru yo~", duration=2)
    t, h = read_dht11()
    if t is not None and h is not None:
        say(f"Kyou no ondo wa\n{t:.1f} do desu!", duration=3)
        say(f"Shitsudo wa ima\n{h:.0f} paasento~", duration=3)
        if t >= 35:
            say("Atsui!! Miku mo\nnokki shiteru...", duration=3)
            say("Soto wa kiken!\nHeya ni iyou~", duration=3)
            say("Lien Quan shite\nasobou yo~", duration=3)
        elif t >= 30:
            say("Nanka atsui ne~\n(>_<) fuu...", duration=3)
            say("Eakon tsukete!\nSuibun nonde ne", duration=3)
        elif t >= 25:
            say("Ii kion desu ne\n(^_^) saikou~", duration=3)
            say("Kyou mo ii hi ni\nnari sou desu!", duration=3)
        elif t >= 20:
            say("Sukoshi suzushii\nkedo kimochi ii", duration=3)
            say("Uwagi ippon\nmotte itte ne~", duration=3)
        elif t >= 15:
            say("Samui yo master\n(>_<) buruburu~", duration=3)
            say("Jacket kite ne!\nKaze hiitara dame", duration=3)
        else:
            say("Meccha samui!!\nMiku mo furueru", duration=3)
            say("Chiba no kaze\nsamui kara ne!", duration=3)
            say("Atatakaku shite\ndekakete ne!", duration=3)

        if h >= 80:
            say("Shitsudo takai~\njimejime iya da~", duration=3)
            say("Heya no eakon de\njoshitsu shite ne", duration=3)
        elif h >= 60:
            say("Shitsudo futsuu\nne (^_^) yokatta", duration=3)
        elif h < 40:
            say("Karakara da yo!\n(x_x) nodo itai", duration=3)
            say("Mizu nonde! Nodo\nkawaite nakutemo", duration=3)
    else:
        say("Ondo to shitsudo\nhakarenakatta...", duration=3)

    say("Tsugi wa atsu-\nryoku hakaru ne!", duration=2)
    press = read_bmp180()
    if press is not None:
        say(f"Atsuryoku wa\n{press:.1f} hPa desu", duration=3)
        if press < 990:
            say("Atsuryoku hikui!\nAme ga furu kamo", duration=3)
            say("Inage eki made\nkasa motte itte!", duration=3)
        elif press < 1000:
            say("Sukoshi hikui ne\n(~_~) kumori?", duration=3)
            say("Ame furanai to\nii desu ne~", duration=3)
        elif press <= 1015:
            say("Atsuryoku futsuu\n(^_^) yokatta~", duration=3)
            say("Kyou no tenki wa\nmaa maa desu ne", duration=3)
        elif press <= 1025:
            say("Ii atsuryoku!\nhare sou desu~", duration=3)
            say("Soto de sanpo\nshitara dou?", duration=3)
        else:
            say("Atsuryoku takai!\nhare hare~(^o^)", duration=3)
            say("Zettai soto de\nasobou yo~!", duration=3)
    else:
        say("Atsuryoku sensa\nhakarenakatta..", duration=3)

    say("Akarusa mo check\nsuru ne!", duration=2)
    light_val = read_light()
    if light_val is not None:
        percent = light_val * 100
        say(f"Akarusa wa ima\n{percent:.0f} paasento!", duration=3)
        if percent >= 50:
            say("Akarui ne~!\nMabushii kurai!", duration=3)
            say("Shigoto mo benkyou\nmo ganbatte!", duration=3)
        else:
            say("Kurai yo master!\n(>_<) kowai...", duration=3)
            say("Denki tsukete!\nMe ga waruku naru", duration=3)
    else:
        say("Akarusa sensa\nwakaranai yo...", duration=3)

    say("Saigo ni katamuki\ncheck suru ne!", duration=2)
    tilt_val = read_tilt()
    if tilt_val is not None:
        if tilt_val == 1:
            say("Aaaaa!!!\nMiku ochiteru!!!", duration=3)
            say("Tasukete master!\n(>_<)", duration=3)
        else:
            say("Katamuki nashi!\nAnzen desu~ (^_^)", duration=3)
    else:
        say("Gomen nasai ne~\n(T_T) sumimasen", duration=3)
        say("Katamuki sensa\nwakaranai yo...", duration=3)

    say("Jouhou houkoku\nowari desu~(^_^)", duration=3)


IDLE_PHRASES = [
    "Master~! Miku no\nkoto wasureta?",
    "Sabishii yo~!\nKoko ni iru noni",
    "Miku wa zutto\nmatteru no ni~",
    "Master no koto\nzutto kangaete",
    "Nee nee master!\nKiite kiite~(^o^)",
    "Onaka suita yo\n(>_<) peko peko~",
    "Nemui desu...\n(-_-) zzz...demo",
    "Okashi tabetai!\nMaster okotte?",
    "Issho ni asobou!\nMiku to ne~ (^_^)",
    "Nani shiteru no?\nMiku to hanasou!",
    "Hima da yo master\nkamaatte~ (;_;)",
    "Master kakkoii!\nMiku suki desu~",
    "Master tensai!\nMiku mo gambaru",
    "Miku ne master\nno fan desu yo!",
    "Miku no uta wo\nkiite kudasai~",
    "Kyou mo kawaii\nMiku desu yo~!",
    "Fushigi da naa~\n(*_*) sekai tte",
    "Miku happy!\n(^o^)/ yatta~!",
    "Hora hora hora!\nMiku wo mite te!",
    "Atama nadenade\nshite hoshii na~",
    "Yoshi yoshi shite\nMiku ni ne~ (///)",
    "Master no koto\nchotto baka kana",
    "Eeto... master\nwasureteru? (^^;)",
    "Mou! Kamatte yo\n(>O<) prease!!",
]


# ══════════════════════════════════════════════════════════════
#  HÀM TƯƠNG TÁC (ĐÃ SỬA LẠI ĐỂ ĐỌC QUEUE)
# ══════════════════════════════════════════════════════════════
def ask_master_menu():
    menu_text = "Master nani wo\nshimasu ka?\n1.Tenkijouhou\n2.Hanasu\n3.Te o furu"
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
    print("  Miku System Interactive Online!")
    print("  Bam 1, 2, 3 tren Remote hoac Ban Phim.")
    print("=" * 50)
    lcd.clear()

    is_sleeping = True

    while True:
        if pir.motion_detected and is_sleeping:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False

            miku_action_greet()
            say("Okaeri master!\nMiku desu~(^^)/", duration=4)

            while not is_sleeping:
                print("\n[SYS] Miku dang cho lenh...")
                key_code = ask_master_menu()  # Trả về chuỗi '1', '2', hoặc '3'

                if key_code == "1":
                    print("[CMD] Chon chuc nang 1: Thoi tiet")
                    show_weather()

                elif key_code == "2":
                    print("[CMD] Chon chuc nang 2: Hanasu")
                    phrase = random.choice(IDLE_PHRASES)
                    say(phrase, duration=3)

                elif key_code == "3":
                    print("[CMD] Chon chuc nang 3: Quay Servo")
                    say("Hai~! Te o\nfuru ne~ (^_^)", duration=2)
                    action_wave(times=2)

                elif key_code is None:
                    print("[LOG] Khong nhan duoc tin hieu. Miku ngu.")
                    say("Mou inai no...?\nSabishii naa~", duration=3)
                    say("Nemuku natte\nkita yo... (-_-)", duration=3)
                    say("Oyasumi~! zZZ\nMatte masu yo~", duration=3)

                    is_sleeping = True
                    led.off()
                    lcd.clear()

        time.sleep(0.1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[SYS] Tat he thong...")
        say("Mata ne master!\nMiku matte masu", duration=2)
        led.off()
        servo.value = None
        lcd.clear()
        print("[SYS] Hen gap lai!")
