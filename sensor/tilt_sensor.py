from gpiozero import DigitalInputDevice
import config

tilt_sensor = None
try:
    tilt_sensor = DigitalInputDevice(config.TILT_PIN)
    print("[HW] Tilt Sensor san sang.")
except Exception as e:
    print(f"[HW] Tilt Sensor loi: {e}")

def read_tilt():
    if tilt_sensor is None:
        return None
    try:
        return tilt_sensor.value
    except:
        return None
