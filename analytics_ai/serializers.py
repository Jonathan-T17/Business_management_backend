from rest_framework import serializers
from .models import AnalyticsSnapshot, AIInsight

class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = "__all__"

class AIInsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIInsight
        fields = "__all__"

class SnapshotWithInsightSerializer(serializers.Serializer):
    snapshot = AnalyticsSnapshotSerializer()
    insight = AIInsightSerializer()