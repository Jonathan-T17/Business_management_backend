from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Report, ReportComment
from .serializers import ReportSerializer, ReportCommentSerializer
from .permissions import can_view_report
from activity.models import ActivityLog
from rest_framework.decorators import action
from rest_framework.response import Response




class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Base filter by company
        reports = Report.objects.filter(company=user.company)

        # Apply fine-grained visibility check
        visible_reports = [
            r.id for r in reports if can_view_report(user, r)
        ]

        return Report.objects.filter(id__in=visible_reports)

    def perform_create(self, serializer):
        # Save with ownership and organizational context
        report = serializer.save(
            created_by=self.request.user,
            company=self.request.user.company,
            branch=self.request.user.branch
        )

        # Audit log entry for traceability
        ActivityLog.objects.create(
            company=report.company,
            project=report.project,
            task=report.task,
            user=self.request.user,
            action="REPORT_SUBMITTED",
            metadata={
                "type": report.report_type,
                "title": report.title
            }
        )


    


    @action(detail=False, methods=["get"])
    def company_feed(self, request):
    
        reports = Report.objects.filter(
            company=request.user.company
        ).order_by("-created_at")[:20]
    
        serializer = self.get_serializer(reports, many=True)
    
        return Response(serializer.data)

        






class ReportCommentViewSet(viewsets.ModelViewSet):
    serializer_class = ReportCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Base filter by company
        comments = ReportComment.objects.filter(report__company=user.company)

        # Apply fine-grained visibility check on parent report
        visible_comments = [
            c.id for c in comments if can_view_report(user, c.report)
        ]

        return ReportComment.objects.filter(id__in=visible_comments)

    def perform_create(self, serializer):
        # Save with ownership context
        comment = serializer.save(author=self.request.user)

        # Audit log entry for traceability
        ActivityLog.objects.create(
            company=comment.report.company,
            project=comment.report.project,
            task=comment.report.task,
            user=self.request.user,
            action="COMMENT_ADDED",
            metadata={
                "report_id": comment.report.id,
                "comment_id": comment.id,
                "content_preview": comment.content[:100]  # safe preview
            }
        )