import threading
from flask import Flask, jsonify, request, render_template

import display
import actuators
import shared_state

app = Flask(__name__)


@app.route('/')
def trang_chu():
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Luôn trả dữ liệu cảm biến + LCD ở cả 2 mode (chỉ đọc)."""
    lcd_state = display.get_lcd_state()
    return jsonify({**shared_state.sensor_data, **lcd_state})


@app.route('/api/control_mode')
def api_control_mode():
    """Trả về mode điều khiển hiện tại để Dashboard cập nhật badge."""
    return jsonify({"remote_control_mode": shared_state.remote_control_mode})


def _check_web_locked():
    """Trả về response lỗi nếu đang ở Remote Mode, None nếu Web được phép."""
    if shared_state.remote_control_mode:
        return jsonify({
            "status": "locked",
            "message": "Remote dang nam quyen. Bam nut 4 de chuyen Web Mode."
        })
    return None


@app.route('/api/servo')
def api_servo():
    err = _check_web_locked()
    if err:
        return err
    goc_dich = request.args.get('goc', default=0, type=int)
    threading.Thread(
        target=actuators.servo_to_angle,
        args=(goc_dich,),
        daemon=True
    ).start()
    display.update_lcd("Servo moved:", f"{goc_dich} degrees")
    return jsonify({"status": "ok", "message": f"Da toi {goc_dich} do"})


@app.route('/api/led')
def api_led():
    err = _check_web_locked()
    if err:
        return err
    r = request.args.get('r', 0, type=int)
    g = request.args.get('g', 0, type=int)
    b = request.args.get('b', 0, type=int)
    actuators.set_led_rgb(r, g, b)
    return jsonify({"status": "ok"})


@app.route('/api/blink')
def api_blink():
    err = _check_web_locked()
    if err:
        return err
    state = (request.args.get('state', 'false').lower() == 'true')
    speed = request.args.get('speed', default=0.5, type=float)
    actuators.set_blink(state, speed)
    return jsonify({"status": "ok"})


@app.route('/api/lcd')
def api_lcd():
    err = _check_web_locked()
    if err:
        return err
    text = request.args.get('text', '')
    if len(text) > 16:
        display.update_lcd(text[:16], text[16:32])
    else:
        display.update_lcd("Message:", text)
    return jsonify({"status": "ok"})
