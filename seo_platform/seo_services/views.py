from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Site, KeywordResearch, GeneratedArticle

@login_required
def dashboard_home(request):
    """
    نمایش صفحه اصلی داشبورد تجاری پلتفرم سئو
    """
    # دریافت اطلاعات آماری پروژه‌ها برای نمایش در کارت‌های بالای داشبورد
    total_sites = Site.objects.count()
    total_keywords = KeywordResearch.objects.count()
    total_articles = GeneratedArticle.objects.count()
    
    # دریافت آخرین کلمات کلیدی استخراج شده
    recent_keywords = KeywordResearch.objects.order_by('-created_at')[:8]
    
    context = {
        'total_sites': total_sites,
        'total_keywords': total_keywords,
        'total_articles': total_articles,
        'recent_keywords': recent_keywords,
    }
    return render(request, 'seo_services/dashboard.html', context)