import requests
import json
from .models import AIConfig

class LLMService:
    @staticmethod
    def send_request(site_id, feature_type, system_message, user_message):
        """
        ارسال هوشمند درخواست به هوش مصنوعی بر اساس تنظیمات اختصاصی هر سایت
        """
        # ۱. خواندن تنظیمات اختصاصی سایت از دیتابیس
        config = AIConfig.objects.filter(site_id=site_id, feature_type=feature_type).first()
        
        if not config or not config.api_key:
            raise ValueError(f"تنظیمات هوش مصنوعی یا کلید API برای این سایت در بخش {feature_type} یافت نشد.")

        provider = config.provider
        model_name = config.model_name
        temperature = config.temperature
        max_tokens = config.max_tokens
        api_key = config.api_key

        # ۲. پردازش درخواست برای پرووایدرهای مبتنی بر ساختار OpenAI (شامل خود OpenAI و GapGPT)
        if provider in ['openai', 'gapgpt']:
            url = "https://api.openai.com/v1/chat/completions" if provider == 'openai' else "https://api.gapgpt.app/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response_data = response.json()
                if response.status_code == 200:
                    return response_data['choices'][0]['message']['content']
                else:
                    raise Exception(f"خطا از سمت پرووایدر {provider}: {response.text}")
            except Exception as e:
                raise Exception(f"خطا در ارتباط با {provider}: {str(e)}")

        # ۳. پردازش درخواست برای گوگل جمینای (Google Gemini)
        elif provider == 'gemini':
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # ادغام پرامپت سیستم و کاربر برای ساختار نیتیو جمینای
            full_prompt = f"{system_message}\n\nتسک شما:\n{user_message}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                response_data = response.json()
                if response.status_code == 200:
                    return response_data['candidates'][0]['content']['parts'][0]['text']
                else:
                    raise Exception(f"خطا از سمت گوگل جمینای: {response.text}")
            except Exception as e:
                raise Exception(f"خطا در ارتباط با جمینای: {str(e)}")

        else:
            raise ValueError("پرووایدر انتخاب شده معتبر نیست.")