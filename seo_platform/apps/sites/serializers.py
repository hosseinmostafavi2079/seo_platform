# apps/sites/serializers.py
from rest_framework import serializers
from sites.models import Site, SiteMembership

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            'id', 'name', 'domain', 'wp_api_url', 'wp_username', 
            'wp_app_password', 'business_description', 
            'target_keywords_seed', 'competitor_urls', 'is_active', 'created_at'
        ]
        extra_kwargs = {
            'wp_app_password': {'write_only': True}  # پسورد هیچ‌وقت در پاسخ GET فرستاده نمی‌شود
        }