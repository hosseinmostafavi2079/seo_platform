from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='user_dashboard'),
    path('keywords/', views.keyword_research_view, name='keyword_research'),
    path('articles/', views.article_factory_view, name='article_factory'),
    path('sites/', views.sites_management_view, name='sites_management'),
    path('api/article-status/<int:article_id>/', views.article_status_api, name='article_status_api'),
    path('api/keyword-status/<int:site_id>/', views.keyword_status_api, name='keyword_status_api'),
]