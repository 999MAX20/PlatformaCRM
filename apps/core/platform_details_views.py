from django.db import DatabaseError
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.core.permissions import IsPlatformUser
from apps.core.platform_crm_views import audited_response
from apps.core.platform_details import correct_business_details, details_projection


@never_cache
@api_view(["GET", "PATCH"])
@permission_classes([IsPlatformUser])
def platform_business_details(request, business_id):
    if request.method == "GET":
        return audited_response(request, business_id, "business_details", details_projection)
    try:
        payload = correct_business_details(request, business_id, request.data)
    except DatabaseError:
        return Response({"detail": "Business details are temporarily unavailable.",
                         "code": "temporary_service_failure", "category": "temporary"},
                        status=503, headers={"Cache-Control": "no-store"})
    return Response(payload, headers={"Cache-Control": "no-store"})
