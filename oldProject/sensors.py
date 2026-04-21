import time
from gpiozero import MotionSensor, MCP3008, DigitalInputDevice
import bmp180
import adafruit_dht
import config

# Khởi tạo PIR
pir = MotionSensor(config.PIR_PIN)

# Khởi tạo DHT11
dht_device = None
try:
    dht_device = adafruit_dht.DHT11(config.DHT_PIN, use_pulseio=False)
    print("[HW] DHT11 san sang.")
except Exception as e:
    print(f"[HW] DHT11 loi: {e}")

# Khởi tạo BMP180
bmp_sensor = None
try:
    bmp_sensor = bmp180.BMP180(config.i2c_bus)
    print("[HW] BMP180 san sang.")
except Exception as e:
    print(f"[HW] BMP180 loi: {e}")

# Khởi tạo MCP3008
light_sensor = None
try:
    light_sensor = MCP3008(channel=config.LDR_CHANNEL)
    print("[HW] MCP3008 (LDR) san sang.")
except Exception as e:
    print(f"[HW] MCP3008 loi: {e}")

# Khởi tạo Tilt
tilt_sensor = None
try:
    tilt_sensor = DigitalInputDevice(config.TILT_PIN)
    print("[HW] Tilt Sensor san sang.")
except Exception as e:
    print(f"[HW] Tilt Sensor loi: {e}")


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
