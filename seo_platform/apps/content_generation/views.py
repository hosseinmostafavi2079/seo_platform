# apps/content_generation/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from content_generation.models import ArticleJob
from content_generation.serializers import ArticleJobSerializer
from content_generation.tasks import generate_article_task
from sites.permissions import IsSiteMember

class ArticleJobViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleJobSerializer
    permission_classes = [IsSiteMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin or user.is_superuser:
            return ArticleJob.objects.all()
        return ArticleJob.objects.filter(site__members__user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        site_obj = serializer.validated_data['site']
        self.check_object_permissions(request, site_obj)
        
        job = serializer.save(created_by=request.user)
        
        # ارجاع فرآیند سنگین تولید متن و تصویر به پس‌زمینه کانتینر ورکر
        generate_article_task.delay(job.id)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)