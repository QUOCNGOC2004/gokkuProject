import time
import threading
from flask import Flask, jsonify, request, render_template_string

# Import thư viện phần cứng từ dự án Gokku
import board
import busio
from gpiozero import AngularServo, RGBLED, MotionSensor, MCP3008, DigitalInputDevice
from RPLCD.i2c import CharLCD
import bmp180
import adafruit_dht

app = Flask(__name__)

# ==========================================
# 1. KHỞI TẠO BIẾN TOÀN CỤC TRẠNG THÁI
# ==========================================
sensor_data = {
    "temp": "Đang tải...",
    "hum": "Đang tải...",
    "press": "Đang tải...",
    "light": "Đang tải...",
    "tilt": "Bình thường",
    "pir": "Không có",
    "lcd_line1": "Khởi động...",
    "lcd_line2": "Hệ thống..."
}

goc_hien_tai = 0
led_color = (0, 0, 0)
is_blinking = False
blink_speed = 0.5 
led_state_on = False

# ==========================================
# 2. KHỞI TẠO PHẦN CỨNG (Phòng tránh lỗi)
# ==========================================
print("[SYS] Đang khởi tạo phần cứng...")
i2c = busio.I2C(board.SCL, board.SDA)

# Khởi tạo LCD
try:
    lcd = CharLCD(i2c_expander="PCF8574", address=0x27, port=1, cols=16, rows=2, charmap="A02")
    lcd.clear()
except Exception as e:
    print(f"[HW] Lỗi LCD: {e}")
    lcd = None

# Khởi tạo các cảm biến
try: dht_device = adafruit_dht.DHT11(board.D4, use_pulseio=False)
except: dht_device = None

try: bmp_sensor = bmp180.BMP180(i2c)
except: bmp_sensor = None

try: light_sensor = MCP3008(channel=0)
except: light_sensor = None

try: tilt_sensor = DigitalInputDevice(5)
except: tilt_sensor = None

try: pir = MotionSensor(17)
except: pir = None

# Đầu ra
servo = AngularServo(18, min_angle=0, max_angle=180, min_pulse_width=0.0005, max_pulse_width=0.0025)
led = RGBLED(red=22, green=27, blue=14)

# ==========================================
# 3. HÀM TRỢ GIÚP
# ==========================================
def update_lcd(line1, line2):
    """Cập nhật LCD thực tế và biến toàn cục để Web đọc được"""
    sensor_data["lcd_line1"] = line1
    sensor_data["lcd_line2"] = line2
    if lcd:
        lcd.clear()
        lcd.cursor_pos = (0, 0)
        lcd.write_string(line1.ljust(16)[:16])
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2.ljust(16)[:16])

def servo_quay_cham(goc_bat_dau, goc_ket_thuc):
    global goc_hien_tai
    goc_bat_dau = max(0, min(180, int(goc_bat_dau)))
    goc_ket_thuc = max(0, min(180, int(goc_ket_thuc)))
    if goc_bat_dau == goc_ket_thuc: return
        
    step = 1 if goc_bat_dau < goc_ket_thuc else -1
    for angle in range(goc_bat_dau, goc_ket_thuc + step, step):
        servo.angle = angle
        time.sleep(0.01) # Trễ xíu cho mượt
    
    time.sleep(0.2)
    servo.detach()
    goc_hien_tai = goc_ket_thuc

# ==========================================
# 4. LUỒNG CHẠY NGẦM PHẦN CỨNG
# ==========================================
def hardware_loop():
    global led_state_on
    update_lcd("Gokku System", "Web Online!")
    
    # Khởi động servo về 0
    servo.angle = 0
    time.sleep(1)
    servo.detach()
    
    last_blink_time = time.time()
    last_sensor_time = time.time()
    
    while True:
        now = time.time()
        
        # Đọc cảm biến mỗi 2 giây (DHT11 đọc chậm, không nên đọc nhanh)
        if now - last_sensor_time >= 2.0:
            # 1. DHT11
            if dht_device:
                try:
                    t = dht_device.temperature
                    h = dht_device.humidity
                    if t is not None: sensor_data["temp"] = f"{t:.1f} °C"
                    if h is not None: sensor_data["hum"] = f"{h:.0f} %"
                except: pass
            
            # 2. BMP180
            if bmp_sensor:
                try: sensor_data["press"] = f"{bmp_sensor.pressure:.1f} hPa"
                except: pass
                
            # 3. LDR (Ánh sáng)
            if light_sensor:
                try: sensor_data["light"] = f"{light_sensor.value * 100:.0f} %"
                except: pass
            
            # 4. Digital (Nghiêng & Chuyển động)
            if tilt_sensor:
                sensor_data["tilt"] = "BỊ ĐỔ!" if tilt_sensor.value == 1 else "An toàn"
            if pir:
                sensor_data["pir"] = "Có người!" if pir.motion_detected else "Không"
                
            last_sensor_time = now
            
        # Xử lý LED (chạy siêu nhanh)
        if is_blinking:
            if now - last_blink_time >= blink_speed:
                led_state_on = not led_state_on
                last_blink_time = now
                if led_state_on: led.color = led_color
                else: led.color = (0, 0, 0)
        else:
            led.color = led_color
            
        time.sleep(0.05)

