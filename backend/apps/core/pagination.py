from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

class BoundedPagination(LimitOffsetPagination):
    default_limit = 25
    max_limit = 100
    def paginate_queryset(self, queryset, request, view=None):
        for key in ('limit', 'offset'):
            if key in request.query_params:
                try:
                    value = int(request.query_params[key])
                except (TypeError, ValueError):
                    raise ValidationError({key: 'Enter a valid whole number.'})
                if value < (1 if key == 'limit' else 0):
                    raise ValidationError({key: 'Enter a valid positive page range.'})
        return super().paginate_queryset(queryset, request, view)
    def get_paginated_response(self, data):
        return Response({'results': data, 'count': self.count})
