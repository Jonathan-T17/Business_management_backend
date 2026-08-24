"""
Deprecated compatibility module.

Application-wide user roles are defined in core.roles.Roles.

Do not define additional user-role systems in the companies app.
"""

from core.roles import Roles

UserRoles = Roles