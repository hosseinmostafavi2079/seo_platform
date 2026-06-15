# apps/sites/views.py
from rest_framework import viewsets
from sites.models import Site
from sites.serializers import SiteSerializer
from sites.permissions import IsSiteMember

class SiteViewSet(viewsets.ModelViewSet):
    serializer_class = SiteSerializer
    permission_classes = [IsSiteMember]

    def get_queryset(self):
        user = self.request.user
        # اگر کاربر سوپر ادمین باشد، دسترسی به تمام سایت‌ها دارد
        if user.is_super_admin or user.is_superuser:
            return Site.objects.all()
        # در غیر این صورت، فقط سایت‌هایی که کاربر عضو آن‌هاست برگشت داده می‌شود
        return Site.objects.filter(members__user=user, is_active=True)

    def perform_create(self, serializer):
        # ذخیره اتوماتیک کاربر سازنده سایت
        serializer.save(created_by=self.request.user)