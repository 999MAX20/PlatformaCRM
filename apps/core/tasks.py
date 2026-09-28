from celery import shared_task

from apps.core.export_jobs import process_due_export_jobs, process_export_job
from apps.core.idempotency import prune_expired_crm_commands
from apps.core.file_scanning import scan_due_attachments


@shared_task(name="files.scan_due_attachments", queue="file_scans")
def scan_due_attachments_task(limit=10):
    return {"processed": scan_due_attachments(limit=limit)}


@shared_task(bind=True, name="exports.process_job", queue="reports_exports")
def process_export_job_task(self, job_id):
    job = process_export_job(job_id)
    return {"job_id": job_id, "status": job.status if job else "missing"}


@shared_task(bind=True, name="exports.process_due_jobs", queue="reports_exports")
def process_due_export_jobs_task(self, limit=50):
    jobs = process_due_export_jobs(limit=limit)
    return {"processed": len(jobs), "job_ids": [job.id for job in jobs if job is not None]}


@shared_task(bind=True, name="crm.prune_command_idempotency", queue="default")
def prune_expired_crm_commands_task(self, limit=1000):
    return {"deleted": prune_expired_crm_commands(limit=limit)}
