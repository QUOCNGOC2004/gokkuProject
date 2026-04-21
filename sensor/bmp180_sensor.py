import bmp180
import config

bmp_sensor = None
try:
    bmp_sensor = bmp180.BMP180(config.i2c_bus)
    print("[HW] BMP180 san sang.")
except Exception as e:
    print(f"[HW] BMP180 loi: {e}")

def read_bmp():
    if bmp_sensor is None:
        return None
    try:
        return bmp_sensor.pressure
    except:
        return None
