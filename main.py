import sys
import time
import random
import threading
import queue
from select import select

from flask import Flask, jsonify, request, render_template_string

import config
import display
import actuators
import sensors
import ir_receiver
import gokku

# ============================================================
# FLASK APP
# ============================================================
app = Flask(__name__)

# ============================================================
# TRẠNG THÁI CẢM BIẾN DÙNG CHUNG (Flask + sensor_loop)
# ============================================================
sensor_data = {
    "temp": "Dang tai...",
    "hum": "Dang tai...",
    "press": "Dang tai...",
    "light": "Dang tai...",
    "tilt": "Binh thuong",
    "pir": "Khong co",
    "lcd_line1": "Khoi dong...",
    "lcd_line2": "He thong...",
}

# Cờ báo Gokku đang thực thi (tránh gọi chồng chéo từ remote)
gokku_busy = False
_gokku_lock = threading.Lock()

# Cờ báo remote đang thức (đang trong menu chờ lệnh hoặc đang thực thi lệnh từ remote)
# Khi True, web KHÔNG được điều khiển LED/Servo/LCD
remote_active = False
_remote_lock = threading.Lock()

# ============================================================
# GIAO DIỆN WEB (HTML/CSS/JS — giữ nguyên từ app.py gốc)
# ============================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gokku Web Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; text-align: center; background-color: #1e1e1e; color: #fff; margin: 0; padding: 20px;}
        .container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; max-width: 1200px; margin: 0 auto;}
        .box { background: #2d2d2d; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); width: 320px; position: relative; text-align: left;}
        h1 { color: #00d2ff; }
        h2 { font-size: 18px; color: #aaa; margin-top: 0; border-bottom: 1px solid #444; padding-bottom: 10px;}

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .data-item { background: #222; padding: 15px; border-radius: 8px; text-align: center; }
        .data-label { font-size: 12px; color: #888; }
        .data-val { font-size: 24px; font-weight: bold; margin-top: 5px; }
        .val-temp { color: #ff6b6b; } .val-hum { color: #4cd137; } .val-press { color: #fbc531; } .val-light { color: #00d2ff; }
        .val-alert { color: #e84118; animation: blink 1s infinite;}

        @keyframes blink { 50% { opacity: 0; } }

        .lcd-screen { background: #004400; color: #55ff55; font-family: 'Courier New', Courier, monospace; font-size: 22px; font-weight: bold; padding: 15px; border-radius: 5px; border: 4px solid #111; box-shadow: inset 0 0 10px #000; letter-spacing: 2px; }

        input[type=range] { width: 100%; margin: 10px 0; }
        button { background: #00d2ff; color: #000; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; transition: 0.2s; width: 100%;}
        button:hover { background: #00a8cc; }

        .slider-label { display: flex; justify-content: space-between; font-size: 14px;}
        #r_input { accent-color: #ff4c4c; } #g_input { accent-color: #4cff4c; } #b_input { accent-color: #4c4cff; }
        #mau_preview { height: 40px; background-color: rgb(0,0,0); border-radius: 8px; margin-bottom: 15px; border: 2px solid #555;}
        .blink-panel { margin-top: 15px; background: #333; padding: 15px; border-radius: 8px;}

        /* Thông báo bận (remote đang hoạt động) */
        .busy-toast { display: none; position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: #e84118; color: #fff; font-weight: bold; padding: 12px 28px;
            border-radius: 10px; font-size: 15px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); z-index: 9999;
            animation: fadeInUp 0.3s ease; }
        @keyframes fadeInUp { from { opacity:0; transform: translateX(-50%) translateY(20px); } to { opacity:1; transform: translateX(-50%) translateY(0); } }
        .status-label { font-size: 12px; color: #f39c12; min-height: 16px; margin-top: 6px; text-align: center; }
        </style>
</head>
<body>
    <h1>🚀 Gokku Smart Hub</h1>
    <div class="container">

        <div class="box">
            <h2>🌍 Môi trường</h2>
            <div class="grid-2">
                <div class="data-item"><div class="data-label">Nhiệt độ</div><div class="data-val val-temp" id="t_temp">--</div></div>
                <div class="data-item"><div class="data-label">Độ ẩm</div><div class="data-val val-hum" id="t_hum">--</div></div>
                <div class="data-item"><div class="data-label">Áp suất</div><div class="data-val val-press" id="t_press">--</div></div>
                <div class="data-item"><div class="data-label">Ánh sáng</div><div class="data-val val-light" id="t_light">--</div></div>
            </div>
        </div>

        <div class="box">
            <h2>🛡️ Trạng thái &amp; Màn hình LCD</h2>
            <div class="grid-2" style="margin-bottom: 15px;">
                <div class="data-item"><div class="data-label">Nghiêng đổ</div><div class="data-val" id="t_tilt">--</div></div>
                <div class="data-item"><div class="data-label">Chuyển động</div><div class="data-val" id="t_pir">--</div></div>
            </div>
            <div class="data-label" style="margin-bottom: 5px;">Màn hình thiết bị đang hiện:</div>
            <div class="lcd-screen">
                <div id="lcd1">Khởi động...</div>
                <div id="lcd2">Vui lòng đợi</div>
            </div>

            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <input type="text" id="custom_text" placeholder="Gửi tin nhắn lên LCD" style="flex: 1; padding: 8px; border-radius: 5px; border: none;">
                <button style="width: auto; padding: 8px 15px;" onclick="guiLCD()">Gửi</button>
            </div>
        </div>

        <div class="box">
            <h2>💡 Điều khiển Đèn RGB</h2>
            <div id="mau_preview"></div>
            <div class="slider-label"><span>Đỏ (R):</span><span id="r_val">0</span></div>
            <input type="range" id="r_input" min="0" max="255" value="0" oninput="capNhatLed()">
            <div class="slider-label"><span>Xanh (G):</span><span id="g_val">0</span></div>
            <input type="range" id="g_input" min="0" max="255" value="0" oninput="capNhatLed()">
            <div class="slider-label"><span>Dương (B):</span><span id="b_val">0</span></div>
            <input type="range" id="b_input" min="0" max="255" value="0" oninput="capNhatLed()">

            <div class="blink-panel">
                <label style="cursor: pointer; display: block; margin-bottom: 10px;">
                    <input type="checkbox" id="blink_toggle" onchange="capNhatBlink()"> 🌟 Bật Nhấp Nháy
                </label>
                <div class="slider-label"><span>Tốc độ:</span><span id="speed_val">0.5s</span></div>
                <input type="range" id="blink_speed" min="0.05" max="2.0" step="0.05" value="0.5" oninput="capNhatBlink()">
            </div>
            <div class="status-label" id="led_status"></div>
        </div>

        <div class="box">
            <h2>⚙️ Động Cơ Servo</h2>
            <div style="text-align: center; font-size: 32px; color: #00d2ff; font-weight: bold; margin: 20px 0;" id="goc_hien_thi">0°</div>
            <input type="range" id="goc_input" min="0" max="180" value="0" oninput="document.getElementById('goc_hien_thi').innerText = this.value + '°'">
            <button onclick="quayServo()">Thực thi quay</button>
            <div id="trang_thai_servo" style="color: #4cd137; text-align: center; margin-top: 10px; height: 20px;"></div>
        </div>

    </div>

    <!-- Toast thông báo bận -->
    <div class="busy-toast" id="busy_toast">⚠️ Remote đang hoạt động — Không thể điều khiển ngay lúc này!</div>

    <script>
        let _busyTimer = null;
        function showBusy() {
            let toast = document.getElementById('busy_toast');
            toast.style.display = 'block';
            clearTimeout(_busyTimer);
            _busyTimer = setTimeout(() => { toast.style.display = 'none'; }, 3000);
        }

        function handleBusy(res, onOk) {
            res.json().then(d => {
                if (d.status === 'busy') { showBusy(); }
                else if (onOk) onOk(d);
            });
        }

        function quayServo() {
            let goc = document.getElementById('goc_input').value;
            document.getElementById('trang_thai_servo').innerText = "Đang quay...";
            fetch('/api/servo?goc=' + goc).then(r => handleBusy(r, d => {
                document.getElementById('trang_thai_servo').innerText = d.message;
                setTimeout(() => document.getElementById('trang_thai_servo').innerText="", 2000);
            }));
        }

        function capNhatLed() {
            let r = document.getElementById('r_input').value;
            let g = document.getElementById('g_input').value;
            let b = document.getElementById('b_input').value;
            document.getElementById('r_val').innerText = r;
            document.getElementById('g_val').innerText = g;
            document.getElementById('b_val').innerText = b;
            document.getElementById('mau_preview').style.backgroundColor = `rgb(${r},${g},${b})`;
            fetch(`/api/led?r=${r}&g=${g}&b=${b}`).then(r => handleBusy(r, d => {
                document.getElementById('led_status').innerText = '';
            }));
        }

        function capNhatBlink() {
            let is_blink = document.getElementById('blink_toggle').checked;
            let speed = document.getElementById('blink_speed').value;
            document.getElementById('speed_val').innerText = speed + "s";
            fetch(`/api/blink?state=${is_blink}&speed=${speed}`).then(r => handleBusy(r));
        }

        function guiLCD() {
            let text = document.getElementById('custom_text').value;
            fetch('/api/lcd?text=' + encodeURIComponent(text)).then(r => handleBusy(r, d => {
                document.getElementById('custom_text').value = '';
            }));
        }

        function quetCamBien() {
            fetch('/api/status').then(r=>r.json()).then(data => {
                document.getElementById('t_temp').innerText = data.temp;
                document.getElementById('t_hum').innerText = data.hum;
                document.getElementById('t_press').innerText = data.press;
                document.getElementById('t_light').innerText = data.light;

                let tiltEl = document.getElementById('t_tilt');
                tiltEl.innerText = data.tilt;
                if(data.tilt === "BI DO!") tiltEl.className = "data-val val-alert"; else tiltEl.className = "data-val val-hum";

                let pirEl = document.getElementById('t_pir');
                pirEl.innerText = data.pir;
                if(data.pir === "Co nguoi!") pirEl.className = "data-val val-temp"; else pirEl.className = "data-val val-hum";

                document.getElementById('lcd1').innerHTML = (data.lcd_line1 || "").replace(/ /g, '&nbsp;');
                document.getElementById('lcd2').innerHTML = (data.lcd_line2 || "").replace(/ /g, '&nbsp;');
            });
        }
        setInterval(quetCamBien, 1000);
        quetCamBien();
    </script>
</body>
</html>
"""

# ============================================================
# FLASK ROUTES
# ============================================================
@app.route('/')
def trang_chu():
    return render_template_string(HTML_PAGE)


@app.route('/api/status')
def api_status():
    # Lấy thêm trạng thái LCD từ display module
    lcd_state = display.get_lcd_state()
    return jsonify({**sensor_data, **lcd_state})


@app.route('/api/servo')
def api_servo():
    with _remote_lock:
        if remote_active:
            return jsonify({"status": "busy", "message": "Remote dang hoat dong"})
    goc_dich = request.args.get('goc', default=0, type=int)
    # Chạy trong thread riêng để Flask không bị blocking
    threading.Thread(
        target=actuators.servo_to_angle,
        args=(goc_dich,),
        daemon=True
    ).start()
    display.update_lcd("Servo moved:", f"{goc_dich} degrees")
    return jsonify({"status": "ok", "message": f"Da toi {goc_dich} do"})


@app.route('/api/led')
def api_led():
    with _remote_lock:
        if remote_active:
            return jsonify({"status": "busy", "message": "Remote dang hoat dong"})
    r = request.args.get('r', 0, type=int)
    g = request.args.get('g', 0, type=int)
    b = request.args.get('b', 0, type=int)
    actuators.set_led_rgb(r, g, b)
    return jsonify({"status": "ok"})


@app.route('/api/blink')
def api_blink():
    with _remote_lock:
        if remote_active:
            return jsonify({"status": "busy", "message": "Remote dang hoat dong"})
    state = (request.args.get('state', 'false').lower() == 'true')
    speed = request.args.get('speed', default=0.5, type=float)
    actuators.set_blink(state, speed)
    return jsonify({"status": "ok"})


@app.route('/api/lcd')
def api_lcd():
    with _remote_lock:
        if remote_active:
            return jsonify({"status": "busy", "message": "Remote dang hoat dong"})
    text = request.args.get('text', '')
    if len(text) > 16:
        display.update_lcd(text[:16], text[16:32])
    else:
        display.update_lcd("Message:", text)
    return jsonify({"status": "ok"})




# ============================================================
# HÀM THỰC THI LỆNH GOKKU (dùng chung cho remote + web)
# ============================================================
def _run_gokku_action(key_code: str):
    """Thực thi hành động Gokku theo mã phím 1/2/3."""
    if key_code == "1":
        gokku.show_weather()
    elif key_code == "2":
        gokku.say(random.choice(gokku.IDLE_PHRASES), duration=3)
    elif key_code == "3":
        gokku.say("Ryoukai! Ima\nte wo furu ne.", duration=2)
        actuators.action_wave(times=2)


# ============================================================
# LUỒNG 1: ĐỌC CẢM BIẾN (cập nhật sensor_data mỗi 2 giây)
# ============================================================
def sensor_loop():
    while True:
        try:
            t, h = sensors.read_dht11()
            if t is not None:
                sensor_data["temp"] = f"{t:.1f} C"
            if h is not None:
                sensor_data["hum"] = f"{h:.0f} %"
        except Exception:
            pass

        try:
            press = sensors.read_bmp180()
            if press is not None:
                sensor_data["press"] = f"{press:.1f} hPa"
        except Exception:
            pass

        try:
            light_val = sensors.read_light()
            if light_val is not None:
                sensor_data["light"] = f"{light_val * 100:.0f} %"
        except Exception:
            pass

        try:
            tilt_val = sensors.read_tilt()
            if tilt_val is not None:
                sensor_data["tilt"] = "BI DO!" if tilt_val == 1 else "An toan"
        except Exception:
            pass

        try:
            sensor_data["pir"] = "Co nguoi!" if sensors.pir.motion_detected else "Khong"
        except Exception:
            pass

        time.sleep(2.0)


# ============================================================
# LUỒNG 2: REMOTE + BÀN PHÍM (logic gốc từ main.py cũ)
# ============================================================
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
    Chạy song song với Flask server.
    remote_active = True khi Gokku đang thức (từ lúc PIR phát hiện đến khi ngủ lại),
    trong suốt thời gian đó web KHÔNG được điều khiển LED/Servo/LCD.
    """
    global gokku_busy, remote_active
    print("[SYS] Gokku dang cho lenh (remote + ban phim)...")
    ir_receiver.start_ir_thread()
    is_sleeping = True

    while True:
        if sensors.pir.motion_detected and is_sleeping:
            print("\n[PIR] Phat hien nguoi!")
            is_sleeping = False
            # Đánh dấu remote đang hoạt động — web sẽ bị từ chối cho các module actuator
            with _remote_lock:
                remote_active = True
            gokku.miku_action_greet()
            gokku.say("Konnichiwa!\nGokku desu yo!", duration=4)

            while not is_sleeping:
                print("\n[SYS] Gokku dang cho lenh...")
                key_code = ask_master_menu()

                if key_code in ["1", "2", "3"]:
                    # Remote ưu tiên: thực thi ngay dù web có đang gửi lệnh
                    with _gokku_lock:
                        gokku_busy = True
                    try:
                        _run_gokku_action(key_code)
                    finally:
                        with _gokku_lock:
                            gokku_busy = False

                elif key_code is None:
                    print("[LOG] Khong nhan duoc tin hieu. He thong nghi.")
                    gokku.say("Daremo inai.\nSuriipu shimasu.", duration=3)
                    is_sleeping = True
                    actuators.turn_off()
                    display.lcd.clear()
                    # Khi ngủ lại → web được phép điều khiển trở lại
                    with _remote_lock:
                        remote_active = False

        time.sleep(0.1)


# ============================================================
# KHỞI ĐỘNG HỆ THỐNG
# ============================================================
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
