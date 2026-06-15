# apps/keyword_research/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from keyword_research.models import KeywordResearchJob
from keyword_research.serializers import KeywordResearchJobSerializer
from keyword_research.tasks import run_keyword_research_task
from sites.permissions import IsSiteMember

class KeywordResearchJobViewSet(viewsets.ModelViewSet):
    serializer_class = KeywordResearchJobSerializer
    permission_classes = [IsSiteMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin or user.is_superuser:
            return KeywordResearchJob.objects.all()
        return KeywordResearchJob.objects.filter(site__members__user=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # بررسی سطح دسترسی آبجکت مپر برای اطمینan از این که کاربر مجاز به ارسال درخواست برای این site_id است
        site_obj = serializer.validated_data['site']
        self.check_object_permissions(request, site_obj)
        
        job = serializer.save(created_by=request.user)
        
        # شلیک و هدایت تسک به Celery Worker با ساختار ناهمگام (.delay)
        run_keyword_research_task.delay(job.id)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)