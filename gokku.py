import threading
import random
import display
import actuators
import sensors

IDLE_PHRASES = [
    "Konnichiwa,\nGokku desu!",
    "Yoi ichinichi wo\nsugoshite ne!",
    "Suibun hokyuu wo\nwasurenaide ne.",
    "1 jikan goto ni\nkyuukei shite!",
    "Oshigoto no\nchoushi wa dou?",
    "Geemu shite\nikinuki shiyou!",
    "Nanika tetsudai\nmashou ka?",
    "Zutto suwarazu\nundou shite ne.",
    "Subete junchou\nni ugoite iru!",
    "Deeta no hozon\nwasurenaide ne!",
]


def say(text, duration=3.0):
    threading.Thread(target=actuators.blink_short, daemon=True).start()
    display.display_text(text, total_duration=duration)


def miku_action_greet():
    threading.Thread(target=actuators.flash_long, args=(5,), daemon=True).start()
    threading.Thread(target=actuators.action_wave, args=(3,), daemon=True).start()


def show_weather():
    say("Chotto matte!\nKeisokuchuu...", duration=2)

    # Kion & Shitsudo
    t, h = sensors.read_dht11()
    if t is not None and h is not None:
        say(f"Ima no kion\n{t:.1f} do C", duration=3)
        say(f"Ima no shitsudo\n{h:.0f} paasento", duration=3)
        if t >= 30:
            say("Atsui desu!!\nKi wo tsukete.", duration=3)
        elif t >= 20:
            say("Kion ga ii ne.\nKaiteki desu.", duration=3)
        else:
            say("Samui desu yo!\nKi wo tsukete.", duration=3)
    else:
        say("Sensa eraa:\nKion, Shitsudo", duration=3)

    # Kiatsu
    say("Tsugi wa kiatsu\nwo hakarimasu!", duration=2)
    press = sensors.read_bmp180()
    if press is not None:
        say(f"Kiatsu wa\n{press:.1f} hPa", duration=3)
        if press < 1000:
            say("Teikiatsu desu!\nAme furu kamo.", duration=3)
        else:
            say("Kiatsu seijou.\nKaiteki desu ne.", duration=3)
    else:
        say("Sensa eraa:\nKiatsu...", duration=3)

    # Akarusa
    say("Akarusa wo\nchekku chuu!", duration=2)
    light_val = sensors.read_light()
    if light_val is not None:
        say(f"Akarusa wa ima\n{light_val*100:.0f} paasento", duration=3)
    else:
        say("Sensa eraa:\nAkarusa...", duration=3)

    # Katamuki
    say("Katamuki sensa\nchekku chuu...", duration=2)
    tilt_val = sensors.read_tilt()
    if tilt_val is not None:
        if tilt_val == 1:
            say("Keikoku!!!\nTaorete imasu!", duration=3)
        else:
            say("Anzen desu.\nKatamuki nashi.", duration=3)
    else:
        say("Gomen, katamuki\nsensa eraa desu.", duration=3)

    say("Houkoku subete\nkanryou shita!", duration=3)
