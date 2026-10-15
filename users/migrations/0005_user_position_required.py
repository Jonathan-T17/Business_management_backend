from django.db import migrations, models


def backfill(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model("users", "User")
    Invite = apps.get_model("companies", "CompanyInvite")
    Profile = apps.get_model("organizations", "EmployeeProfile")
    for invite in Invite.objects.using(alias).filter(status="ACCEPTED", position__isnull=True).iterator():
        users = User.objects.using(alias).filter(company_id=invite.company_id,
            email__iexact=invite.email, role__in=["EMPLOYEE", "MANAGER"])
        users.update(position_required=True)
        for user in users:
            Profile.objects.using(alias).get_or_create(user_id=user.pk, defaults={
                "company_id": invite.company_id, "employee_id": f"INV-{invite.pk}"})


class Migration(migrations.Migration):
    dependencies = [("users", "0004_user_theme_preference"),
                    ("companies", "0009_companyinvite_position"),
                    ("organizations", "0012_employeepositionassignment")]
    operations = [migrations.AddField(model_name="user", name="position_required",
        field=models.BooleanField(default=False, editable=False)),
        migrations.RunPython(backfill, migrations.RunPython.noop)]
