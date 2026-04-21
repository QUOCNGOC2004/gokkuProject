from gpiozero import MCP3008
import config

try:
    ldr = MCP3008(channel=config.LDR_CHANNEL)
except Exception as e:
    print(f"[-] Không thể khởi tạo ADC MCP3008 cho LDR: {e}")
    ldr = None

def read_ldr():
    """Đọc giá trị biến trở/LDR, trả về dải float từ 0.0 (tối thiểu) đến 1.0 (tối đa), hoặc None"""
    try:
        if ldr is None:
            return None
        return ldr.value
    except Exception as e:
        print(f"[-] Lỗi đọc giá trị LDR: {e}")
        return None
