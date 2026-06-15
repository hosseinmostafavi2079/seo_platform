from abc import ABC, abstractmethod

class BaseAIClient(ABC):
    @abstractmethod
    def chat_completion(self, messages: list, temperature: float, max_tokens: int, **kwargs) -> dict:
        """Sends a text prompt/messages and returns a unified dict response."""
        pass

    @abstractmethod
    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Generates an image from a prompt and returns raw bytes."""
        pass