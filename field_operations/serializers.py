from rest_framework import serializers
from .models import FieldActivity, FieldStop, FieldStopMetric


class FieldStopMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldStopMetric
        fields = ("id", "key", "label", "numeric_value", "text_value", "unit")


class FieldStopSerializer(serializers.ModelSerializer):
    metrics = FieldStopMetricSerializer(many=True, required=False)

    class Meta:
        model = FieldStop
        fields = (
            "id", "activity", "sequence", "stop_type", "client_name",
            "location_name", "address", "contact_name", "contact_phone",
            "status", "planned_arrival", "arrived_at", "completed_at",
            "latitude", "longitude", "notes", "form_submission", "metrics",
            "created_at",
        )
        read_only_fields = ("status", "arrived_at", "completed_at", "created_at")

    def validate(self, attrs):
        request = self.context["request"]
        activity = attrs.get("activity")

        # SUPERUSER bypass
        if (
            activity
            and request.user.role != "SUPERUSER"
            and activity.company_id != request.user.company_id
        ):
            raise serializers.ValidationError(
                {"activity": "Activity belongs to another company."}
            )
        return attrs

    def create(self, validated_data):
        metrics_data = validated_data.pop("metrics", [])
        stop = FieldStop.objects.create(**validated_data)
        for metric in metrics_data:
            FieldStopMetric.objects.create(stop=stop, **metric)
        return stop


class FieldActivitySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    stops = FieldStopSerializer(many=True, read_only=True)

    class Meta:
        model = FieldActivity
        fields = (
            "id", "company", "branch", "branch_name", "department",
            "department_name", "employee", "employee_name", "activity_type",
            "title", "description", "activity_date", "status", "project", "task",
            "vehicle_reference", "started_at", "completed_at",
            "started_latitude", "started_longitude", "completed_latitude",
            "completed_longitude", "created_by", "created_at", "updated_at",
            "stops",
        )
        read_only_fields = (
            "company", "created_by", "status", "started_at", "completed_at",
            "started_latitude", "started_longitude", "completed_latitude",
            "completed_longitude", "created_at", "updated_at",
        )

    def validate(self, attrs):
        request = self.context["request"]
        company_id = request.user.company_id
        if company_id is None:
            raise serializers.ValidationError(
                "Field operations require a tenant company context."
            )

        # Loop through related fields for concise validation
        for name in ("employee", "branch", "department", "project", "task"):
            value = attrs.get(name)
            if value and value.company_id != company_id:
                raise serializers.ValidationError(
                    {name: f"{name.replace('_', ' ').title()} belongs to another company."}
                )

        # Ensure task belongs to project
        task = attrs.get("task")
        project = attrs.get("project")
        if task and project and task.project_id != project.id:
            raise serializers.ValidationError(
                {"task": "Task does not belong to the selected project."}
            )
        return attrs




# from rest_framework import serializers

# from .models import (
#     FieldActivity,
#     FieldStop,
#     FieldStopMetric,
# )


# class FieldStopMetricSerializer(
#     serializers.ModelSerializer
# ):

#     class Meta:
#         model = FieldStopMetric

#         fields = (
#             "id",
#             "key",
#             "label",
#             "numeric_value",
#             "text_value",
#             "unit",
#         )


# class FieldStopSerializer(
#     serializers.ModelSerializer
# ):

#     metrics = FieldStopMetricSerializer(
#         many=True,
#         required=False,
#     )

#     class Meta:
#         model = FieldStop

#         fields = (
#             "id",
#             "activity",

#             "sequence",
#             "stop_type",

#             "client_name",
#             "location_name",
#             "address",

#             "contact_name",
#             "contact_phone",

#             "status",

#             "planned_arrival",
#             "arrived_at",
#             "completed_at",

#             "latitude",
#             "longitude",

#             "notes",

#             "form_submission",

#             "metrics",

#             "created_at",
#         )

#         read_only_fields = (
#             "status",
#             "arrived_at",
#             "completed_at",
#             "created_at",
#         )

#     def validate(self, attrs):

#         request = self.context[
#             "request"
#         ]

#         activity = attrs.get(
#             "activity"
#         )

#         if (
#             activity
#             and request.user.role
#             != "SUPERUSER"
#             and activity.company_id
#             != request.user.company_id
#         ):
#             raise serializers.ValidationError(
#                 "Activity belongs to "
#                 "another company."
#             )

#         return attrs

#     def create(
#         self,
#         validated_data,
#     ):

#         metrics_data = (
#             validated_data.pop(
#                 "metrics",
#                 [],
#             )
#         )

#         stop = FieldStop.objects.create(
#             **validated_data
#         )

#         for metric in metrics_data:

#             FieldStopMetric.objects.create(
#                 stop=stop,
#                 **metric,
#             )

#         return stop


# class FieldActivitySerializer(
#     serializers.ModelSerializer
# ):

#     employee_name = serializers.CharField(
#         source="employee.full_name",
#         read_only=True,
#     )

#     branch_name = serializers.CharField(
#         source="branch.name",
#         read_only=True,
#     )

