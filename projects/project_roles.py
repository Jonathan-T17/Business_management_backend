from enum import Enum


class ProjectRoles(str, Enum):

    OWNER = "OWNER"
    MANAGER = "MANAGER"
    CONTRIBUTOR = "CONTRIBUTOR"
    VIEWER = "VIEWER"

    @classmethod
    def choices(cls):
        return [
            (role.value, role.name.title())
            for role in cls
        ]

    @classmethod
    def values(cls):
        return [
            role.value
            for role in cls
        ]

    @classmethod
    def can_manage_project(cls, role):
        return role in (
            cls.OWNER.value,
            cls.MANAGER.value,
        )

    @classmethod
    def can_manage_members(cls, role):
        return role in (
            cls.OWNER.value,
            cls.MANAGER.value,
        )

    @classmethod
    def can_modify_project(cls, role):
        return role in (
            cls.OWNER.value,
            cls.MANAGER.value,
        )

    @classmethod
    def can_delete_project(cls, role):
        return role == cls.OWNER.value