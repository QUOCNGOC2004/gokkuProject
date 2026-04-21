import config

# --- Khởi tạo Gemini ---
_model = None
_init_error: str | None = None

try:
    import google.generativeai as genai

    if config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-2.5-flash")
        print("[AI] Gemini san sang.")
    else:
        _init_error = "Thieu GEMINI_API_KEY"
        print(f"[AI] {_init_error}")

except ImportError:
    _init_error = "Thieu thu vien google-generativeai"
    print(f"[AI] {_init_error}")
except Exception as e:
    _init_error = str(e)
    print(f"[AI] Loi khoi tao: {e}")


def ask(prompt: str) -> str | None:
    """
    Gọi Gemini API với prompt cho trước.
    Trả về chuỗi văn bản đã clean, hoặc None nếu thất bại.
    """
    if _model is None:
        print(f"[AI] Bo qua - {_init_error}")
        return None

    try:
        response = _model.generate_content(prompt)
        text = response.text.strip()
        # Xóa ký tự xuống dòng thừa để text_scroller xử lý đều
        text = " ".join(text.split())
        return text if text else None
    except Exception as e:
        print(f"[AI] Loi goi API: {e}")
        return None
