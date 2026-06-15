import httpx
from ai_providers.services.base import BaseAIClient

class GeminiClient(BaseAIClient):
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def chat_completion(self, messages: list, temperature: float, max_tokens: int, **kwargs) -> dict:
        # تبدیل ساختار استاندارد پیام‌های پلتفرم به ساختار بومی جمینای (contents)
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # استخراج داده‌ها به شیوه یکسان‌سازی شده
            text_output = data["candidates"][0]["content"]["parts"][0]["text"]
            return {
                "text": text_output,
                "prompt_tokens": 0,  # جمینای در این اندپوینت به صورت پیش‌فرض کانت باز نمی‌گرداند
                "completion_tokens": 0,
                "raw_response": data
            }

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        # جمینای به طور مستقیم از این متد پشتیبانی نمی‌کند و در فاز فکتوری هندل می‌شود
        raise NotImplementedError("Image generation is not supported directly by Gemini client.")