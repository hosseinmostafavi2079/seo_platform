# config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# ایمپورت ویوست‌های توسعه داده شده اپ‌ها
from sites.views import SiteViewSet
from keyword_research.views import KeywordResearchJobViewSet
from content_generation.views import ArticleJobViewSet

router = DefaultRouter()
router.register(r'sites', SiteViewSet, basename='site')
router.register(r'keyword-research', KeywordResearchJobViewSet, basename='keyword-research')
router.register(r'articles', ArticleJobViewSet, basename='articles')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # اندپوینت‌های اصلی دایرکتوری API نسخه ۱ پلتفرم
    path('api/v1/', include(router.urls)),
    
    # سیستم احراز هویت متمرکز و امن توکن‌های چرخشی JWT
    path('api/v1/auth/login/', TokenObtainPairView.as_callable(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_callable(), name='token_refresh'),
]