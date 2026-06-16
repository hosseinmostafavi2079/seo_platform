from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Site, KeywordResearch, GeneratedArticle, AIConfig
from .tasks import run_keyword_research_task, run_article_generation_task
from django.core.paginator import Paginator

@login_required
def dashboard_home(request):
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
def keyword_research_view(request):
    """ مدیریت و ویرایش بانک کلمات کلیدی اختصاصی هر سایت """
    selected_site_id = request.GET.get('site_id')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # الف: ثبت درخواست اسکرپ و تحقیق اتوماتیک کلمات کلیدی
        if action == 'run_ai_research':
            site_id = request.POST.get('site_id')
            business_desc = request.POST.get('business_desc')
            core_kw = request.POST.get('core_keywords')
            competitors = request.POST.get('competitors')
            if site_id and core_kw:
                run_keyword_research_task.delay(int(site_id), business_desc, core_kw, competitors)
                messages.success(request, "🤖 فرآیند استخراج عناوین خوشه‌ای سئو در پس‌زمینه آغاز شد.")
            return redirect(f'/keywords/?site_id={site_id}')
            
        # ب: افزودن موضوع دستی سئو شده به جدول اختصاصی سایت
        elif action == 'add_manual_topic':
            site_id = request.POST.get('site_id')
            title = request.POST.get('article_title')
            category = request.POST.get('category_pillar', 'عمومی')
            intent = request.POST.get('intent', 'Informational')
            if site_id and title:
                KeywordResearch.objects.create(
                    site_id=int(site_id), keyword=title, article_title=title,
                    category_pillar=category, intent=intent, status='approved'
                )
                messages.success(request, "🎯 موضوع سئو شده دستی با موفقیت به بانک کلمات سایت اضافه شد.")
            return redirect(f'/keywords/?site_id={site_id}')
            
        # ج: تغییر سریع وضعیت موضوع (تایید یا حذف ردیف)
        elif action == 'change_status':
            kw_id = request.POST.get('kw_id')
            new_status = request.POST.get('status')
            kw_item = get_object_or_404(KeywordResearch, id=int(kw_id))
            kw_item.status = new_status
            kw_item.save()
            return JsonResponse({'status': 'success'})

    # فیلتر داینامیک جداول بر اساس انتخاب پروژه کاربر
    sites = Site.objects.all()
    if not selected_site_id and sites.exists():
        selected_site_id = str(sites.first().id)
        
    keywords = KeywordResearch.objects.filter(site_id=selected_site_id).order_by('-created_at') if selected_site_id else []

    context = {
        'sites': sites,
        'keywords': keywords,
        'selected_site_id': int(selected_site_id) if selected_site_id else None,
        'active_menu': 'keywords'
    }
    return render(request, 'seo_services/keyword_research.html', context)

@login_required
def keyword_status_api(request, site_id):
    """ وب‌سرویس ارسال وضعیت نوار پیشرفت تحقیق کلمات کلیدی به فرانت‌اَند """
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
    """ مدیریت بانک کلمات کلیدی: مجهز به حذف دائمی، فیلتر، سورت ستون‌ها و صفحه‌بندی پویای SaaS """
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
            
            # تغییر بنیادین: اگر دستور حذف آمد، ردیف را به طور کامل از دیتابیس پاک کن
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
            messages.success(request, "✍️ ردیف موضوع با موفقیت ویرایش و اصلاح شد.")
            return redirect(f'/keywords/?site_id={selected_site_id}')

    # 📊 لایه استخراج اطلاعات به همراه فیلترها و مرتب‌سازی پویای ستون‌ها
    keywords_query = KeywordResearch.objects.filter(site_id=selected_site_id) if selected_site_id else KeywordResearch.objects.none()
    
    # ۱. فیلتر کادر جستجوی متنی زنده (سرچ در عنوان یا لایه پیلار)
    search_q = request.GET.get('search', '')
    if search_q:
        keywords_query = keywords_query.filter(article_title__icontains=search_q) | keywords_query.filter(category_pillar__icontains=search_q)
        
    # ۲. فیلتر نوع Intent
    intent_f = request.GET.get('intent', 'All')
    if intent_f and intent_f != 'All':
        keywords_query = keywords_query.filter(intent=intent_f)
        
    # ۳. فیلتر وضعیت ردیف
    status_f = request.GET.get('status', 'All')
    if status_f and status_f != 'All':
        keywords_query = keywords_query.filter(status=status_f)

    # 📈 مرتب‌سازی (Sorting) پویای تمام ستون‌ها بر اساس کلیک کاربر
    sort_by = request.GET.get('sort', '-created_at')
    allowed_sorts = ['article_title', '-article_title', 'category_pillar', '-category_pillar', 'intent', '-intent', 'status', '-status', 'created_at', '-created_at']
    if sort_by in allowed_sorts:
        keywords_query = keywords_query.order_by(sort_by)
    else:
        keywords_query = keywords_query.order_by('-created_at')

    # 📄 صفحه‌بندی (Pagination) داینامیک و منعطف ابزار سئو
    per_page = int(request.GET.get('per_page', 20)) # تعداد پیش‌فرض ردیف در هر صفحه
    paginator = Paginator(keywords_query, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'sites': sites,
        'keywords': page_obj, # ارسال آبجکت صفحه‌بندی شده به جای کوئری خام
        'selected_site_id': int(selected_site_id) if selected_site_id else None,
        'search_query': search_q,
        'intent_filter': intent_f,
        'status_filter': status_f,
        'sort_by': sort_by,
        'per_page': per_page,
        'active_menu': 'keywords'
    }
    return render(request, 'seo_services/keyword_research.html', context)

