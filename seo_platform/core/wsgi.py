import os
from django.core.wsgi import get_wsgi_application

# تنظیم ماژول تنظیمات پیش‌فرض جنگو برای وب‌سرور
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# راه‌اندازی هندلر اصلی جا‌به‌جایی ترافیک وب جنگو
application = get_wsgi_application()