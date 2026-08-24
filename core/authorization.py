from core.roles import Roles


class Authorization:

    @staticmethod
    def is_superuser(user):
        return user.is_authenticated and user.role == Roles.SUPERUSER

    @staticmethod
    def is_admin(user):
        return user.is_authenticated and user.role == Roles.ADMIN

    @staticmethod
    def is_manager(user):
        return user.is_authenticated and user.role == Roles.MANAGER

    @staticmethod
    def is_employee(user):
        return user.is_authenticated and user.role == Roles.EMPLOYEE

    @staticmethod
    def can_manage_company(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

    @staticmethod
    def can_manage_branch(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_create_project(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_update_project(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_delete_project(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

    @staticmethod
    def can_create_task(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_update_task(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )

    @staticmethod
    def can_complete_task(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )

    @staticmethod
    def can_create_report(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )

    @staticmethod
    def can_create_comment(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
            Roles.EMPLOYEE,
        )

    @staticmethod
    def can_manage_users(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

    @staticmethod
    def can_invite_member(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_remove_member(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_change_owner(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

    @staticmethod
    def can_manage_subscription(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

    @staticmethod
    def can_view_analytics(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
            Roles.MANAGER,
        )

    @staticmethod
    def can_manage_company_settings(user):
        return user.is_authenticated and user.role in (
            Roles.SUPERUSER,
            Roles.ADMIN,
        )

# from core.roles import Roles


# class Authorization:

#     @staticmethod
#     def can_manage_company(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_manage_branch(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]

#     @staticmethod
#     def can_create_project(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]

#     @staticmethod
#     def can_delete_project(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_archive_project(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_invite_member(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]

#     @staticmethod
#     def can_remove_member(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]

#     @staticmethod
#     def can_change_owner(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_create_workspace(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_delete_workspace(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_create_task(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]

#     @staticmethod
#     def can_complete_task(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER, Roles.EMPLOYEE]

#     @staticmethod
#     def can_create_report(user):
#         return user.role != Roles.INDIVIDUAL

#     @staticmethod
#     def can_manage_users(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN]

#     @staticmethod
#     def can_view_ai(user):
#         return user.role in [Roles.SUPERUSER, Roles.ADMIN, Roles.MANAGER]
