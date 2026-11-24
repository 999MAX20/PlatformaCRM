from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.domain_errors import InvalidTransition
from .models import MedicalOrder
from .order_reads import order_workspace_access


def order_assistance_context(*, actor, scope, expected_revision):
    patient_revision = scope.get("expected_patient_revision")
    order_id = scope.get("order_id")
    order_revision = scope.get("expected_order_revision")
    if type(patient_revision) is not int or patient_revision < 1:
        raise ValidationError({"expected_patient_revision": "Provide the current patient revision."})
    if (order_id is None) != (order_revision is None) or any(
        type(value) is not int or value < 1 for value in (order_id, order_revision) if value is not None
    ):
        raise ValidationError({"order": "Provide an order and its current revision."})
    access = order_workspace_access(actor=actor, **{key: scope.get(key) for key in (
        "business_id", "patient_id", "encounter_id", "appointment_id", "participation_id")})
    if not access["actions"]["update" if order_id is not None else "create"]:
        raise PermissionDenied()
    if access["encounter_revision"] != expected_revision or access["patient_revision"] != patient_revision:
        raise InvalidTransition("The patient or encounter changed; reload before requesting assistance.")
    if order_id is not None:
        order = MedicalOrder.objects.filter(pk=order_id, business_id=scope["business_id"],
            encounter_id=scope["encounter_id"], author=actor).first()
        if order is None:
            raise PermissionDenied()
        if order.revision != order_revision or order.state != "draft":
            raise InvalidTransition("The order changed; reload before requesting assistance.")
    return {"actor": actor.pk, "business": scope["business_id"], "patient": scope["patient_id"],
        "encounter": scope["encounter_id"], "revision": expected_revision, "field": "order_text",
        "patient_revision": patient_revision, "order": order_id, "order_revision": order_revision}