#     department_name = serializers.CharField(
#         source="department.name",
#         read_only=True,
#     )

#     stops = FieldStopSerializer(
#         many=True,
#         read_only=True,
#     )

#     class Meta:
#         model = FieldActivity

#         fields = "__all__"

#         read_only_fields = (
#             "company",
#             "created_by",

#             "status",

#             "started_at",
#             "completed_at",

#             "started_latitude",
#             "started_longitude",

#             "completed_latitude",
#             "completed_longitude",

#             "created_at",
#             "updated_at",
#         )

#     def validate(self, attrs):

#         request = self.context[
#             "request"
#         ]

#         company = request.user.company

#         employee = attrs.get(
#             "employee"
#         )

#         branch = attrs.get(
#             "branch"
#         )

#         department = attrs.get(
#             "department"
#         )

#         project = attrs.get(
#             "project"
#         )

#         task = attrs.get(
#             "task"
#         )

#         if (
#             employee
#             and employee.company_id
#             != company.id
#         ):
#             raise serializers.ValidationError({
#                 "employee":
#                     "Employee belongs to another company."
#             })

#         if (
#             branch
#             and branch.company_id
#             != company.id
#         ):
#             raise serializers.ValidationError({
#                 "branch":
#                     "Branch belongs to another company."
#             })

#         if (
#             department
#             and department.company_id
#             != company.id
#         ):
#             raise serializers.ValidationError({
#                 "department":
#                     "Department belongs to another company."
#             })

#         if (
#             project
#             and project.company_id
#             != company.id
#         ):
#             raise serializers.ValidationError({
#                 "project":
#                     "Project belongs to another company."
#             })

#         if (
#             task
#             and task.company_id
#             != company.id
#         ):
#             raise serializers.ValidationError({
#                 "task":
#                     "Task belongs to another company."
#             })

#         if (
#             task
#             and project
#             and task.project_id
#             != project.id
#         ):
#             raise serializers.ValidationError({
#                 "task":
#                     "Task does not belong "
#                     "to the selected project."
#             })

#         return attrs





# from rest_framework import serializers

# from .models import FieldActivity, FieldStop, FieldStopMetric


# class FieldStopMetricSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = FieldStopMetric
#         fields = ("id", "key", "label", "numeric_value", "text_value", "unit")


# class FieldStopSerializer(serializers.ModelSerializer):
#     metrics = FieldStopMetricSerializer(many=True, required=False)

#     class Meta:
#         model = FieldStop
#         fields = (
#             "id", "activity", "sequence", "stop_type", "client_name",
#             "location_name", "address", "contact_name", "contact_phone",
#             "status", "planned_arrival", "arrived_at", "completed_at",
#             "latitude", "longitude", "notes", "form_submission", "metrics",
#             "created_at",
#         )
#         read_only_fields = ("status", "arrived_at", "completed_at", "created_at")

#     def validate(self, attrs):
#         request = self.context["request"]
#         activity = attrs.get("activity")
#         if activity and activity.company_id != request.user.company_id:
#             raise serializers.ValidationError(
#                 {"activity": "Activity belongs to another company."}
#             )
#         return attrs

#     def create(self, validated_data):
#         metrics_data = validated_data.pop("metrics", [])
#         stop = FieldStop.objects.create(**validated_data)
#         for metric in metrics_data:
#             FieldStopMetric.objects.create(stop=stop, **metric)
#         return stop


# class FieldActivitySerializer(serializers.ModelSerializer):
#     employee_name = serializers.CharField(source="employee.full_name", read_only=True)
#     branch_name = serializers.CharField(source="branch.name", read_only=True)
#     department_name = serializers.CharField(source="department.name", read_only=True)
#     stops = FieldStopSerializer(many=True, read_only=True)

#     class Meta:
#         model = FieldActivity
#         fields = (
#             "id", "company", "branch", "branch_name", "department",
#             "department_name", "employee", "employee_name", "activity_type",
#             "title", "description", "activity_date", "status", "project", "task",
#             "vehicle_reference", "started_at", "completed_at",
#             "started_latitude", "started_longitude", "completed_latitude",
#             "completed_longitude", "created_by", "created_at", "updated_at",
#             "stops",
#         )
#         read_only_fields = (
#             "company", "created_by", "status", "started_at", "completed_at",
#             "started_latitude", "started_longitude", "completed_latitude",
#             "completed_longitude", "created_at", "updated_at",
#         )

#     def validate(self, attrs):
#         request = self.context["request"]
#         company_id = request.user.company_id
#         if company_id is None:
#             raise serializers.ValidationError(
#                 "Field operations require a tenant company context."
#             )

#         for name in ("employee", "branch", "department", "project", "task"):
#             value = attrs.get(name)
#             if value and value.company_id != company_id:
#                 raise serializers.ValidationError(
#                     {name: f"{name.replace('_', ' ').title()} belongs to another company."}
#                 )

#         task = attrs.get("task")
#         project = attrs.get("project")
#         if task and project and task.project_id != project.id:
#             raise serializers.ValidationError(
#                 {"task": "Task does not belong to the selected project."}
#             )
#         return attrs
