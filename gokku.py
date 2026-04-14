import threading
import random
import display
import actuators
import sensors
import shared_state
import config

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

if HAS_GENAI and hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY and config.GEMINI_API_KEY != "YOUR_API_KEY_HERE":
    genai.configure(api_key=config.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
else:
    gemini_model = None

IDLE_PHRASES = [
    "Konnichiwa,\nGokku desu!",
    "Yoi ichinichi wo\nsugoshite ne!",
    "Suibun hokyuu wo\nwasurenaide ne.",
    "1 jikan goto ni\nkyuukei shite!",
]


def say(text, duration=3.0):
    threading.Thread(target=actuators.blink_short, daemon=True).start()
    display.display_text(text, total_duration=duration)


def miku_action_greet():
    threading.Thread(target=actuators.flash_long, args=(5,), daemon=True).start()
    threading.Thread(target=actuators.action_wave, args=(3,), daemon=True).start()


def ask_gemini(prompt):
    """ Hàm cốt lõi để gọi Gemini API và cân đối thời gian hiển thị LCD """
    if not gemini_model:
        say("API Key erro!\nGemini muko.", duration=3)
        return
    
    # Bật nháy đèn ngắn và báo trên màn hình đang suy nghĩ
    threading.Thread(target=actuators.blink_short, args=(2,), daemon=True).start()
    display.write_direct("Kangaechuu...", "Matte ne~")
    
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.replace("\n", "  ").strip() 
        
        # Tính thời gian chạy chữ tương đối cho người dùng
        total_chars = len(text)
        estimated_duration = max(5.0, (total_chars / 32.0) * 5.0) + 4.0
        say(text, duration=estimated_duration)
    except Exception as e:
        print(f"[AI] Loi Gemini: {e}")
        say("Gomen! AI eraa\ndesu.", duration=3)


def show_weather():
    """ Đọc cảm biến thực tế, lấy prompt đưa cho AI làm thông báo thời tiết """
    if not gemini_model:
        say("API Key erro!\nGemini muko.", duration=3)
        return

    # Lấy dữ liệu từ background loop thay vì block đo lại 
    t = shared_state.sensor_data.get("temp", "Khong ro")
    h = shared_state.sensor_data.get("hum", "Khong ro")
    p = shared_state.sensor_data.get("press", "Khong ro")
    l = shared_state.sensor_data.get("light", "Khong ro")
    tilt = shared_state.sensor_data.get("tilt", "Khong roi")
    
    prompt = f"""
    You are Gokku, a polite, friendly, and hardworking office worker acting as a smart assistant.
    You are interacting with your colleagues.
    Current sensor readings:
    - Temperature: {t}
    - Humidity: {h}
    - Pressure: {p}
    - Environment light: {l}
    - Tilt sensor (an toan/bi do): {tilt}

    Rules:
    1. Reply ONLY in Romanized Japanese (Romaji plain text). NO emojis, NO kanji, NO hiragana.
    2. Length limitation: None. Feel free to make it as long as you need.
    3. Content Rule 1: You MUST explicitly report ALL the exact reading values for Temperature, Humidity, Pressure, Light, and Tilt. Do not omit any sensor.
    4. Content Rule 2: Provide an overall evaluation/commentary on the environment based on those full readings.
    5. Content Rule 3: Conclude with a lively, caring, and roleplay-fitting advice for your colleague based on the weather conditions.
    6. CRITICAL LCD RULE: When stating sensor values, you MUST write the exact numbers and signs (e.g. "24.5 C", "60 %", "1012 hPa"). DO NOT spell out digits or percent into romaji (for example, never say "ni juu yon" or "pasento").
    """
    ask_gemini(prompt)


def ai_oshaberi():
    """ Tám chuyện ngẫu nhiên cùng đồng nghiệp thay cho chức năng cũ """
    if not gemini_model:
        say(random.choice(IDLE_PHRASES), duration=3)
        return

    prompt = """
    You are Gokku, a friendly, polite, and caring human office worker.
    Say a random, creative greeting, a short encouraging message, or a gentle reminder (e.g. stretch arms, drink water) to your human colleague/boss.
    
    Rules:
    1. Reply ONLY in Romanized Japanese (Romaji plain text). NO emojis, NO kanji, NO hiragana.
    2. Write max 2-3 short sentences (around 80-120 chars total) so it fits on an LCD.
    """
    ask_gemini(prompt)
