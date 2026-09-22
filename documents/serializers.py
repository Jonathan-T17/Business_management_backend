from django.contrib.contenttypes.models import (
    ContentType,
)

from rest_framework import serializers

from .models import (
    Attachment,
    DocumentCategory,
    Document,
    DocumentVersion,
)

from .services import (
    MAX_ATTACHMENT_SIZE,
    MAX_DOCUMENT_SIZE,
    validate_uploaded_file,
    validate_attachment_target,
)
from subscriptions.services import SubscriptionService


# ============================================================
# Attachment
# ============================================================

class AttachmentSerializer(
    serializers.ModelSerializer
):

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.content_type.app_label == 'forms_engine' and instance.content_type.model == 'formsubmission':
            data['file'] = None
            data['file_url'] = None
        return data

    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment

        fields = (
            "id",

            "company",
            "uploaded_by",

            "content_type",
            "object_id",

            "attachment_type",

            "file",
            "file_url",

            "original_filename",
            "mime_type",
            "file_size",

            "description",

            "created_at",
        )

        read_only_fields = (
            "company",
            "uploaded_by",

            "original_filename",
            "mime_type",
            "file_size",

            "created_at",
        )

    def get_file_url(
        self,
        obj,
    ) -> str | None:
        request = self.context.get(
            "request"
        )

        if not obj.file:
            return None

        url = obj.file.url

        if request:
            return (
                request.build_absolute_uri(
                    url
                )
            )

        return url

    def validate(self, attrs):

        request = self.context[
            "request"
        ]

        content_type = attrs[
            "content_type"
        ]

        object_id = attrs[
            "object_id"
        ]

        file = attrs[
            "file"
        ]

        mime_type = (
            validate_uploaded_file(
                file,
                max_size=
                    MAX_ATTACHMENT_SIZE,
            )
        )

        target, company = (
            validate_attachment_target(
                content_type=
                    content_type,
                object_id=
                    object_id,
                user=
                    request.user,
            )
        )

        if not SubscriptionService.can_upload(
            company,
            additional_bytes=file.size,
        ):
            raise serializers.ValidationError({
                "file": "Your subscription storage limit has been reached.",
            })

        attrs[
            "_target_company"
        ] = company

        attrs[
            "_mime_type"
        ] = mime_type

        return attrs

    def create(
        self,
        validated_data,
    ):

        company = (
            validated_data.pop(
                "_target_company"
            )
        )

        mime_type = (
            validated_data.pop(
                "_mime_type"
            )
        )

        request = self.context[
            "request"
        ]

        file = validated_data[
            "file"
        ]

        from .services import AttachmentService
        return AttachmentService.create(
            actor=request.user,
            parent=validated_data['content_type'].get_object_for_this_type(pk=validated_data['object_id']),
            file=file, original_filename=file.name, mime_type=mime_type, file_size=file.size,
            attachment_type=validated_data.get('attachment_type', 'FILE'),
            description=validated_data.get('description', ''),
        )


# ============================================================
# Categories
# ============================================================

class DocumentCategorySerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = DocumentCategory

        fields = (
            "id",
            "company",
            "name",
            "description",
            "default_visibility",
            "sensitive",
            "is_active",
            "created_at",
        )

        read_only_fields = (
            "company",
            "created_at",
        )


# ============================================================
# Versions
# ============================================================

class DocumentVersionSerializer(
    serializers.ModelSerializer
):

    file_url = (
        serializers.SerializerMethodField()
    )

    uploaded_by_name = (
        serializers.CharField(
            source=
                "uploaded_by.full_name",
            read_only=True,
        )
    )

    class Meta:
        model = DocumentVersion

        fields = (
            "id",
            "version_number",

            "file",
            "file_url",

            "original_filename",
            "mime_type",
            "file_size",

            "change_note",

            "uploaded_by",
            "uploaded_by_name",

            "created_at",
        )

        read_only_fields = fields

    def get_file_url(
        self,
        obj,
    ) -> str | None:
        request = self.context.get(
            "request"
        )

        if not obj.file:
            return None

        url = obj.file.url

        if request:
            return (
                request.build_absolute_uri(
                    url
                )
            )

        return url


# ============================================================
# Document
# ============================================================

class DocumentSerializer(
    serializers.ModelSerializer
):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    team_name = serializers.CharField(
        source="team.name",
        read_only=True,
    )

    owner_name = serializers.CharField(
        source="owner.full_name",
        read_only=True,
    )

    versions = (
        DocumentVersionSerializer(
            many=True,
            read_only=True,
        )
    )

    initial_file = (
        serializers.FileField(
            write_only=True,
            required=True,
        )
    )

    def validate(self, attrs):
        category = attrs.get("category")
        request = self.context["request"]
        if category and category.company_id != request.user.company_id:
            raise serializers.ValidationError({
                "category": "Category belongs to another company.",
            })
        if category and "visibility" not in attrs and not self.instance:
            attrs["visibility"] = category.default_visibility
        return attrs

    class Meta:
        model = Document

        fields = (
            "id",

            "company",

            "category",
            "category_name",

            "branch",
            "branch_name",

            "department",
            "department_name",

            "team",
            "team_name",

            "project",

            "title",
            "description",
            "document_number",

            "visibility",
            "status",

            "current_version",

            "owner",
            "owner_name",

            "created_by",

            "effective_date",
            "expiry_date",

            "is_active",

            "initial_file",

            "versions",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "company",
            "current_version",
            "created_by",
            "created_at",
            "updated_at",
        )

    def validate(
        self,
        attrs,
    ):

        request = self.context[
            "request"
        ]

        company = (
            request.user.company
        )

        branch = attrs.get(
            "branch"
        )

        department = attrs.get(
            "department"
        )

        team = attrs.get(
            "team"
        )

        project = attrs.get(
            "project"
        )

        initial_file = attrs.get(
            "initial_file"
        )

        if initial_file:
            validate_uploaded_file(
                initial_file,
                max_size=
                    MAX_DOCUMENT_SIZE,
            )

        if (
            branch
            and branch.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "branch":
                    "Branch belongs to another company."
            })

        if (
            department
            and department.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "department":
                    "Department belongs to another company."
            })

        if (
            team
            and team.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "team":
                    "Team belongs to another company."
            })

        if (
            project
            and project.company_id
            != company.id
        ):
            raise serializers.ValidationError({
                "project":
                    "Project belongs to another company."
            })

        if (
            department
            and branch
            and department.branch_id
            != branch.id
        ):
            raise serializers.ValidationError({
                "department":
                    "Department must belong "
                    "to the selected branch."
            })

        if (
            team
            and department
            and team.department_id
            != department.id
        ):
            raise serializers.ValidationError({
                "team":
                    "Team must belong to "
                    "the selected department."
            })

        return attrs

    def create(
        self,
        validated_data,
    ):

        initial_file = (
            validated_data.pop(
                "initial_file"
            )
        )

        request = self.context[
            "request"
        ]

        mime_type = (
            validate_uploaded_file(
                initial_file,
                max_size=
                    MAX_DOCUMENT_SIZE,
            )
        )

        document = (
            Document.objects.create(
                company=
                    request.user.company,

                created_by=
                    request.user,

                **validated_data,
            )
        )

        DocumentVersion.objects.create(
            document=document,

            version_number=1,

            file=initial_file,

            original_filename=
                initial_file.name,

            mime_type=mime_type,

            file_size=
                initial_file.size,

            change_note=
                "Initial version",

            uploaded_by=
                request.user,
        )

        return document