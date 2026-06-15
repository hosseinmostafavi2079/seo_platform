from django.db import models
from sites.models import Site

class AIProviderConfig(models.Model):
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI Direct'),
        ('gapgpt', 'GapGPT (Multi-model proxy)'),
        ('gemini', 'Google Gemini'),
        ('anthropic', 'Anthropic Claude'),
        ('custom', 'Custom Endpoint'),
    ]

    site = models.ForeignKey(
        Site, 
        null=True, 
        blank=True, 
        related_name='ai_configs', 
        on_delete=models.CASCADE,
        help_text="If null, this is a global config managed by Super Admin."
    )
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    name = models.CharField(max_length=100, help_text="e.g., GapGPT - GPT4o or Gemini Pro")
    api_key = models.CharField(max_length=512)  # در فاز ۴ رمزنگاری سطح دیتابیس اعمال می‌شود
    base_url = models.URLField(blank=True, help_text="Required for custom or proxy endpoints like GapGPT")
    model_name = models.CharField(max_length=100, help_text="e.g., gpt-4o, gemini-1.5-pro")
    is_active = models.BooleanField(default=True)
    is_default_for_site = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        scope = f"Site: {self.site.name}" if self.site else "Global"
        return f"{self.name} ({scope}) - {self.model_name}"

    def save(self, *auto_id, **kwargs):
        if self.api_key and not self.api_key.startswith('gAAAAA'):
            from core.utils.encryption import EncryptedFieldHelper
            self.api_key = EncryptedFieldHelper.encrypt(self.api_key)
        super().save(*auto_id, **kwargs)

    @property
    def decrypted_api_key(self):
        from core.utils.encryption import EncryptedFieldHelper
        if self.api_key and self.api_key.startswith('gAAAAA'):
            return EncryptedFieldHelper.decrypt(self.api_key)
        return self.api_key

    @property
    def masked_api_key(self):
        """نمایش امنیتی کلید در داشبورد به صورت لایه ماسک شده"""
        decrypted = self.decrypted_api_key
        if len(decrypted) <= 8:
            return "********"
        return f"{decrypted[:4]}***...***{decrypted[-4:]}"


class GenerationProfile(models.Model):
    SEO_PLUGINS = [
        ('rankmath', 'RankMath'),
        ('yoast', 'Yoast SEO'),
    ]

    site = models.OneToOneField(Site, related_name='generation_profile', on_delete=models.CASCADE)
    ai_config = models.ForeignKey(AIProviderConfig, on_delete=models.SET_NULL, null=True, blank=True)
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=4000)
    tone_of_voice = models.CharField(max_length=255, blank=True, default="رسمی")
    target_word_count = models.IntegerField(default=1200)
    internal_links_min = models.IntegerField(default=2)
    internal_links_max = models.IntegerField(default=5)
    seo_plugin = models.CharField(max_length=50, choices=SEO_PLUGINS, default='rankmath')
    images_count_default = models.IntegerField(default=2)
    custom_instructions = models.TextField(blank=True)

    def __str__(self):
        return f"Generation Profile for {self.site.name}"