# ==========================================
# 5. GIAO DIỆN WEB (HTML/CSS/JS)
# ==========================================
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
            <h2>🛡️ Trạng thái & Màn hình LCD</h2>
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
        </div>

        <div class="box">
            <h2>⚙️ Động Cơ Servo</h2>
            <div style="text-align: center; font-size: 32px; color: #00d2ff; font-weight: bold; margin: 20px 0;" id="goc_hien_thi">0°</div>
            <input type="range" id="goc_input" min="0" max="180" value="0" oninput="document.getElementById('goc_hien_thi').innerText = this.value + '°'">
            <button onclick="quayServo()">Thực thi quay</button>
            <div id="trang_thai_servo" style="color: #4cd137; text-align: center; margin-top: 10px; height: 20px;"></div>
        </div>
    </div>

    <script>
        function quayServo() {
            let goc = document.getElementById('goc_input').value;
            document.getElementById('trang_thai_servo').innerText = "Đang quay...";
            fetch('/api/servo?goc=' + goc).then(r=>r.json()).then(d => {
                document.getElementById('trang_thai_servo').innerText = d.message;
                setTimeout(() => document.getElementById('trang_thai_servo').innerText="", 2000);
            });
        }

        function capNhatLed() {
            let r = document.getElementById('r_input').value;
            let g = document.getElementById('g_input').value;
            let b = document.getElementById('b_input').value;
            document.getElementById('r_val').innerText = r;
            document.getElementById('g_val').innerText = g;
            document.getElementById('b_val').innerText = b;
            document.getElementById('mau_preview').style.backgroundColor = `rgb(${r},${g},${b})`;
            fetch(`/api/led?r=${r}&g=${g}&b=${b}`);
        }
        
        function capNhatBlink() {
            let is_blink = document.getElementById('blink_toggle').checked;
            let speed = document.getElementById('blink_speed').value;
            document.getElementById('speed_val').innerText = speed + "s";
            fetch(`/api/blink?state=${is_blink}&speed=${speed}`);
        }
        
        function guiLCD() {
            let text = document.getElementById('custom_text').value;
            fetch('/api/lcd?text=' + encodeURIComponent(text));
            document.getElementById('custom_text').value = "";
        }

        function quetCamBien() {
            fetch('/api/status').then(r=>r.json()).then(data => {
                document.getElementById('t_temp').innerText = data.temp;
                document.getElementById('t_hum').innerText = data.hum;
                document.getElementById('t_press').innerText = data.press;
                document.getElementById('t_light').innerText = data.light;
                
                let tiltEl = document.getElementById('t_tilt');
                tiltEl.innerText = data.tilt;
                if(data.tilt === "BỊ ĐỔ!") tiltEl.className = "data-val val-alert"; else tiltEl.className = "data-val val-hum";
                
                let pirEl = document.getElementById('t_pir');
                pirEl.innerText = data.pir;
                if(data.pir === "Có người!") pirEl.className = "data-val val-temp"; else pirEl.className = "data-val val-hum";
                
                // Màn hình LCD sử dụng font monospaced và thay khoảng trắng bằng &nbsp; để giữ đúng format
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

# ==========================================
# 6. API CỦA FLASK SERVER
# ==========================================
@app.route('/')
def trang_chu():
    return render_template_string(HTML_PAGE)

@app.route('/api/status')
def api_status():
    return jsonify(sensor_data)

@app.route('/api/servo')
def api_servo():
    goc_dich = request.args.get('goc', default=0, type=int)
    servo_quay_cham(goc_hien_tai, goc_dich)
    update_lcd("Servo moved:", f"{goc_dich} degrees")
    return jsonify({"message": f"Đã tới {goc_dich}°"})

@app.route('/api/led')
def api_led():
    global led_color
    r = request.args.get('r', 0, type=int)
    g = request.args.get('g', 0, type=int)
    b = request.args.get('b', 0, type=int)
    led_color = (r / 255.0, g / 255.0, b / 255.0)
    return jsonify({"status": "ok"})

@app.route('/api/blink')
def api_blink():
    global is_blinking, blink_speed
    is_blinking = (request.args.get('state', 'false') == 'true')
    blink_speed = request.args.get('speed', default=0.5, type=float)
    return jsonify({"status": "ok"})

@app.route('/api/lcd')
def api_lcd():
    text = request.args.get('text', '')
    if len(text) > 16:
        update_lcd(text[:16], text[16:32])
    else:
        update_lcd("Message:", text)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    # Chạy luồng đọc cảm biến ngầm
    t = threading.Thread(target=hardware_loop, daemon=True)
    t.start()
    
    print("------------------------------------------")
    print("✅ Web Dashboard Gokku Đã Khởi Động!")
    print("🌐 Truy cập: http://<IP_CUA_PI>:5000")
    print("------------------------------------------")
    # Tắt reloader để không làm luồng phần cứng bị khởi động 2 lần
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)