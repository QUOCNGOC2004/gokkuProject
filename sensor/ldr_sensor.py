from gpiozero import MCP3008
import config

light_sensor = None
try:
    light_sensor = MCP3008(channel=config.LDR_CHANNEL)
    print("[HW] MCP3008 (LDR) san sang.")
except Exception as e:
    print(f"[HW] MCP3008 loi: {e}")

def read_ldr():
    if light_sensor is None:
        return None
    try:
        val = light_sensor.value
        return val if val >= 0.02 else None
    except:
        return None
