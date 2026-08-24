class CompanyQuerysetMixin:
    
    company_field = "company"

    def get_queryset(self):

        qs = super().get_queryset()

        user = self.request.user

        if user.role == "SUPERUSER":
            return qs.filter(
                **{
                    self.company_field: user.company
                }
            )

        if user.role == "ADMIN":
            return qs.filter(
                **{
                    self.company_field: user.company
                }
            )

        if user.role == "MANAGER":
            return qs.filter(
                **{
                    self.company_field: user.company
                }
            )

        if user.role == "EMPLOYEE":
            return qs.filter(
                **{
                    self.company_field: user.company
                }
            )

        return qs.none()

class BranchRestrictedMixin:
    
    def get_queryset(self):

        qs = super().get_queryset()

        user = self.request.user

        if user.role == "MANAGER":
            return qs.filter(
                branch=user.branch,
                company=user.company
            )

        return qs.filter(company=user.company)



# from rest_framework.exceptions import PermissionDenied

# class CompanyObjectPermission:
#     def check_company(self, obj):
#         user = self.request.user
#         if obj.company != user.company:
#             raise PermissionDenied("Access denied.")

#     def check_branch(self, obj):
#         user = self.request.user
#         if hasattr(obj, "branch") and user.role == "MANAGER":
#             if obj.branch != user.branch:
#                 raise PermissionDenied("Branch access denied.")
