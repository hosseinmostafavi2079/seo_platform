# apps/ai_providers/services/factory.py
from ai_providers.models import AIProviderConfig
from ai_providers.services.base import BaseAIClient
from ai_providers.services.openai_client import OpenAICompatibleClient
from ai_providers.services.gemini_client import GeminiClient

class AIClientFactory:
    @staticmethod
    def get_client(ai_config: AIProviderConfig) -> BaseAIClient:
        provider = ai_config.provider.lower()
        
        if provider in ('openai', 'gapgpt', 'custom'):
            return OpenAICompatibleClient(
                api_key=ai_config.api_key,
                base_url=ai_config.base_url,
                model_name=ai_config.model_name
            )
        elif provider == 'gemini':
            return GeminiClient(
                api_key=ai_config.api_key,
                model_name=ai_config.model_name
            )
        else:
            raise ValueError(f"Unsupported AI Provider factory target: {ai_config.provider}")