import time
import adafruit_dht
import config

dht_device = None
try:
    dht_device = adafruit_dht.DHT11(config.DHT_PIN, use_pulseio=False)
    print("[HW] DHT11 san sang.")
except Exception as e:
    print(f"[HW] DHT11 loi: {e}")

def read_dht():
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