@login_required
def article_factory_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        article_id = request.POST.get('article_id')
        
        if action == 'generate' and article_id:
            run_article_generation_task.delay(int(article_id))
            return JsonResponse({'status': 'queued'})
            
        # 🤖 قابلیت جدید: شلیک خودکار کارخانه و برداشتن اتوماتیک موضوع بعدی سئو شده سایت
        elif action == 'auto_generate_next':
            site_id = request.POST.get('site_id')
            img_count = int(request.POST.get('image_count', 2))
            
            # برداشتن اولین کلمه کلیدی آزاد (تایید شده یا در انتظار) این سایت
            next_topic = KeywordResearch.objects.filter(
                site_id=site_id, status__in=['approved', 'pending']
            ).order_by('created_at').first()
            
            if next_topic:
                # تغییر آنی وضعیت کلمه به 'generated' جهت تیک خوردن و عدم استفاده مجدد
                next_topic.status = 'generated'
                next_topic.save()
                
                # ایجاد ردیف کارخانه
                article = GeneratedArticle.objects.create(
                    site_id=int(site_id), keyword_ref=next_topic, title=next_topic.article_title,
                    image_count=img_count, current_step='idle', status='draft'
                )
                run_article_generation_task.delay(article.id)
                return JsonResponse({'status': 'queued', 'article_id': article.id})
            else:
                return JsonResponse({'status': 'error', 'message': 'هیچ موضوع تایید شده یا آزادی در بانک کلمات کلیدی این سایت یافت نشد!'}, status=400)
                
        elif action == 'create_manual':
            site_id = request.POST.get('site_id')
            title = request.POST.get('title')
            img_count = request.POST.get('image_count', 1)
            if site_id and title:
                GeneratedArticle.objects.create(
                    site_id=int(site_id), title=title, image_count=int(img_count), current_step='idle', status='draft'
                )
                messages.success(request, "عنوان دستی در کارخانه رزرو شد.")
        return redirect('article_factory')

    context = {
        'sites': Site.objects.all(),
        'articles': GeneratedArticle.objects.order_by('-created_at'),
        'active_menu': 'articles'
    }
    return render(request, 'seo_services/article_factory.html', context)

@login_required
def sites_management_view(request):
    if request.method == 'POST':
        site_id = request.POST.get('site_id')
        if site_id:
            site = get_object_or_404(Site, id=int(site_id))
            site.name = request.POST.get('name')
            site.domain = request.POST.get('domain')
            site.wp_url = request.POST.get('wp_url')
            site.wp_username = request.POST.get('wp_username')
            wp_pass = request.POST.get('wp_app_password')
            if wp_pass and not wp_pass.startswith('••••'):
                site.wp_app_password = wp_pass
            site.is_automation_active = request.POST.get('is_automation_active') == 'on'
            site.automation_interval_days = int(request.POST.get('automation_interval_days', 2))
            site.content_type = request.POST.get('content_type', 'educational')
            site.save()
            
            for f_type in ['keyword', 'article_text', 'article_image']:
                AIConfig.objects.update_or_create(
                    site=site, feature_type=f_type,
                    defaults={
                        'provider': request.POST.get(f'ai_provider_{f_type}'),
                        'model_name': request.POST.get(f'ai_model_{f_type}'),
                        'temperature': float(request.POST.get(f'ai_temp_{f_type}', 0.7)),
                        'max_tokens': int(request.POST.get(f'ai_tokens_{f_type}', 4000)),
                        'api_key': request.POST.get(f'ai_key_{f_type}')
                    }
                )
            messages.success(request, f"⚙️ تنظیمات سایت {site.name} با موفقیت ذخیره شد.")
        else:
            name = request.POST.get('name')
            domain = request.POST.get('domain')
            if name and domain:
                Site.objects.create(name=name, domain=domain, wp_url=request.POST.get('wp_url'), wp_username=request.POST.get('wp_username'), wp_app_password=request.POST.get('wp_app_password'))
                messages.success(request, "🌐 وب‌سایت جدید با موفقیت ایجاد شد.")
        return redirect('sites_management')

    sites_list = Site.objects.all()
    for s in sites_list:
        s.cfg_kw = AIConfig.objects.filter(site=s, feature_type='keyword').first()
        s.cfg_text = AIConfig.objects.filter(site=s, feature_type='article_text').first()
        s.cfg_img = AIConfig.objects.filter(site=s, feature_type='article_image').first()

    context = {
        'sites': sites_list,
        'active_menu': 'sites'
    }
    return render(request, 'seo_services/sites_management.html', context)