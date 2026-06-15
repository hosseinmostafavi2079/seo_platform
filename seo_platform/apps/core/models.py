# apps/core/models.py
from django.db import models
from sites.models import Site
from ai_providers.models import AIProviderConfig

class AIRequestLog(models.Model):
    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.SET_NULL)
    ai_config = models.ForeignKey(AIProviderConfig, null=True, blank=True, on_delete=models.SET_NULL)
    purpose = models.CharField(max_length=100, help_text="keyword_research / content_generation")
    prompt_tokens = models.IntegerField(null=True, blank=True)
    completion_tokens = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log {self.purpose} - {self.status} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"