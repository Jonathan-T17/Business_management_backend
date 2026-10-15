from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import timedelta
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
        # Keep calendar spacing honest: an inactive day is zero, not a missing point.
        trend_end = values.get('end_date', timezone.localdate())
        trend_start = max(values.get('start_date', trend_end - timedelta(days=29)),
                          trend_end - timedelta(days=29))
        daily = dict(submissions.filter(created_at__date__gte=trend_start,
                                        created_at__date__lte=trend_end)
                     .annotate(date=TruncDate('created_at')).values('date')
                     .annotate(value=Count('pk', distinct=True)).values_list('date', 'value'))
        trend = [{'date': trend_start + timedelta(days=offset),
                  'value': daily.get(trend_start + timedelta(days=offset), 0)}
                 for offset in range((trend_end - trend_start).days + 1)]
        branch_activity = list(submissions.exclude(status__in=['DRAFT', 'CANCELLED'])
                               .values('branch_id', 'branch__name').annotate(
                                   total=Count('pk', distinct=True),
                                   awaiting_review=Count('pk', filter=Q(status__in=['SUBMITTED', 'UNDER_REVIEW']), distinct=True),
                                   approved=Count('pk', filter=Q(status='APPROVED'), distinct=True),
                                   returned=Count('pk', filter=Q(status='RETURNED'), distinct=True),
                               ).order_by('-total', 'branch__name', 'branch_id'))
        for item in branch_activity:
            item['name'] = item.pop('branch__name') or 'No branch recorded'
            item['other'] = item['total'] - item['awaiting_review'] - item['approved'] - item['returned']
        waiting = submissions.filter(status__in=['SUBMITTED', 'UNDER_REVIEW'])
        now = timezone.now()
        review_age = [
            {'label': 'Under 2 days', 'value': waiting.filter(submitted_at__gt=now - timedelta(days=2)).count()},
            {'label': '2–7 days', 'value': waiting.filter(submitted_at__lte=now - timedelta(days=2), submitted_at__gt=now - timedelta(days=7)).count()},
            {'label': '7 days or more', 'value': waiting.filter(submitted_at__lte=now - timedelta(days=7)).count()},
            {'label': 'Date not recorded', 'value': waiting.filter(submitted_at__isnull=True).count()},
        ]
        from forms_engine.models import MaterialJourney
        from forms_engine.materials import journey_status
        material_counts = {label: 0 for label in ('Awaiting review', 'Awaiting delivery',
                                                 'Partial fulfillment', 'Completed',
                                                 'Returned', 'Rejected', 'Cancelled')}
        journeys = MaterialJourney.objects.filter(
            submission__in=submissions.exclude(status='DRAFT')
        ).select_related('submission').prefetch_related('movements')
        for journey in journeys.iterator(chunk_size=200):
            material_counts[journey_status(journey)] += 1
        return Response({'metrics': [
            {'key':'submissions','label':'Form submissions','value':submissions.count()},
            {'key':'review','label':'Submissions awaiting review','value':submission_counts['submitted'] + submission_counts['under_review']},
            {'key':'approved','label':'Approved submissions','value':submission_counts['approved']},
            {'key':'requests','label':'Requests awaiting review','value':request_counts['submitted'] + request_counts['under_review']},
        ], 'tasks':counts, 'requests':request_counts, 'submissions':submission_counts,
           'submission_trend':trend, 'branch_activity': branch_activity,
           'review_age': review_age, 'materials': material_counts})
