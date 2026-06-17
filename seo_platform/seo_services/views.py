from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Site, KeywordResearch, GeneratedArticle, AIConfig
from .tasks import run_keyword_research_task, run_article_generation_task

@login_required
def dashboard_home(request):
    """ صفحه اصلی داشبورد: نمایش آمار کلی سیستم """
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
def article_status_api(request, article_id):
    """ وب‌سرویس پایش زنده وضعیت نوار پیشرفت استپر مقالات """
    article = get_object_or_404(GeneratedArticle, id=article_id)
    step_percentages = {
        'idle': 0, 'links': 25, 'text': 50, 'images': 75, 'assembly': 90, 'success': 100, 'failed': 100
    }
    return JsonResponse({
        'step': article.current_step,
        'step_display': article.get_current_step_display(),
        'percentage': step_percentages.get(article.current_step, 0),
        'error_log': article.error_log or ""
    })

@login_required
def keyword_status_api(request, site_id):
    """ وب‌سرویس پایش زنده وضعیت نوار پیشرفت تحقیق کلمات کلیدی """
    site = get_object_or_404(Site, id=site_id)
    step_percentages = {
        'idle': 0, 'serper': 30, 'llm': 65, 'saving': 85, 'success': 100, 'failed': 100
    }
    return JsonResponse({
        'step': site.keyword_current_step,
        'step_display': site.get_keyword_current_step_display(),
        'percentage': step_percentages.get(site.keyword_current_step, 0),
        'error_log': site.keyword_error_log or ""
    })

@login_required
def keyword_research_view(request):
    """ مدیریت بانک کلمات کلیدی: مجهز به حذف دائمی دیتابیسی، سورت ستون‌ها، جستجو و صفحه‌بندی """
    selected_site_id = request.GET.get('site_id')
    sites = Site.objects.all()
    if not selected_site_id and sites.exists():
        selected_site_id = str(sites.first().id)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'run_ai_research':
            site_id = request.POST.get('site_id')
            business_desc = request.POST.get('business_desc')
            core_kw = request.POST.get('core_keywords')
            competitors = request.POST.get('competitors')
            topic_count = int(request.POST.get('topic_count', 20))
            intent_filter = request.POST.get('intent_filter', 'All')
            if site_id and core_kw:
                run_keyword_research_task.delay(int(site_id), business_desc, core_kw, competitors, topic_count, intent_filter)
                return JsonResponse({'status': 'queued'})
                
        elif action == 'add_manual_topic':
            site_id = request.POST.get('site_id')
            title = request.POST.get('article_title')
            category = request.POST.get('category_pillar', 'عمومی')
            intent = request.POST.get('intent', 'Informational')
            if site_id and title:
                KeywordResearch.objects.create(site_id=int(site_id), keyword=title, article_title=title, category_pillar=category, intent=intent, status='approved')
                messages.success(request, "🎯 موضوع دستی با موفقیت ثبت شد.")
            return redirect(f'/keywords/?site_id={site_id}')
            
        elif action == 'change_status':
            kw_id = request.POST.get('kw_id')
            new_status = request.POST.get('status')
            kw_item = get_object_or_404(KeywordResearch, id=int(kw_id))
            
            # حذف قطعی و کامل کلمه/موضوع از دیتابیس PostgreSQL
            if new_status == 'deleted':
                kw_item.delete()
            else:
                kw_item.status = new_status
                kw_item.save()
            return JsonResponse({'status': 'success'})
            
        elif action == 'update_keyword_row':
            kw_id = request.POST.get('kw_id')
            kw_item = get_object_or_404(KeywordResearch, id=int(kw_id))
            kw_item.article_title = request.POST.get('article_title')
            kw_item.category_pillar = request.POST.get('category_pillar')
            kw_item.intent = request.POST.get('intent')
            kw_item.save()
            messages.success(request, "✍️ موضوع با موفقیت اصلاح شد.")
            return redirect(f'/keywords/?site_id={selected_site_id}')

    # لایه استخراج اطلاعات به همراه فیلترها و مرتب‌سازی پویای ستون‌ها
    keywords_query = KeywordResearch.objects.filter(site_id=selected_site_id) if selected_site_id else KeywordResearch.objects.none()
    
    search_q = request.GET.get('search', '')
    if search_q:
        keywords_query = keywords_query.filter(article_title__icontains=search_q) | keywords_query.filter(category_pillar__icontains=search_q)
        
    intent_f = request.GET.get('intent', 'All')
    if intent_f and intent_f != 'All': 
        keywords_query = keywords_query.filter(intent=intent_f)
        
    status_f = request.GET.get('status', 'All')
    if status_f and status_f != 'All': 
        keywords_query = keywords_query.filter(status=status_f)

    sort_by = request.GET.get('sort', '-created_at')
    keywords_query = keywords_query.order_by(sort_by)

    per_page = int(request.GET.get('per_page', 20))
    paginator = Paginator(keywords_query, per_page)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'sites': sites, 'keywords': page_obj, 'selected_site_id': int(selected_site_id) if selected_site_id else None,
        'search_query': search_q, 'intent_filter': intent_f, 'status_filter': status_f, 'sort_by': sort_by, 'per_page': per_page, 'active_menu': 'keywords'
    }
    return render(request, 'seo_services/keyword_research.html', context)

