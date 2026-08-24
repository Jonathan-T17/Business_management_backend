from rest_framework import serializers

from .models import (
    AnalyticsSnapshot,
    AIInsight,
    AIAnalyticsRecord,
)


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):

    class Meta:
        model = AnalyticsSnapshot
        fields = "__all__"
        read_only_fields = (
            "id",
            "company",
            "generated_at",
        )


class AIInsightSerializer(serializers.ModelSerializer):

    class Meta:
        model = AIInsight
        fields = "__all__"
        read_only_fields = (
            "id",
            "company",
            "generated_at",
            "resolved_at",
        )


class AIAnalyticsRecordSerializer(serializers.ModelSerializer):

    class Meta:
        model = AIAnalyticsRecord
        fields = "__all__"
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