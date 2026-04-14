import config
import google.generativeai as genai

def main():
    print("Đang kiểm tra các model hỗ trợ với API Key của bạn...")
    if not hasattr(config, 'GEMINI_API_KEY') or not config.GEMINI_API_KEY or config.GEMINI_API_KEY == 'YOUR_API_KEY_HERE':
        print("[LỖI] Bạn chưa điền GEMINI_API_KEY vào config.py")
        return

    genai.configure(api_key=config.GEMINI_API_KEY)
    
    try:
        models = genai.list_models()
        found = False
        print("-" * 40)
        print("DANH SÁCH MODEL KHẢ DỤNG CHO GEN CONTENT:")
        print("-" * 40)
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"Hỗ trợ: {m.name}")
                found = True
        
        if not found:
            print("Không tìm thấy model nào hỗ trợ 'generateContent' đối với Key này.")
            print("Có thể vùng quốc gia của Key bị chặn, hoặc Key không hợp lệ.")
            
    except Exception as e:
        print(f"[LỖI XÁC THỰC API] {e}")

if __name__ == "__main__":
    main()
