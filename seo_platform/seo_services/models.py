from django.db import models
from django.contrib.auth.models import User
from django_jalali.db import models as jmodels

class Site(models.Model):
    name = models.CharField(max_length=255, verbose_name="نام سایت")
    domain = models.URLField(unique=True, verbose_name="آدرس دامنه")
    wp_url = models.URLField(verbose_name="آدرس API وردپرس")
    wp_username = models.CharField(max_length=150, verbose_name="نام کاربری وردپرس")
    wp_app_password = models.CharField(max_length=255, verbose_name="رمز عبور اپلیکیشن وردپرس")
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت در سیستم")

    is_automation_active = models.BooleanField(default=False, verbose_name="اتوماسیون زمان‌بندی فعال است؟")
    automation_interval_days = models.IntegerField(default=2, verbose_name="فاصله زمانی تولید خودکار (روز)")
    content_type = models.CharField(
        max_length=100, default='educational', 
        choices=[
            ('educational', 'آموزشی و راهنما (Educational)'),
            ('commercial', 'بررسی محصول و تجاری (Commercial)'),
            ('news', 'خبری و ترند روز (News)'),
            ('corporate', 'شرکتی و معرفی خدمات (Corporate)')
        ],
        verbose_name="نوع و ساختار پیش‌فرض محتوا"
    )

    # 📊 فیلدهای جدید پایش زنده نوار پیشرفت تحقیق کلمات کلیدی
    KEYWORD_STEP_CHOICES = [
        ('idle', 'در انتظار شروع تحقیق کلمات'),
        ('serper', '🔍 ۱. اسکرپ زنده نتایج گوگل و ردیابی کانتنت‌گپ رقبا'),
        ('llm', '🧠 ۲. پردازش مهندسی هوش مصنوعی و استخراج خوشه‌های محتوایی'),
        ('saving', '📦 ۳. سازمان‌دهی و ذخیره‌سازی ساختار یافته عناوین در دیتابیس'),
        ('success', '✅ ۴. فرآیند تحقیق کلمات با موفقیت پایان یافت'),
        ('failed', '❌ خطا در فرآیند تحقیق کلمات کلیدی'),
    ]
    keyword_current_step = models.CharField(max_length=30, choices=KEYWORD_STEP_CHOICES, default='idle', verbose_name="مرحله فعلی تحقیق کلمات")
    keyword_error_log = models.TextField(blank=True, null=True, verbose_name="لاگ خطای تحقیق کلمات")

    class Meta:
        verbose_name = "سایت"
        verbose_name_plural = "۱. سایت‌ها"

    def __str__(self):
        return self.name

class SiteAccess(models.Model):
    ROLE_CHOICES = [('admin', 'مدیر سایت'), ('editor', 'نویسنده / ویرایشگر')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="site_permissions", verbose_name="کاربر")
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="authorized_users", verbose_name="سایت")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='editor', verbose_name="سطح دسترسی")

    class Meta:
        verbose_name = "دسترسی کاربر"
        verbose_name_plural = "۲. سطوح دسترسی کاربران"
        unique_together = ('user', 'site')

class AIConfig(models.Model):
    # تفکیک دقیق فرآیندها طبق خواسته شما برای استفاده از هوش مصنوعی‌های مجزا در متن و عکس
    FEATURE_CHOICES = [
        ('keyword', 'تحقیق کلمات کلیدی'),
        ('article_text', 'تولید متن مقاله'),
        ('article_image', 'تولید تصویر مقاله'),
    ]
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI (Direct)'),
        ('gapgpt', 'GapGPT API'),
        ('gemini', 'Google Gemini'),
    ]
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="ai_configs", verbose_name="سایت")
    feature_type = models.CharField(max_length=20, choices=FEATURE_CHOICES, verbose_name="نوع فرآیند")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='gapgpt', verbose_name="پرووایدر هوش مصنوعی")
    model_name = models.CharField(max_length=100, default='gpt-5-mini', verbose_name="نام دقیق مدل")
    temperature = models.FloatField(default=0.7, verbose_name="میزان خلاقیت (Temperature)")
    max_tokens = models.IntegerField(default=4000, verbose_name="حداکثر توکن مصرفی")
    api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name="کلید API اختصاصی")

    class Meta:
        verbose_name = "تنظیمات هوش مصنوعی"
        verbose_name_plural = "۳. تنظیمات هوش مصنوعی سایت‌ها"
        unique_together = ('site', 'feature_type')

