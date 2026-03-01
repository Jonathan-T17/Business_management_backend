from rest_framework import serializers
from .models import Company, Branch, CompanyInvite


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"


class CompanyInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyInvite
        fields = "__all__"
        read_only_fields = ("token", "is_used", "created_at")