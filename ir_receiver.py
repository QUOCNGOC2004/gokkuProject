import threading
import subprocess
import queue
import config

ir_queue = queue.Queue()


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
                    if hex_code in config.IR_BUTTONS:
                        ir_queue.put(config.IR_BUTTONS[hex_code])
                buffer = []
    except Exception as e:
        print(f"[IR] Loi luong doc hong ngoai: {e}")


def start_ir_thread():
    threading.Thread(target=ir_reader_thread, daemon=True).start()
    print("[HW] IR Receiver san sang.")
