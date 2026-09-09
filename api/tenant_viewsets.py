from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .pagination import StandardPageNumberPagination
class TenantScopedMixin:
    pagination_class=StandardPageNumberPagination
    def visible_queryset(self,user,queryset): raise NotImplementedError
    def get_queryset(self): return self.visible_queryset(self.request.user,super().get_queryset())
class TenantModelViewSet(TenantScopedMixin,ModelViewSet): pass
class TenantReadOnlyModelViewSet(TenantScopedMixin,ReadOnlyModelViewSet): pass
