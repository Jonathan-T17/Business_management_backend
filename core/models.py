from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "is_active", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "is_active", "deleted_at"])


class CompanyModel(TimeStampedModel, SoftDeleteModel):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
    )

    class Meta:
        abstract = True


class CompanyBranchModel(CompanyModel):
    branch = models.ForeignKey(
        "companies.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True



# from django.db import models


# class TimeStampedModel(models.Model):

#     created_at = models.DateTimeField(
#         auto_now_add=True
#     )

#     updated_at = models.DateTimeField(
#         auto_now=True
#     )

#     class Meta:
#         abstract = True


# class SoftDeleteModel(models.Model):

#     is_active = models.BooleanField(
#         default=True
#     )

#     class Meta:
#         abstract = True


# class CompanyModel(TimeStampedModel, SoftDeleteModel):

#     company = models.ForeignKey(
#         "companies.Company",
#         on_delete=models.CASCADE,
#     )

#     class Meta:
#         abstract = True


# class CompanyBranchModel(CompanyModel):

#     branch = models.ForeignKey(
#         "companies.Branch",
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#     )

#     class Meta:
#         abstract = True