from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class ActiveCompanyJWTScheme(SimpleJWTScheme):
    target_class = "security.authentication.ActiveCompanyJWTAuthentication"
