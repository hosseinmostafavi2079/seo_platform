# apps/keyword_research/models.py
from django.db import models
from django.conf import settings
from sites.models import Site

class KeywordResearchJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    DEPTH_CHOICES = [
        ('basic', 'کم (۱۵-۲۰ موضوع)'),
        ('standard', 'متوسط (۴۰-۵۰ موضوع)'),
        ('deep', 'عمیق (۸۰-۱۰۰ موضوع)'),
    ]

    site = models.ForeignKey(Site, related_name='keyword_jobs', on_delete=models.CASCADE)
    business_description = models.TextField()
    seed_keywords = models.TextField()
    competitor_urls = models.JSONField(default=list, blank=True)
    depth_option = models.CharField(max_length=20, choices=DEPTH_CHOICES, default='standard')
    domain_focus = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_ai_output = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Job #{self.id} - {self.site.name} ({self.status})"


class KeywordCategory(models.Model):
    """دسته‌بندی‌های سطح بالا یا همان ساختار Pillar Pages"""
    job = models.ForeignKey(KeywordResearchJob, related_name='categories', on_delete=models.CASCADE)
    site = models.ForeignKey(Site, related_name='categories', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class Keyword(models.Model):
    INTENT_CHOICES = [
        ('informational', 'Informational'),
        ('commercial', 'Commercial'),
        ('transactional', 'Transactional'),
        ('navigational', 'Navigational'),
    ]
    job = models.ForeignKey(KeywordResearchJob, related_name='keywords', on_delete=models.CASCADE)
    site = models.ForeignKey(Site, related_name='keywords', on_delete=models.CASCADE)
    keyword = models.CharField(max_length=255)
    intent = models.CharField(max_length=20, choices=INTENT_CHOICES)
    is_approved = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.keyword


class ContentTopic(models.Model):
    """موضوعات استخراج شده نهایی برای تولید مقاله"""
    job = models.ForeignKey(KeywordResearchJob, related_name='topics', on_delete=models.CASCADE)
    site = models.ForeignKey(Site, related_name='topics', on_delete=models.CASCADE)
    category = models.ForeignKey(KeywordCategory, related_name='topics', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    target_keyword = models.CharField(max_length=255, blank=True)
    is_approved = models.BooleanField(default=False)
    used_for_article = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title