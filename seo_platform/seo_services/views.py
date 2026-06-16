from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Site, KeywordResearch, GeneratedArticle
from .tasks import run_keyword_research_task, run_article_generation_task

@login_required
def dashboard_home(request):
    """ صفحه اصلی داشبورد: آمار کلی سیستم """
    context = {
        'total_sites': Site.objects.count(),
        'total_keywords': KeywordResearch.objects.count(),
        'total_articles': GeneratedArticle.objects.count(),
        'recent_keywords': KeywordResearch.objects.order_by('-created_at')[:5],
        'recent_articles': GeneratedArticle.objects.order_by('-created_at')[:5],
        'active_menu': 'dashboard'
    }
    return render(request, 'seo_services/dashboard.html', context)

@login_required
def keyword_research_view(request):
    """ صفحه تحقیق کلمات کلیدی: فرم درخواست + جدول نتایج """
    if request.method == 'POST':
        site_id = request.POST.get('site_id')
        business_desc = request.POST.get('business_desc')
        core_kw = request.POST.get('core_keywords')
        competitors = request.POST.get('competitors')
        
        if site_id and core_kw:
            run_keyword_research_task.delay(int(site_id), business_desc, core_kw, competitors)
            messages.success(request, "🤖 فرآیند استخراج کلمات کلیدی و عناوین خوشه‌ای توسط هوش مصنوعی در پس‌زمینه آغاز شد.")
        return redirect('keyword_research')

    context = {
        'sites': Site.objects.all(),
        'keywords': KeywordResearch.objects.order_by('-created_at'),
        'active_menu': 'keywords'
    }
    return render(request, 'seo_services/keyword_research.html', context) # باگ این خط کاملاً رفع شد

@login_required
def article_factory_view(request):
    """ صفحه کارخانه تولید محتوا: مدیریت مقالات، تعداد تصاویر و زمان‌بندی """
    if request.method == 'POST':
        action = request.POST.get('action')
        article_id = request.POST.get('article_id')
        
        if action == 'generate' and article_id:
            run_article_generation_task.delay(int(article_id))
            messages.success(request, "📝 هوش مصنوعی شروع به نوشتن مقاله، لینک‌سازی داخلی و تولید تصاویر مابین متن کرد.")
            
        elif action == 'create_manual':
            site_id = request.POST.get('site_id')
            title = request.POST.get('title')
            img_count = request.POST.get('image_count', 1)
            if site_id and title:
                GeneratedArticle.objects.create(
                    site_id=int(site_id), title=title, image_count=int(img_count), status='draft'
                )
                messages.success(request, "عنوان دستی با موفقیت در کارخانه رزرو شد.")
        return redirect('article_factory')

    context = {
        'sites': Site.objects.all(),
        'articles': GeneratedArticle.objects.order_by('-created_at'),
        'active_menu': 'articles'
    }
    return render(request, 'seo_services/article_factory.html', context)

@login_required
def sites_management_view(request):
    """ صفحه مدیریت پروژه‌ها: اتصال به وردپرس """
    if request.method == 'POST':
        name = request.POST.get('name')
        domain = request.POST.get('domain')
        wp_url = request.POST.get('wp_url')
        wp_user = request.POST.get('wp_username')
        wp_pass = request.POST.get('wp_app_password')
        
        if name and domain:
            Site.objects.create(name=name, domain=domain, wp_url=wp_url, wp_username=wp_user, wp_app_password=wp_pass)
            messages.success(request, "🌐 پروژه جدید با موفقیت به پلتفرم متصل شد.")
        return redirect('sites_management')

    context = {
        'sites': Site.objects.order_by('-created_at'),
        'active_menu': 'sites'
    }
    return render(request, 'seo_services/sites_management.html', context)