class KeywordResearch(models.Model):
    INTENT_CHOICES = [
        ('Informational', 'اطلاعاتی (Informational)'),
        ('Commercial', 'تجاری (Commercial)'),
        ('Transactional', 'معاملاتی (Transactional)'),
        ('Navigational', 'ناوبری (Navigational)'),
    ]
    # افزودن وضعیت 'generated' برای جلوگیری از تولید محتوای تکراری
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('approved', 'تایید شده'),
        ('generated', 'مقاله تولید شده 📝'),
        ('deleted', 'حذف شده'),
    ]
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="keywords", verbose_name="سایت")
    keyword = models.CharField(max_length=255, verbose_name="کلمه کلیدی")
    intent = models.CharField(max_length=50, choices=INTENT_CHOICES, verbose_name="هدف جستجو (Intent)")
    category_pillar = models.CharField(max_length=255, verbose_name="دسته‌بندی مادر (Pillar Page)")
    article_title = models.CharField(max_length=500, verbose_name="عنوان مقاله پیشنهادی خوشه‌ای")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ تولید")

    class Meta:
        verbose_name = "دیتای کیورد ریسرچ"
        verbose_name_plural = "۴. بانک کلمات کلیدی و عناوین"

    def __str__(self):
        return self.article_title

class GeneratedArticle(models.Model):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس در پلتفرم'),
        ('sent_to_wp', 'ارسال شده به وردپرس (Draft)'),
        ('published', 'منتشر شده روی سایت'),
    ]
    # وضعیت‌های استپر نوار پیشرفت زنده کارخانه تولید محتوا
    STEP_CHOICES = [
        ('idle', 'در انتظار شروع پردازش'),
        ('links', '🔗 ۱. در حال استخراج و تحلیل لینک‌های داخلی وردپرس'),
        ('text', '✍️ ۲. در حال نگارش متن جامع و تگ‌های متای سئو'),
        ('images', '🖼️ ۳. در حال طراحی تصاویر اختصاصی مدیا با هوش مصنوعی'),
        ('assembly', '📦 ۴. در حال ساختاردهی نهایی و تزریق کدهای HTML'),
        ('success', '✅ ۵. عملیات تولید با موفقیت کامل پایان یافت'),
        ('failed', '❌ خطا در فرآیند تولید محتوا'),
    ]
    
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="articles", verbose_name="سایت")
    keyword_ref = models.ForeignKey(KeywordResearch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="کلمه کلیدی مرجع")
    title = models.CharField(max_length=255, verbose_name="عنوان مقاله")
    slug = models.CharField(max_length=255, blank=True, verbose_name="اسلاگ (URL)")
    content = models.TextField(blank=True, verbose_name="متن کامل مقاله")
    seo_title = models.CharField(max_length=255, blank=True, null=True, verbose_name="عنوان سئو")
    seo_description = models.TextField(blank=True, null=True, verbose_name="متا دسکریپشن")
    image_count = models.IntegerField(default=1, verbose_name="تعداد تصاویر مابین متن")
    featured_image_url = models.URLField(blank=True, null=True, verbose_name="لینک تصویر شاخص")
    wp_post_id = models.IntegerField(blank=True, null=True, verbose_name="شناسه پست در وردپرس")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت انتشار")
    
    # فیلدهای جدید مدیریت وضعیت نوار پیشرفت زنده و لاگ دقیق خطاها
    current_step = models.CharField(max_length=30, choices=STEP_CHOICES, default='idle', verbose_name="مرحله فعلی تولید")
    error_log = models.TextField(blank=True, null=True, verbose_name="گزارش دقیق خطا برای اصلاح کاربر")
    
    created_at = jmodels.jDateTimeField(auto_now_add=True, verbose_name="تاریخ تولید")
    published_at = jmodels.jDateTimeField(blank=True, null=True, verbose_name="تاریخ انتشار زمان‌بندی شده")

    class Meta:
        verbose_name = "مقاله تولید شده"
        verbose_name_plural = "۵. کارخانه تولید مقاله"

    def __str__(self):
        return self.title