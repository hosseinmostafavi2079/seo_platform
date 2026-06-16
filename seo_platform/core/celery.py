import os
from celery import Celery

# تنظیم ماژول تنظیمات پیش‌فرض جنگو برای برنامه سلری
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# استفاده از رشته تنظیمات جنگو در اینجا به این معنی است که سلری
# نیازی ندارد پیکربندی‌هایش را در فایل‌های مجزا نگه دارد.
app.config_from_object('django.conf:settings', namespace='CELERY')

# لود کردن تسک‌ها از تمام Appهای نصب شده
app.autodiscover_tasks()