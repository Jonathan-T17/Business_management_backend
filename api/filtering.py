from rest_framework.exceptions import ValidationError
class SafeOrderingMixin:
    ordering_fields=(); default_ordering=None
    def get_ordering(self):
        raw=self.request.query_params.get('ordering')
        if not raw: return self.default_ordering
        requested=[p.strip() for p in raw.split(',') if p.strip()]
        invalid=[f for f in requested if f.lstrip('-') not in set(self.ordering_fields)]
        if invalid: raise ValidationError({'ordering':'Unsupported ordering field.'})
        return requested
class SafeSearchMixin:
    search_fields=(); max_search_length=100
    def validated_search_term(self):
        term=(self.request.query_params.get('search') or '').strip()
        if len(term)>self.max_search_length: raise ValidationError({'search':'Search term is too long.'})
        return term
