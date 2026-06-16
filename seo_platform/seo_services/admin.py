import csv
import requests
from django.contrib import admin
from django.http import HttpResponse
from django_jalali.admin.filters import JDateFieldListFilter
from .models import Site, SiteAccess, AIConfig, KeywordResearch, GeneratedArticle
from .tasks import run_keyword_research_task, run_article_generation_task

# اکشن فاز ۵: خروجی اکسل کلمات کلیدی
@admin.action(description='خروجی اکسل (CSV) از موارد انتخاب شده')
def export_keywords_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="seo_keyword_research.csv"'
    writer = csv.writer(response)
    writer.writerow(['کلمه کلیدی مرجع', 'سایت مربوطه', 'هدف جستجو (Intent)', 'دسته‌بندی مادر (Pillar)', 'عنوان مقاله پیشنهادی خوشه‌ای', 'وضعیت تایید'])
    for obj in queryset:
        writer.writerow([obj.keyword, obj.site.name, obj.get_intent_display(), obj.category_pillar, obj.article_title, obj.get_status_display()])
    return response

# اکشن فاز ۶: انتقال اتوماتیک کلمات کلیدی به کارخانه محتوا و شروع تولید خودکار اسلاگ و متن
@admin.action(description='انتقال عناوین انتخابی به کارخانه تولید مقاله')
def move_to_article_factory(modeladmin, request, queryset):
    for kw in queryset:
        article = GeneratedArticle.objects.create(
            site=kw.site,
            keyword_ref=kw,
            title=kw.article_title,
            slug='',
            content='',
            status='draft'
        )
        run_article_generation_task.delay(article.id)
    modeladmin.message_user(request, f"تعداد {queryset.count()} عنوان به صف سلری منتقل شدند. هوش مصنوعی در حال تولید محتوا، اسلاگ و متادسکریپشن است.")

# اکشن جدید: تولید یا بازنویسی هوشمند مقالات دستی
@admin.action(description='🤖 فرمان به هوش مصنوعی: تولید/تکمیل محتوا و اسلاگ برای موارد انتخابی')
def trigger_ai_generation_for_manual_posts(modeladmin, request, queryset):
    for article in queryset:
        run_article_generation_task.delay(article.id)
    modeladmin.message_user(request, f"فرمان تولید محتوا برای {queryset.count()} مورد صادر شد. تا دقایقی دیگر فیلدهای متن، اسلاگ و تصاویر خودکار پر می‌شوند.")

# اکشن فاز ۶ اصلاح شده: انتشار آنی یا زمان‌بندی شده هوشمند در وردپرس بر اساس تاریخ شمسی
@admin.action(description='🚀 تایید نهایی؛ ارسال و انتشار مستقیم در وردپرس (آنی یا زمان‌بندی)')
def publish_to_wordpress_action(modeladmin, request, queryset):
    success_count = 0
    for article in queryset:
        site = article.site
        
        # ۱. آپلود تصویر شاخص اختصاصی هوش مصنوعی در وردپرس
        featured_media_id = None
        if article.featured_image_url and article.featured_image_url.startswith('http'):
            try:
                img_data = requests.get(article.featured_image_url, timeout=20).content
                wp_media_url = f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/media"
                headers = {
                    "Content-Disposition": f'attachment; filename="featured-{article.id}.jpg"',
                    "Content-Type": "image/jpeg"
                }
                media_res = requests.post(wp_media_url, auth=(site.wp_username, site.wp_app_password), headers=headers, data=img_data, timeout=30)
                if media_res.status_code == 201:
                    featured_media_id = media_res.json().get('id')
            except Exception as e:
                print(f"خطا در آپلود رسانه: {str(e)}")

        # ۲. مدیریت هوشمند انتشار آنی یا زمان‌بندی آینده
        wp_posts_url = f"{site.wp_url.rstrip('/')}/wp-json/wp/v2/posts"
        post_payload = {
            "title": article.title,
            "slug": article.slug,
            "content": article.content,
            "featured_media": featured_media_id
        }
        
        # اگر تاریخ انتشار شمسی در آینده تنظیم شده باشد، تبدیل به میلادی شده و به عنوان کارهای زمان‌بندی شده به وردپرس پاس داده می‌شود
        if article.published_at:
            gregorian_dt = article.published_at.togregorian()
            post_payload["date"] = gregorian_dt.isoformat()
            post_payload["status"] = "future"  # وضعیت زمان‌بندی شده در وردپرس
        else:
            post_payload["status"] = "publish"  # انتشار درجا و آنی

        try:
            post_res = requests.post(wp_posts_url, auth=(site.wp_username, site.wp_app_password), json=post_payload, timeout=20)
            if post_res.status_code in [200, 201]:
                article.wp_post_id = post_res.json().get('id')
                article.status = 'published' if not article.published_at else 'sent_to_wp'
                article.save()
                success_count += 1
        except Exception as e:
            print(f"خطا در ارتباط با وردپرس: {str(e)}")
            
    modeladmin.message_user(request, f"تعداد {success_count} مقاله با موفقیت پردازش و بر روی وردپرس اعمال شدند.")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'created_at')
    search_fields = ('name', 'domain')
    list_filter = (('created_at', JDateFieldListFilter),)

@admin.register(SiteAccess)
class SiteAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'site', 'role')
    list_filter = ('role', 'site')

@admin.register(AIConfig)
class AIConfigAdmin(admin.ModelAdmin):
    list_display = ('site', 'feature_type', 'provider', 'model_name', 'temperature')
    list_filter = ('feature_type', 'provider', 'site')

@admin.register(KeywordResearch)
class KeywordResearchAdmin(admin.ModelAdmin):
    list_display = ('article_title', 'site', 'intent', 'category_pillar', 'status', 'created_at')
    list_filter = ('status', 'intent', 'site', ('created_at', JDateFieldListFilter))
    search_fields = ('article_title', 'keyword')
    list_editable = ('status',)
    actions = [export_keywords_as_csv, move_to_article_factory]

@admin.register(GeneratedArticle)
class GeneratedArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'site', 'status', 'created_at', 'published_at')
    list_filter = ('status', 'site', ('created_at', JDateFieldListFilter), ('published_at', JDateFieldListFilter))
    search_fields = ('title', 'slug')
    list_editable = ('status',)
    # دکمه‌های مدیریت تولید آنی هوش مصنوعی و زمان‌بندی انتشار وردپرس
    actions = [trigger_ai_generation_for_manual_posts, publish_to_wordpress_action]