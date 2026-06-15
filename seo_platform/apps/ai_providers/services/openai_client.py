import httpx
from ai_providers.services.base import BaseAIClient

class OpenAICompatibleClient(BaseAIClient):
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        # اگر base_url خالی بود، از آدرس پیش‌فرض رسمی خود OpenAI استفاده کند
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model_name = model_name

    def chat_completion(self, messages: list, temperature: float, max_tokens: int, **kwargs) -> dict:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return {
                "text": data["choices"][0]["message"]["content"],
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
                "raw_response": data
            }

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "prompt": prompt,
            "n": 1,
            "size": size
        }
        
        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            image_url = res.json()["data"][0]["url"]
            
            # دانلود تصویر و بازگرداندن به صورت Raw Bytes
            img_res = client.get(image_url)
            img_res.raise_for_status()
            return img_res.content