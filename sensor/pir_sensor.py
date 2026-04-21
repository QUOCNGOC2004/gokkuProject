from gpiozero import MotionSensor
import config

pir = None
try:
    pir = MotionSensor(config.PIR_PIN)
    print("[HW] PIR san sang.")
except Exception as e:
    print(f"[HW] PIR loi: {e}")

def read_pir():
    if pir is None:
        return None
    try:
        return pir.motion_detected
    except:
        return None
