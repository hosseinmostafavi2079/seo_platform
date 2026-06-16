from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='user_dashboard'),
    path('keywords/', views.keyword_research_view, name='keyword_research'),
    path('articles/', views.article_factory_view, name='article_factory'),
    path('sites/', views.sites_management_view, name='sites_management'),
]