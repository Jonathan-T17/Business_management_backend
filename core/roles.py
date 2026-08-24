from enum import Enum


class Roles(str, Enum):
    SUPERUSER = "SUPERUSER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    INDIVIDUAL = "INDIVIDUAL"

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


ROLE_LEVEL = {
    Roles.SUPERUSER: 100,
    Roles.ADMIN: 80,
    Roles.MANAGER: 60,
    Roles.EMPLOYEE: 40,
    Roles.INDIVIDUAL: 20,
}