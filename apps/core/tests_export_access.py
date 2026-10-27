from unittest.mock import patch
from datetime import date

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.export_jobs import process_export_job, request_report_export
from apps.core.models import ExportJob, AuditLog
from apps.leads.models import Lead


@override_settings(EXPORT_SYNC_MAX_ROWS=0, REPORT_EXPORT_SYNC_MAX_DAYS=0, CELERY_TASK_ALWAYS_EAGER=False)
class ExportAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="export-owner", email="export-owner@example.test")
        self.actor = User.objects.create_user(username="export-member", email="export-member@example.test")
        self.other = User.objects.create_user(username="export-other", email="export-other@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Export", slug="export-access")
        self.role = BusinessRole.objects.create(business=self.business, name="Export role")
        self.permission = RolePermission.objects.create(business_role=self.role, resource="leads", action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="analytics", action="view", scope="business")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer = BusinessMember.objects.create(business=self.business, user=self.other, role="operator")
        customer = Client.objects.create(business=self.business, full_name="Export customer")
        self.mine = Lead.objects.create(business=self.business, client=customer, responsible_user=self.actor, message="own-visible")
        self.theirs = Lead.objects.create(business=self.business, client=customer, responsible_user=self.other, message="peer-private")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def export(self):
        response = self.api.get("/api/export/leads/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 202, response.data)
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        return job

    def download(self, job, status=200):
        response = self.api.get(f"/api/export-jobs/{job.pk}/download/")
        self.assertEqual(response.status_code, status)
        if status == 200:
            content = b"".join(response.streaming_content)
            response.close()
            return content
        self.assertFalse(response.streaming)
        return response

    def test_unchanged_access_and_denied_download_has_no_success_audit(self):
        job = self.export()
        self.assertIn(b"peer-private", self.download(job))
        count = AuditLog.objects.filter(metadata__kind="file_download").count()
        self.permission.scope = "own"
        self.permission.save()
        self.download(job, 403)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="file_download").count(), count)
        fresh = self.export()
        content = self.download(fresh)
        self.assertIn(b"own-visible", content)
        self.assertNotIn(b"peer-private", content)

    def test_business_to_team_and_team_member_revocation(self):
        team = Team.objects.create(business=self.business, name="Export team")
        TeamMember.objects.create(team=team, member=self.member)
        peer_link = TeamMember.objects.create(team=team, member=self.peer)
        job = self.export()
        self.permission.scope = "team"
        self.permission.save()
        self.download(job, 403)
        team_job = self.export()
        self.assertIn(b"peer-private", self.download(team_job))
        peer_link.delete()
        self.download(team_job, 403)

    def test_reassignment_invalidates_own_scope_without_role_change(self):
        self.permission.scope = "own"
        self.permission.save()
        job = self.export()
        self.mine.responsible_user = self.other
        self.mine.save()
        self.download(job, 403)

    def test_branch_revocation_invalidates_file(self):
        branch = Branch.objects.create(business=self.business, name="Office")
        grant = BranchAccess.objects.create(member=self.member)
        grant.branches.add(branch)
        job = self.export()
        grant.branches.clear()
        self.download(job, 403)

    def test_view_and_membership_revocation(self):
        job = self.export()
        self.permission.is_allowed = False
        self.permission.save()
        self.download(job, 403)
        self.member.is_active = False
        self.member.save()
        self.download(job, 404)

    def test_other_actor_and_foreign_business_cannot_download(self):
        job = self.export()
        self.api.force_authenticate(self.other)
        self.download(job, 404)
        stranger = User.objects.create_user(username="export-stranger", email="export-stranger@example.test")
        Business.objects.create(owner=stranger, name="Other", slug="export-other")
        self.api.force_authenticate(stranger)
        self.download(job, 404)

    def test_legacy_file_fails_closed_without_modifying_stored_bytes(self):
        job = self.export()
        with job.result_file.open("rb") as file:
            original = file.read()
        job.parameters_json = {}
        job.save(update_fields=["parameters_json"])
        self.download(job, 403)
        with job.result_file.open("rb") as file:
            self.assertEqual(file.read(), original)

    def test_capability_revocation(self):
        job = self.export()
        BusinessCapability.objects.filter(business=self.business, module_key="leads").update(is_enabled=False)
        self.download(job, 403)

    def test_analytics_team_lead_revocation(self):
        team = Team.objects.create(business=self.business, name="Managed team")
        link = TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer)
        _, queued = request_report_export(business=self.business, actor=self.actor,
            report_key="workspace_team", start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
        job = process_export_job(queued.pk)
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        self.download(job)
        link.is_lead = False
        link.save()
        self.download(job, 403)

    def test_worker_uses_scope_at_generation_and_rejects_revoked_actor(self):
        response = self.api.get("/api/export/leads/", {"business": self.business.pk})
        self.permission.scope = "own"
        self.permission.save()
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        self.assertNotIn(b"peer-private", self.download(job))
        response = self.api.get("/api/export/leads/", {"business": self.business.pk})
        User.objects.filter(pk=self.actor.pk).update(is_active=False)
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.FAILED)
        self.assertFalse(job.result_file)

    def test_analytics_rechecks_underlying_resource_scope(self):
        _, queued = request_report_export(business=self.business, actor=self.actor,
            report_key="workspace_overview", start_date=date(2026, 1, 1), end_date=date(2026, 1, 2))
        job = process_export_job(queued.pk)
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED, job.error)
        self.download(job)
        self.permission.scope = "own"
        self.permission.save()
        self.download(job, 403)

    def test_access_change_during_generation_does_not_publish_file(self):
        from apps.core.import_export import export_entity_response
        def changing_response(*args, **kwargs):
            response = export_entity_response(*args, **kwargs)
            self.permission.scope = "own"
            self.permission.save()
            return response
        response = self.api.get("/api/export/leads/", {"business": self.business.pk})
        with patch("apps.core.export_jobs.export_entity_response", side_effect=changing_response):
            job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.FAILED)
        self.assertFalse(job.result_file)
        self.download(job, 400)