@login_required
def article_factory_view(request):
    """ مدیریت کارخانه تولید محتوا: تولید اتوماتیک، دستی و حذف قطعی دیتابیسی مقالات """
    if request.method == 'POST':
        action = request.POST.get('action')
        article_id = request.POST.get('article_id')
        
        if action == 'generate' and article_id:
            run_article_generation_task.delay(int(article_id))
            return JsonResponse({'status': 'queued'})
            
        elif action == 'auto_generate_next':
            site_id = request.POST.get('site_id')
            img_count = int(request.POST.get('image_count', 2))
            next_topic = KeywordResearch.objects.filter(site_id=site_id, status__in=['approved', 'pending']).order_by('created_at').first()
            if next_topic:
                next_topic.status = 'generated'
                next_topic.save()
                article = GeneratedArticle.objects.create(site_id=int(site_id), keyword_ref=next_topic, title=next_topic.article_title, image_count=img_count, current_step='idle', status='draft')
                run_article_generation_task.delay(article.id)
                return JsonResponse({'status': 'queued', 'article_id': article.id})
            return JsonResponse({'status': 'error', 'message': 'موضوع آزادی یافت نشد.'}, status=400)
                
        elif action == 'create_manual':
            site_id = request.POST.get('site_id')
            title = request.POST.get('title')
            img_count = request.POST.get('image_count', 1)
            if site_id and title:
                GeneratedArticle.objects.create(site_id=int(site_id), title=title, image_count=int(img_count), current_step='idle', status='draft')
                messages.success(request, "عنوان دستی رزرو شد.")
                
        # 🗑️ قابلیت جدید و مهم: حذف دائمی و کامل کارت مقاله از دیتابیس پلتفرم
        elif action == 'delete_article' and article_id:
            article = get_object_or_404(GeneratedArticle, id=int(article_id))
            article.delete()
            return JsonResponse({'status': 'deleted'})
            
        return redirect('article_factory')

    context = {
        'sites': Site.objects.all(),
        'articles': GeneratedArticle.objects.order_by('-created_at'),
        'active_menu': 'articles'
    }
    return render(request, 'seo_services/article_factory.html', context)

@login_required
def sites_management_view(request):
    """ مدیریت پیشرفته مشخصات اتصال، اتوماسیون و پلتفرم‌های مستقل هوش مصنوعی """
    if request.method == 'POST':
        site_id = request.POST.get('site_id')
        if site_id:
            site = get_object_or_404(Site, id=int(site_id))
            site.name = request.POST.get('name')
            site.domain = request.POST.get('domain')
            site.wp_url = request.POST.get('wp_url')
            site.wp_username = request.POST.get('wp_username')
            wp_pass = request.POST.get('wp_app_password')
            if wp_pass and not wp_pass.startswith('••••'): site.wp_app_password = wp_pass
            site.is_automation_active = request.POST.get('is_automation_active') == 'on'
            site.automation_interval_days = int(request.POST.get('automation_interval_days', 2))
            site.content_type = request.POST.get('content_type', 'educational')
            site.save()
            
            for f_type in ['keyword', 'article_text', 'article_image']:
                AIConfig.objects.update_or_create(
                    site=site, feature_type=f_type,
                    defaults={
                        'provider': request.POST.get(f'ai_provider_{f_type}'), 'model_name': request.POST.get(f'ai_model_{f_type}'),
                        'temperature': float(request.POST.get(f'ai_temp_{f_type}', 0.7)), 'max_tokens': int(request.POST.get(f'ai_tokens_{f_type}', 4000)),
                        'api_key': request.POST.get(f'ai_key_{f_type}')
                    }
                )
            messages.success(request, "⚙️ تنظیمات با موفقیت ذخیره شد.")
        else:
            Site.objects.create(name=request.POST.get('name'), domain=request.POST.get('domain'), wp_url=request.POST.get('wp_url'), wp_username=request.POST.get('wp_username'), wp_app_password=request.POST.get('wp_app_password'))
            messages.success(request, "🌐 وب‌سایت ایجاد شد.")
        return redirect('sites_management')

    sites_list = Site.objects.all()
    for s in sites_list:
        s.cfg_kw = AIConfig.objects.filter(site=s, feature_type='keyword').first()
        s.cfg_text = AIConfig.objects.filter(site=s, feature_type='article_text').first()
        s.cfg_img = AIConfig.objects.filter(site=s, feature_type='article_image').first()
    return render(request, 'seo_services/sites_management.html', {'sites': sites_list, 'active_menu': 'sites'})