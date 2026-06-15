# apps/content_generation/serializers.py
from rest_framework import serializers
from content_generation.models import ArticleJob

class ArticleJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArticleJob
        fields = [
            'id', 'site', 'topic', 'title', 'target_keyword', 'wp_category_id',
            'seo_title', 'seo_meta_description', 'seo_focus_keyword', 
            'images_count', 'content_html', 'status', 'wp_post_id', 'error_message'
        ]
        read_only_fields = ['seo_title', 'seo_meta_description', 'seo_focus_keyword', 'content_html', 'status', 'wp_post_id', 'error_message']