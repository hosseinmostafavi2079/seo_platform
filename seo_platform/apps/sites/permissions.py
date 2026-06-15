from rest_framework import permissions
from apps.sites.models import SiteMembership

class IsSiteMember(permissions.BasePermission):
    """
    Permission to check if the user is assigned to the site.
    Super Admins bypass this check.
    """
    def has_permission(self, request, view):
        # کاربر حتماً باید احراز هویت شده باشد
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # اگر کاربر سوپر ادمین سیستم باشد، دسترسی کامل دارد
        if request.user.is_super_admin or request.user.is_superuser:
            return True
            
        # تشخیص مدل آبجکت (خود سایت یا مدل‌های متصل به سایت)
        from apps.sites.models import Site
        site = obj if isinstance(obj, Site) else getattr(obj, 'site', None)
        
        if not site:
            return False
            
        # چک کردن وجود عضویت فعال برای کاربر در آن سایت
        return SiteMembership.objects.filter(user=request.user, site=site).exists()