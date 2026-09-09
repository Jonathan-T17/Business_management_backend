from rest_framework.versioning import URLPathVersioning
class SmartBizURLPathVersioning(URLPathVersioning):
    default_version='v1'; allowed_versions=('v1',); version_param='version'
