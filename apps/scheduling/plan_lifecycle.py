"""Called under the scheduling Business lock before locking an Appointment."""
from apps.scheduling.models import VisitPlan


def lock_appointment_plan(appointment):
    return VisitPlan.objects.select_for_update().filter(
        business_id=appointment.business_id, steps__appointment_id=appointment.pk).first()


def touch_appointment_plan(plan):
    if plan is not None:
        plan.revision += 1
        plan.save(update_fields=["revision", "updated_at"])
