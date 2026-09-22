from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from core.capabilities import Capabilities
from core.capability_service import CapabilityService
from core.visibility import VisibilityService
from subscriptions.services import SubscriptionService


class OverviewFilters(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    branch = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        if attrs.get('start_date') and attrs.get('end_date') and attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError('End date must be on or after start date.')
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError('Unsupported analytics filter.')
        return attrs


class AnalyticsOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not CapabilityService.is_tenant_identity(user) or not any(CapabilityService.has(user, capability) for capability in (Capabilities.VIEW_COMPANY_ANALYTICS, Capabilities.VIEW_EXECUTIVE_DASHBOARD)):
            raise PermissionDenied('Analytics access is required.')
        SubscriptionService.require_active(user.company)
        filters = OverviewFilters(data=request.query_params)
        filters.is_valid(raise_exception=True)
        values = filters.validated_data
        from tasks.models import Task
        from projects.models import Project
        from requests_app.models import BusinessRequest
        from companies.models import Branch
        from forms_engine.models import FormSubmission
        tasks = VisibilityService.tasks_queryset(user=user, queryset=Task.objects.filter(is_active=True))
        projects = VisibilityService.projects_queryset(user=user, queryset=Project.objects.all())
        requests = VisibilityService.business_requests_queryset(user=user, queryset=BusinessRequest.objects.all())
        submissions = VisibilityService.form_submissions_queryset(user=user, queryset=FormSubmission.objects.all())
        if not (CapabilityService.has_company(user,Capabilities.VIEW_COMPANY_ANALYTICS) or CapabilityService.has_company(user,Capabilities.VIEW_EXECUTIVE_DASHBOARD)):
            from core.position_scope import PositionScope
            scope=PositionScope.branches_for(user,Capabilities.VIEW_COMPANY_ANALYTICS)
            tasks=tasks.filter(project__branches__id__in=scope).distinct()
            projects=projects.filter(branches__id__in=scope).distinct()
            requests=requests.filter(branch_id__in=scope)
            submissions=submissions.filter(branch_id__in=scope)
        if 'branch' in values:
            branch = values['branch']
            if not Branch.objects.filter(pk=branch, company=user.company).exists():
                raise serializers.ValidationError({'branch': 'Choose a branch in your company.'})
            tasks = tasks.filter(project__branches=branch)
            projects = projects.filter(branches=branch)
            requests = requests.filter(branch_id=branch)
            submissions = submissions.filter(branch_id=branch)
        querysets = [tasks, projects, requests, submissions]
        for index, queryset in enumerate(querysets):
            if 'start_date' in values:
                queryset = queryset.filter(created_at__date__gte=values['start_date'])
            if 'end_date' in values:
                queryset = queryset.filter(created_at__date__lte=values['end_date'])
            querysets[index] = queryset.distinct()
        tasks, projects, requests, submissions = querysets
        counts = tasks.aggregate(total=Count('pk', distinct=True), todo=Count('pk',filter=Q(status='pending'),distinct=True), in_progress=Count('pk',filter=Q(status='in_progress'),distinct=True), done=Count('pk',filter=Q(status='done'),distinct=True), overdue=Count('pk',filter=~Q(status='done') & Q(due_date__lt=timezone.localdate()),distinct=True))
        request_counts = {name.lower(): requests.filter(status=name).count() for name in ('SUBMITTED','UNDER_REVIEW','APPROVED','REJECTED','FULFILLED')}
        submission_counts = {name.lower(): submissions.filter(status=name).count()
                             for name, _ in FormSubmission.STATUS_CHOICES}
        trend = list(submissions.annotate(date=TruncDate('created_at')).values('date')
                     .annotate(value=Count('pk', distinct=True)).order_by('-date')[:30])
        trend.reverse()
        return Response({'metrics': [
            {'key':'submissions','label':'Form submissions','value':submissions.count()},
            {'key':'review','label':'Submissions awaiting review','value':submission_counts['submitted'] + submission_counts['under_review']},
            {'key':'approved','label':'Approved submissions','value':submission_counts['approved']},
            {'key':'requests','label':'Requests awaiting review','value':request_counts['submitted'] + request_counts['under_review']},
        ], 'tasks':counts, 'requests':request_counts, 'submissions':submission_counts,
           'submission_trend':trend})
