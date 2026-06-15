# apps/content_generation/models.py
from django.db import models
from django.conf import settings
from sites.models import Site
from keyword_research.models import ContentTopic
from ai_providers.models import AIProviderConfig

class ArticleJob(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generating', 'Generating Content'),
        ('ready_for_review', 'Ready for Review'),
        ('approved', 'Approved'),
        ('publishing', 'Publishing to WordPress'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    site = models.ForeignKey(Site, related_name='article_jobs', on_delete=models.CASCADE)
    topic = models.ForeignKey(ContentTopic, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255)
    target_keyword = models.CharField(max_length=255, blank=True)
    wp_category_id = models.IntegerField(null=True, blank=True, help_text="WordPress Category ID")
    
    seo_title = models.CharField(max_length=255, blank=True)
    seo_meta_description = models.TextField(blank=True)
    seo_focus_keyword = models.CharField(max_length=255, blank=True)
    
    images_count = models.IntegerField(default=2, help_text="Number of inline images requested")
    content_html = models.TextField(blank=True)
    featured_image = models.ImageField(upload_to='articles/featured/', null=True, blank=True)
    inline_images = models.JSONField(default=list, blank=True, help_text="List of saved image paths")
    internal_links_used = models.JSONField(default=list, blank=True, help_text="Links injected by AI")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    wp_post_id = models.IntegerField(null=True, blank=True, help_text="ID of the draft post in WordPress")
    ai_config_used = models.ForeignKey(AIProviderConfig, null=True, blank=True, on_delete=models.SET_NULL)
    custom_instructions = models.TextField(blank=True)
    
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Article: {self.title} ({self.status})"