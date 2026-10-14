from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.businesses.models import Business
from apps.core.permissions import user_can_access_business
from apps.core.service_status import business_service_status


@api_view(["GET"])
def service_status(request):
    try:
        business_id = int(request.query_params.get("business", ""))
    except (TypeError, ValueError):
        raise ValidationError({"business": "A valid business ID is required."})
    business = Business.objects.filter(pk=business_id).first()
    if business is None or not user_can_access_business(request.user, business):
        raise PermissionDenied("Business is not available.")
    return Response(business_service_status(business))
