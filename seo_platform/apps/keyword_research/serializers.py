# apps/keyword_research/serializers.py
from rest_framework import serializers
from keyword_research.models import KeywordResearchJob, KeywordCategory, Keyword, ContentTopic

class KeywordResearchJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeywordResearchJob
        fields = [
            'id', 'site', 'business_description', 'seed_keywords', 
            'competitor_urls', 'depth_option', 'domain_focus', 
            'status', 'created_at', 'completed_at', 'error_message'
        ]
        read_only_fields = ['status', 'created_at', 'completed_at', 'error_message']