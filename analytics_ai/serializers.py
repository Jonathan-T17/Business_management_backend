from rest_framework import serializers

from .models import (
    AnalyticsSnapshot,
    AIInsight,
    AIAnalyticsRecord,
)


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnalyticsSnapshot
        fields = ('id', 'snapshot_type', 'total_tasks', 'completed_tasks', 'pending_tasks', 'in_progress_tasks', 'blocked_tasks', 'overdue_tasks', 'total_projects', 'active_projects', 'total_reports', 'total_comments', 'completion_rate', 'overdue_rate', 'collaboration_score', 'workload_balance_score', 'ai_summary', 'generated_at', 'company', 'branch', 'project')
        read_only_fields = (
            "id",
            "company",
            "generated_at",
        )


class AIInsightSerializer(serializers.ModelSerializer):

    class Meta:
        model = AIInsight
        fields = ('id', 'insight_type', 'severity', 'status', 'title', 'summary', 'metrics', 'generated_at', 'resolved_at', 'company', 'branch', 'project', 'user')
        read_only_fields = (
            "id",
            "company",
            "generated_at",
            "resolved_at",
        )


class AIAnalyticsRecordSerializer(serializers.ModelSerializer):

    class Meta:
        model = AIAnalyticsRecord
        fields = ('id', 'level', 'summary', 'metrics', 'generated_at', 'company', 'branch', 'project', 'user')
        read_only_fields = (
            "id",
            "company",
            "generated_at",
        )


class SnapshotWithInsightSerializer(serializers.Serializer):

    snapshot = AnalyticsSnapshotSerializer()

    insight = AIInsightSerializer(
        allow_null=True
    )