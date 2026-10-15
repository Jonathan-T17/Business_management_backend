from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.sequence import company_local_date
from workflows.services import WorkflowService

from .models import (
    FormTemplate,
    FormSubmission,
)


class FormSubmissionService:

    # ========================================================
    # Schema Snapshot
    # ========================================================

    @staticmethod
    def build_schema_snapshot(template):

        fields = []

        for field in (
            template.fields
            .filter(is_active=True)
            .order_by("order", "id")
        ):

            fields.append({
                "help_text": field.help_text,
                "placeholder": field.placeholder,
                "classification": field.classification,
                "key":
                    field.key,

                "label":
                    field.label,

                "field_type":
                    field.field_type,

                "required":
                    field.required,

                "options":
                    field.options,

                "validation_rules":
                    field.validation_rules,

                "order":
                    field.order,
            })

        return {
            "source_starter": template.source_starter,
            "template_id":
                str(template.id),

            "template_name":
                template.name,

            "template_code":
                template.code,

            "template_version":
                template.version,

            "category":
                template.category,

            "fields":
                fields,
        }

    # ========================================================
    # Validate Submission Data
    # ========================================================

    @classmethod
    def validate_data(
        cls,
        *,
        template,
        data,
        partial=False,
        schema=None,
    ):

        if not isinstance(
            data,
            dict,
        ):
            raise ValidationError(
                "Submission data must be an object."
            )

        errors = {}

        fields = (
            template.fields
            .filter(
                is_active=True
            )
            .order_by(
                "order",
                "id",
            )
        )

        if schema is not None:
            from types import SimpleNamespace
            definitions=schema.get('fields',[]) if isinstance(schema,dict) else schema
            fields=[SimpleNamespace(**dict({'required':False,'options':[],'validation_rules':{},'label':f.get('key','')},**f)) for f in definitions]

        allowed_keys = {
            field.key
            for field in fields
        }

        unknown_keys = (
            set(data.keys())
            - allowed_keys
        )

        if unknown_keys:
            errors["data"] = (
                "Unknown form fields: "
                + ", ".join(
                    sorted(
                        unknown_keys
                    )
                )
            )

        for field in fields:

            condition=field.validation_rules.get('show_when')
            if condition and str(data.get(condition['field'],'')).lower()!=str(condition['equals']).lower():
                data.pop(field.key,None)
                continue
            value = data.get(
                field.key
            )

            if (
                not partial
                and field.required
                and cls._is_empty(value)
            ):
                errors[field.key] = (
                    "This field is required."
                )

                continue

            if cls._is_empty(value):
                continue

            try:
                cls._validate_field(
                    field=field,
                    value=value,
                )

            except ValidationError as exc:

                message = (
                    exc.messages[0]
                    if hasattr(
                        exc,
                        "messages",
                    )
                    else str(exc)
                )

                errors[
                    field.key
                ] = message

        if errors:
            raise ValidationError(
                errors
            )

        return data

    # ========================================================
    # Field Validation
    # ========================================================

    @classmethod
    def _validate_field(
        cls,
        *,
        field,
        value,
    ):

        field_type = (
            field.field_type
        )
        if field_type == 'ITEM_LIST':
            from .materials import item_list
            try:
                item_list(value)
            except Exception as exc:
                from rest_framework.exceptions import ValidationError as APIValidationError
                if isinstance(exc, APIValidationError):
                    raise ValidationError(str(exc.detail))
                raise
            return

        rules = (
            field.validation_rules
            or {}
        )
        from .validation import validate_rules, finite_number
        validate_rules(rules)

        # ------------------------------------
        # TEXT
        # ------------------------------------

        if field_type in (
            "TEXT",
            "LONG_TEXT",
            "EMAIL",
            "PHONE",
        ):

            if not isinstance(
                value,
                str,
            ):
                raise ValidationError(
                    "Must be text."
                )

            min_length = rules.get(
                "min_length"
            )

            max_length = rules.get(
                "max_length"
            )
            if field_type == 'EMAIL':
                from django.core.validators import validate_email
                validate_email(value)

            if (
                min_length is not None
                and len(value)
                < int(min_length)
            ):
                raise ValidationError(
                    f"Minimum length is "
                    f"{min_length}."
                )

            if (
                max_length is not None
                and len(value)
                > int(max_length)
            ):
                raise ValidationError(
                    f"Maximum length is "
                    f"{max_length}."
                )

            return

        # ------------------------------------
        # INTEGER
        # ------------------------------------

        if field_type == "INTEGER":

            if isinstance(
                value,
                bool,
            ):
                raise ValidationError(
                    "Must be an integer."
                )

            try:
                decimal = finite_number(value)
                if decimal != decimal.to_integral_value():
                    raise ValidationError('Must be a whole number.')
                number = decimal
            except (
                TypeError,
                ValueError,
            ):
                raise ValidationError(
                    "Must be an integer."
                )

            cls._validate_number_rules(
                number,
                rules,
            )

            return

        # ------------------------------------
        # DECIMAL
        # ------------------------------------

        if field_type == "DECIMAL":

            try:
                number = finite_number(value)

            except (
                InvalidOperation,
                TypeError,
            ):
                raise ValidationError(
                    "Must be a number."
                )

            cls._validate_number_rules(
                number,
                rules,
            )

            return

        # ------------------------------------
        # BOOLEAN
        # ------------------------------------

        if field_type == "BOOLEAN":

            if not isinstance(
                value,
                bool,
            ):
                raise ValidationError(
                    "Must be true or false."
                )

            return

        # ------------------------------------
        # SELECT
        # ------------------------------------

        if field_type == "SELECT":

            allowed = {
                option.get("value")
                for option in field.options
            }

            if value not in allowed:
                raise ValidationError(
                    "Invalid option."
                )

            return

        # ------------------------------------
        # MULTISELECT
        # ------------------------------------

        if field_type == "MULTISELECT":

            if not isinstance(
                value,
                list,
            ):
                raise ValidationError(
                    "Must be a list."
                )

            allowed = {
                option.get("value")
                for option in field.options
            }

            invalid = [
                item
                for item in value
                if item not in allowed
            ]

            if invalid:
                raise ValidationError(
                    "One or more selected "
                    "options are invalid."
                )

            return

        # ------------------------------------
        # LOCATION
        # ------------------------------------

        if field_type == "LOCATION":

            if not isinstance(
                value,
                dict,
            ):
                raise ValidationError(
                    "Location must be an object."
                )

            if (
                "latitude" not in value
                or "longitude" not in value
            ):
                raise ValidationError(
                    "Latitude and longitude "
                    "are required."
                )

            try:
                latitude = float(
                    value["latitude"]
                )

                longitude = float(
                    value["longitude"]
                )

            except (
                TypeError,
                ValueError,
            ):
                raise ValidationError(
                    "Invalid location coordinates."
                )

            if not (
                -90
                <= latitude
                <= 90
            ):
                raise ValidationError(
                    "Invalid latitude."
                )

            if not (
                -180
                <= longitude
                <= 180
            ):
                raise ValidationError(
                    "Invalid longitude."
                )

            return

        # Date/time values initially travel as ISO strings.
        if field_type in (
            "DATE",
            "TIME",
            "DATETIME",
        ):

            if not isinstance(
                value,
                str,
            ):
                raise ValidationError(
                    "Must be an ISO date/time string."
                )
            from datetime import date, datetime, time
            import re
            patterns = {
                'DATE': r'\d{4}-\d{2}-\d{2}',
                'TIME': r'\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?',
                'DATETIME': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?',
            }
            try:
                if not re.fullmatch(patterns[field_type], value):
                    raise ValueError()
                {'DATE': date, 'TIME': time, 'DATETIME': datetime}[field_type].fromisoformat(value)
            except ValueError:
                raise ValidationError(f'Enter a valid {field_type.lower().replace("datetime", "date and time")}.')

            return

    # ========================================================
    # Number Rules
    # ========================================================

    @staticmethod
    def _validate_number_rules(
        number,
        rules,
    ):

        minimum = rules.get(
            "min"
        )

        maximum = rules.get(
            "max"
        )

        if (
            minimum is not None
            and number
            < Decimal(str(minimum))
        ):
            raise ValidationError(
                f"Minimum value is "
                f"{minimum}."
            )

        if (
            maximum is not None
            and number
            > Decimal(str(maximum))
        ):
            raise ValidationError(
                f"Maximum value is "
                f"{maximum}."
            )

    # ========================================================
    # Create Draft
    # ========================================================

    @classmethod
    @transaction.atomic
    def create_submission(
        cls,
        *,
        template,
        user,
        data=None,
        title="",
        reporting_date=None,
        branch=None,
        department=None,
        team=None,
        project=None,
        task=None,
        client_request_id=None,
    ):

        from .access import FormAccess
        company = user.company
        if template.company_id != company.pk or not FormAccess.can_submit(user):
            raise ValidationError('This form is not available in your company.')
        if client_request_id:
            # Serialize retries within the tenant before allocating a reference.
            type(company).objects.select_for_update().get(pk=company.pk)
            existing = FormSubmission.objects.filter(company=company, submitted_by=user, client_request_id=client_request_id).first()
            if existing:
                if existing.template_id != template.pk:
                    raise ValidationError({'client_request_id': 'This entry reference is already used for a different form.'})
                return existing
        if not FormAccess.eligible(user,template):
            raise ValidationError('This published form is not available to you.')
        if not template.is_active:
            raise ValidationError('Form template is inactive.')

        if (
            template.company_id
            != company.id
        ):
            raise ValidationError(
                "Form belongs to another company."
            )

        # A branch-specific form keeps its branch when filled through another position.
        requested_branch = branch
        if requested_branch is not None and not FormAccess.filing_branches(user, template).filter(pk=requested_branch.pk).exists():
            raise ValidationError('Choose a submission location within your assigned access and this form’s audience.')
        branch = branch or template.branch or getattr(user,"branch",None)
        department = department or template.department
        team = team or template.team
        from core.capability_service import CapabilityService
        from core.position_scope import PositionScope
        if not (CapabilityService.has_company(user,"SUBMIT_FORMS") or CapabilityService.has_company(user,"USE_FORMS")):
            allowed=PositionScope.branches_for(user,"SUBMIT_FORMS") | PositionScope.branches_for(user,"USE_FORMS")
            primary = PositionScope.primary_position(user)
            if requested_branch is None and template.branch_id is None and primary and primary.primary_scope == "BRANCH":
                if PositionScope.primary_capabilities(user) & {"SUBMIT_FORMS", "USE_FORMS"}:
                    branch = primary.branch
            if FormAccess.default_member_access(user):
                  allowed.add(getattr(FormAccess.starting_branch(user), 'pk', None))
            if getattr(branch,"pk",None) not in allowed:
                raise ValidationError("Choose a submission location within your assigned access.")

        cls._validate_scope(
            company=company,
            template=template,
            branch=branch,
            department=department,
            team=team,
            project=project,
            task=task,
        )

        from .defaults import apply_defaults
        data = apply_defaults(cls.build_schema_snapshot(template), user, data, branch=branch)

        cls.validate_data(
            template=template,
            data=data,
            partial=True,
        )

        submission = (
            FormSubmission.objects.create(
                company=company,
                template=template,
                submitted_by=user,
                client_request_id=client_request_id,

                branch=(
                    branch
                    or getattr(
                        user,
                        "branch",
                        None,
                    )
                ),

                department=
                    department,

                team=team,

                project=project,
                task=task,

                title=title,

                reporting_date=(
                    reporting_date
                    or company_local_date(company)
                ),

                data=data,

                template_version=
                    template.version,

                schema_snapshot=
                    cls.build_schema_snapshot(
                        template
                    ),

                reference_number=
                    cls.generate_reference_number(
                        company=company,
                        template=template,
                    ),
            )
        )

        return submission

    # ========================================================
    # Submit
    # ========================================================

    @classmethod
    @transaction.atomic
    def submit(
        cls,
        *,
        submission,
        user,
        workflow=None,
    ):

        from .access import FormAccess
        submission=FormSubmission.objects.select_for_update(of=('self',)).select_related('template__workflow').get(pk=submission.pk)
        if not FormAccess.can_submit(user) or user.company_id != submission.company_id:
            raise ValidationError('Form submission permission is required.')
        if hasattr(submission,'business_request'):
            raise ValidationError('Submit this form through its business request.')
        if (
            submission.submitted_by_id
            != user.id
        ):
            raise ValidationError(
                "Only the author can submit this form."
            )

        if submission.status not in (
            "DRAFT",
            "RETURNED",
        ):
            raise ValidationError(
                "This submission cannot be submitted "
                "in its current status."
            )

        cls.validate_data(
            template=
                submission.template,
            data=
                submission.data,
            partial=False,
            schema=submission.schema_snapshot,
        )

        if workflow and workflow.pk != submission.template.workflow_id:
            raise ValidationError('The published template determines the workflow.')
        workflow=submission.template.workflow
        if submission.template.source_starter in {'material-dispatch','material-receipt','material-return'}:
            raise ValidationError('Record this action from its approved material request so quantities stay connected.')
        if submission.template.source_starter == 'material-request' and not workflow:
            raise ValidationError('Material requests require an assigned review route.')
        if not workflow:
            submission.status='SUBMITTED';submission.submitted_at=timezone.now()
            submission.save(update_fields=['status','submitted_at','updated_at'])
            if hasattr(submission,'reporting_obligation'):
                from reporting_schedules.services import ReportingObligationStateService
                ReportingObligationStateService.mark_submitted(obligation=submission.reporting_obligation,submitted_at=submission.submitted_at)
            return submission,None
        if workflow.company_id!=submission.company_id or workflow.target_type!='FORM_SUBMISSION' or not workflow.is_active:
            raise ValidationError('No active form approval workflow is available.')

        from workflows.runtime_service import WorkflowRuntimeService
        instance = WorkflowRuntimeService.start(
            workflow=workflow,
            target=submission,
            submitted_by=user,
        )

        submission.refresh_from_db()

        obligation = getattr(
            submission,
            "reporting_obligation",
            None,
        )

        if obligation:
            from reporting_schedules.services import (
                ReportingObligationStateService,
            )

            ReportingObligationStateService.mark_submitted(
                obligation=obligation,
                submitted_at=
                    timezone.now(),
            )

        return (
            submission,
            instance,
        )

    # ========================================================
    # Reference Number
    # ========================================================

    @staticmethod
    def generate_reference_number(
        *,
        company,
        template,
    ):

        today = (
            timezone.localdate()
        )

        prefix = (
            template.code.upper()
        )

        count = (
            FormSubmission.objects.filter(
                company=company,
                template=template,
                created_at__date=today,
            ).count()
            + 1
        )

        return (
            f"{prefix}-"
            f"{today:%Y%m%d}-"
            f"{count:05d}"
        )

    # ========================================================
    # Tenant / Scope Validation
    # ========================================================

    @staticmethod
    def _validate_scope(
        *,
        company,
        template,
        branch,
        department,
        team,
        project,
        task,
    ):

        if (
            branch
            and branch.company_id
            != company.id
        ):
            raise ValidationError(
                "Branch belongs to another company."
            )

        if (
            department
            and department.company_id
            != company.id
        ):
            raise ValidationError(
                "Department belongs to another company."
            )

        if (
            team
            and team.company_id
            != company.id
        ):
            raise ValidationError(
                "Team belongs to another company."
            )

        if (
            project
            and project.company_id
            != company.id
        ):
            raise ValidationError(
                "Project belongs to another company."
            )

        if (
            task
            and task.company_id
            != company.id
        ):
            raise ValidationError(
                "Task belongs to another company."
            )

        if (
            department
            and branch
            and department.branch_id
            != branch.id
        ):
            raise ValidationError(
                "Department does not belong "
                "to the selected branch."
            )

        if (
            team
            and department
            and team.department_id
            != department.id
        ):
            raise ValidationError(
                "Team does not belong "
                "to the selected department."
            )

        if (
            task
            and project
            and task.project_id
            != project.id
        ):
            raise ValidationError(
                "Task does not belong "
                "to the selected project."
            )

        if (
            template.branch_id
            and branch
            and template.branch_id
            != branch.id
        ):
            raise ValidationError(
                "This form is restricted "
                "to another branch."
            )

    @staticmethod
    def _is_empty(value):

        return (
            value is None
            or (isinstance(value, str) and not value.strip())
            or value == []
        )
