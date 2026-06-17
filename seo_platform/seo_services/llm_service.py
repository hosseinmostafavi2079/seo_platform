import requests
import json
from .models import AIConfig

class LLMService:
    @staticmethod
    def send_request(site_id, feature_type, system_message, user_message):
        """
        ارسال هوشمند و پایدار درخواست به هوش مصنوعی با فعال‌سازی JSON Mode نیتیو
        """
        config = AIConfig.objects.filter(site_id=site_id, feature_type=feature_type).first()
        
        if not config or not config.api_key:
            raise ValueError(f"تنظیمات هوش مصنوعی یا کلید API برای این سایت در بخش {feature_type} یافت نشد.")

        provider = config.provider
        model_name = config.model_name
        temperature = config.temperature
        max_tokens = config.max_tokens
        api_key = config.api_key

        # پردازش درخواست پرووایدرهای مبتنی بر ساختار OpenAI (شامل OpenAI و GapGPT)
        if provider in ['openai', 'gapgpt']:
            url = "[https://api.openai.com/v1/chat/completions](https://api.openai.com/v1/chat/completions)" if provider == 'openai' else "[https://api.gapgpt.app/v1/chat/completions](https://api.gapgpt.app/v1/chat/completions)"
            
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
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}  # 🎯 فعال‌سازی حالت بومی ساختار JSON
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

        # پردازش درخواست برای گوگل جمینای (Google Gemini) طبق داک رسمی پرووایدر
        elif provider == 'gemini':
            url = f"[https://generativelanguage.googleapis.com/v1beta/models/](https://generativelanguage.googleapis.com/v1beta/models/){model_name}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{
                    "parts": [{"text": user_message}]
                }],
                "systemInstruction": {  # 🧠 ارسال تفکیک شده پرامپت سیستم
                    "parts": [{"text": system_message}]
                },
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json"  # 🎯 اجبار جمینای به خروجی جی‌سان کاملاً ساختاریافته
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