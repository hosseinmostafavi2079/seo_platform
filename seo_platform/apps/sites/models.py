from django.db import models
from django.conf import settings

class Site(models.Model):
    name = models.CharField(max_length=255)
    domain = models.URLField(unique=True)
    wp_api_url = models.URLField()
    wp_username = models.CharField(max_length=255)
    wp_app_password = models.CharField(max_length=512)  # در فاز ۴ رمزنگاری می‌شود
    business_description = models.TextField()
    target_keywords_seed = models.TextField(blank=True)
    competitor_urls = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_sites'
    )

    def __str__(self):
        return self.name

class SiteMembership(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')

    class Meta:
        unique_together = ('user', 'site')

    def __str__(self):
        return f"{self.user.username} - {self.site.name} ({self.role})"