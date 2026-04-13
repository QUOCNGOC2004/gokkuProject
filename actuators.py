import time
import random
from gpiozero import RGBLED, Servo
import config

servo = Servo(
    config.SERVO_PIN,
    initial_value=None,
    min_pulse_width=0.5 / 1000,
    max_pulse_width=2.5 / 1000,
)
led = RGBLED(red=config.LED_R, green=config.LED_G, blue=config.LED_B)

BLINK_COLORS = [
    (1, 0, 0.5),
    (0, 1, 0.5),
    (0.5, 0, 1),
    (1, 0.5, 0),
    (0, 0.5, 1),
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 0),
    (1, 0, 1),
    (0, 1, 1),
]


def blink_short(flashes=4):
    for _ in range(flashes):
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.12)
        led.off()
        time.sleep(0.08)


def flash_long(duration=5):
    end = time.time() + duration
    while time.time() < end:
        led.color = random.choice(BLINK_COLORS)
        time.sleep(0.18)
    led.off()


def action_wave(times=3):
    for _ in range(times):
        servo.max()
        time.sleep(0.45)
        servo.min()
        time.sleep(0.45)
    servo.value = None


def turn_off():
    led.off()
    servo.value = None
