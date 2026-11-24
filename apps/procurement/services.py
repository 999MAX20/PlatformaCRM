from decimal import Decimal, InvalidOperation
from datetime import date
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .dental_access import doctor_context
from .models import PurchaseRequest, PurchaseRequestLine, PurchaseRequestHistory


UNITS = ("piece", "package", "ml", "l", "g", "kg", "m")


@transaction.atomic
def request_context(*, actor, business_id):
    from apps.branches.models import Branch
    from apps.medical.role_access import assert_medical_role_permission
    from apps.businesses.models import Business
    business = Business.objects.filter(pk=business_id).first()
    role = assert_medical_role_permission(actor, business, "medical_records", "create")
    if role.kind not in ("doctor", "head"):
        raise PermissionDenied()
    rows = []
    for branch in Branch.objects.filter(business=business, is_active=True, archived_at__isnull=True).order_by("name", "pk"):
        try:
            doctor_context(actor, business_id, branch.pk)
        except PermissionDenied:
            continue
        rows.append({"id": branch.pk, "name": branch.name})
    return {"branches": rows}


def validate_fields(fields):
    if set(fields) != {"material", "specification", "quantity", "unit", "urgent", "needed_by", "comment"}:
        raise ValidationError({"request": "Provide only the material request fields."})
    data = dict(fields)
    for name, limit in (("material", 200), ("specification", 200), ("comment", 1000)):
        if not isinstance(data[name], str) or len(data[name].strip()) > limit:
            raise ValidationError({name: "Invalid text length."})
        data[name] = data[name].strip()
    if not data["material"] or data["unit"] not in UNITS or type(data["urgent"]) is not bool:
        raise ValidationError({"request": "Select material, unit and urgency."})
    try:
        quantity = Decimal(str(data["quantity"]))
        if not quantity.is_finite() or not 0 < quantity < Decimal("1000000000") or quantity != quantity.quantize(Decimal("0.001")):
            raise ValueError()
        if data["unit"] in ("piece", "package") and quantity != quantity.to_integral_value():
            raise ValueError()
    except (InvalidOperation, ValueError):
        raise ValidationError({"quantity": "Use a positive quantity, up to three decimals; pieces and packages are whole numbers."})
    data["quantity"] = quantity
    if (data["needed_by"] is not None and type(data["needed_by"]) is not date) or (data["urgent"] and data["needed_by"] is None):
        raise ValidationError({"needed_by": "Urgent requests require a date."})
    return data


def projection(item):
    line = item.line
    return {"id": item.pk, "branch_id": item.branch_id, "author_name": item.author.full_name or item.author.get_full_name(),
        "created_at": item.created_at.isoformat(), "state": item.state, "revision": item.revision,
        "urgent": item.urgent, "needed_by": item.needed_by.isoformat() if item.needed_by else None,
        "comment": item.comment, "material": line.material, "specification": line.specification,
        "quantity": str(line.quantity), "unit": line.unit, "received": str(line.received)}


def record_history(item, actor, action, reason=""):
    PurchaseRequestHistory.objects.create(request=item, actor=actor, revision=item.revision,
        action=action, reason=reason, snapshot=projection(item))
    write_actor_audit_log(actor=actor, business=item.business, action=AuditLog.Actions.CREATE if action == "created" else AuditLog.Actions.UPDATE,
        instance=item, metadata={"kind": "purchase_request_" + action, "revision": item.revision})


def validate_key(key):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValidationError({"idempotency_key": "Provide a key of at most 128 characters."})


def apply_fields(item, fields):
    for name in ("urgent", "needed_by", "comment"):
        setattr(item, name, fields[name])
    line = item.line
    for name in ("material", "specification", "quantity", "unit"):
        setattr(line, name, fields[name])
    line.full_clean()
    line.save()


@transaction.atomic
def create_request(*, actor, business_id, branch_id, fields, idempotency_key):
    actor, business, branch = doctor_context(actor, business_id, branch_id)
    validate_key(idempotency_key)
    fields = validate_fields(fields)
    def operation():
        item = PurchaseRequest.objects.create(business=business, branch=branch, author=actor,
            urgent=fields["urgent"], needed_by=fields["needed_by"], comment=fields["comment"])
        PurchaseRequestLine.objects.create(request=item, **{key: fields[key] for key in ("material", "specification", "quantity", "unit")})
        record_history(item, actor, "created")
        return CRMCommandResult(data={"id": item.pk}, resource=item)
    result = run_idempotent_crm_command(business=business, actor=actor, action="procurement.create",
        idempotency_key=idempotency_key, payload={"branch": branch.pk, "fields": fields}, operation=operation)
    return PurchaseRequest.objects.select_related("author", "line").get(pk=result.resource_id if result.replayed else result.resource.pk, business=business), result.replayed


@transaction.atomic
def change_own_request(*, actor, business_id, branch_id, request_id, expected_revision, action, reason, fields, idempotency_key):
    actor, business, branch = doctor_context(actor, business_id, branch_id)
    validate_key(idempotency_key)
    item = PurchaseRequest.objects.select_related("author", "line").filter(pk=request_id, business=business, branch=branch, author=actor).first()
    if item is None:
        raise PermissionDenied()
    if action not in ("edit", "cancel") or not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000:
        raise ValidationError({"reason": "Select an action and provide its reason."})
    fields = validate_fields(fields) if action == "edit" else fields
    if action == "cancel" and fields:
        raise ValidationError({"fields": "Cancellation cannot change material fields."})
    def operation():
        if type(expected_revision) is not int or item.revision != expected_revision or item.state != "new":
            raise InvalidTransition("The request was changed or accepted; reload its current state.")
        if action == "edit":
            apply_fields(item, fields)
        else:
            item.state = "cancelled"
        item.revision += 1
        item.updated_at = timezone.now()
        item.full_clean(); item.save()
        record_history(item, actor, action, reason.strip())
        return CRMCommandResult(data={"id": item.pk}, resource=item)
    result = run_idempotent_crm_command(business=business, actor=actor, action="procurement.own_change",
        idempotency_key=idempotency_key, payload={"request": request_id, "revision": expected_revision, "action": action, "reason": reason, "fields": fields}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed


@transaction.atomic
def list_own_requests(*, actor, business_id, branch_id, after_id=0):
    actor, business, branch = doctor_context(actor, business_id, branch_id)
    if type(after_id) is not int or after_id < 0:
        raise ValidationError({"after_id": "Invalid cursor."})
    rows = list(PurchaseRequest.objects.select_related("author", "line").filter(business=business, branch=branch, author=actor, pk__gt=after_id).order_by("pk")[:26])
    return {"results": [projection(item) for item in rows[:25]], "next_id": rows[24].pk if len(rows)>25 else None}


@transaction.atomic
def own_history(*, actor, business_id, branch_id, request_id, after_id=0):
    actor, business, branch = doctor_context(actor, business_id, branch_id)
    item = PurchaseRequest.objects.filter(pk=request_id, business=business, branch=branch, author=actor).first()
    if item is None:
        raise PermissionDenied()
    rows = list(item.history.select_related("actor").filter(pk__gt=after_id).order_by("pk")[:26])
    return {"results": [{"id": row.pk, "actor_name": row.actor.full_name or row.actor.get_full_name(), "created_at": row.created_at,
        "action": row.action, "reason": row.reason, "snapshot": row.snapshot} for row in rows[:25]],
        "next_id": rows[24].pk if len(rows)>25 else None}
