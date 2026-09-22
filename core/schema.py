from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.openapi import AutoSchema


class ActiveCompanyJWTScheme(SimpleJWTScheme):
    target_class = "security.authentication.ActiveCompanyJWTAuthentication"


class SmartBizAutoSchema(AutoSchema):
    def get_operation(self, path, path_regex, path_prefix, method, registry):
        # Maintenance PUT requires a record id; the shared APIView also appears on the collection URL.
        if path.endswith("/administration/{key}/") and method.upper() == "PUT":
            return None
        return super().get_operation(path, path_regex, path_prefix, method, registry)

    def get_operation_id(self):
        name = super().get_operation_id()
        if "/administration/{key}/" in self.path and "/choices/" not in self.path:
            return name + ("_record" if self.path.endswith("/{id}/") else "_collection")
        if "/form-submissions/" in self.path and "/attachments/" in self.path:
            return name + ("_file" if "{attachment_id}" in self.path else "_collection")
        return name
