from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('seo_services.urls')), # متصل کردن صفحه اصلی به داشبورد جدید شما
]