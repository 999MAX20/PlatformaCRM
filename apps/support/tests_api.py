from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.businesses.models import BusinessMember
from apps.support.messages import append_message
from apps.support.models import InternalNote, PublicMessage, SupportCase
from apps.support.services import assign_case
from apps.support.tests_domain import SupportFixture


class SupportAPITests(SupportFixture):
    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.employee)

    def clinic_url(self, case=None, action="", business=None):
        suffix = f"{case.pk}/{action + '/' if action else ''}" if case else ""
        return f"/api/support/cases/{suffix}?business={(business or self.business).pk}"

    def platform_url(self, case=None, action=""):
        suffix = f"{case.pk}/{action + '/' if action else ''}" if case else ""
        return f"/api/platform/support-cases/{suffix}"

    def test_clinic_create_list_detail_and_repeat(self):
        payload = {"subject": "Question", "text": "Please help"}
        first = self.api.post(self.clinic_url(), payload, format="json", HTTP_IDEMPOTENCY_KEY="api-case")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.api.post(self.clinic_url(), payload, format="json", HTTP_IDEMPOTENCY_KEY="api-case")
        self.assertEqual(first.data["id"], second.data["id"])
        listing = self.api.get(self.clinic_url())
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["unread_count"], 0)
        case = SupportCase.objects.get()
        detail = self.api.get(self.clinic_url(case))
        self.assertEqual(detail.data["number"], f"SUP-{case.pk:06d}")
        self.assertEqual(detail.data["available_actions"]["transitions"], [])
        self.assertFalse(detail.data["available_actions"]["internal_note"])

    def test_platform_can_create_without_crm_grant_and_does_not_impersonate_owner(self):
        self.api.force_authenticate(self.platform_manager)
        with override_settings(SUPPORT_REQUIRES_GRANT=True):
            response = self.api.post(self.platform_url(), {"business": self.business.pk, "subject": "Setup", "text": "We can help"}, format="json", HTTP_IDEMPOTENCY_KEY="manual-case")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["author"]["id"], self.platform_manager.pk)
        self.assertEqual(response.data["contact"]["id"], self.owner.pk)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.clinic_url()).data["count"], 1)
        self.api.force_authenticate(self.employee)
        self.assertEqual(self.api.get(self.clinic_url()).data["count"], 0)

    def test_clinic_context_cannot_be_overridden_in_body(self):
        response = self.api.post(self.clinic_url(), {"business": self.other_business.pk, "subject": "Subject", "text": "Body"}, format="json", HTTP_IDEMPOTENCY_KEY="bad-scope")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SupportCase.objects.exists())
        self.assertEqual(self.api.get("/api/support/cases/").status_code, 400)
        self.assertEqual(self.api.get(self.clinic_url(business=self.other_business)).status_code, 404)

    def test_same_business_other_author_and_cross_tenant_are_hidden(self):
        other_author = self.create(actor=self.colleague)
        foreign = self.create(actor=self.other_owner, business=self.other_business)
        for case in [other_author, foreign]:
            for action in ["", "messages", "events"]:
                self.assertEqual(self.api.get(self.clinic_url(case, action)).status_code, 404)
            self.assertEqual(self.api.post(self.clinic_url(case, "messages"), {"text": "intrusion"}, format="json", HTTP_IDEMPOTENCY_KEY="foreign-message").status_code, 404)
            self.assertEqual(self.api.post(self.clinic_url(case, "read"), {"through_id": 1}, format="json").status_code, 404)

    def test_clinic_privileged_roles_have_only_their_business_cases(self):
        own = self.create()
        colleague = self.create(actor=self.colleague)
        self.create(actor=self.other_owner, business=self.other_business)
        for actor in [self.owner, self.clinic_admin]:
            self.api.force_authenticate(actor)
            result = self.api.get(self.clinic_url())
            self.assertSetEqual({item["id"] for item in result.data["results"]}, {own.pk, colleague.pk})
            self.assertEqual(self.api.get(self.clinic_url(business=self.other_business)).status_code, 404)

    def test_private_notes_never_appear_in_clinic_details_search_messages_or_history(self):
        case = self.create()
        before = self.api.get(self.clinic_url(case)).data
        self.api.force_authenticate(self.platform_manager)
        note = self.api.post(self.platform_url(case, "internal-notes"), {"text": "INTERNAL-SECRET-PHRASE"}, format="json", HTTP_IDEMPOTENCY_KEY="private-note")
        self.assertEqual(note.status_code, 201, note.data)
        self.assertEqual(self.api.get(self.platform_url(case, "internal-notes")).data["count"], 1)
        self.api.force_authenticate(self.employee)
        self.assertEqual(self.api.get(self.platform_url(case, "internal-notes")).status_code, 403)
        self.assertEqual(self.api.get(self.clinic_url(case, "internal-notes")).status_code, 404)
        self.assertEqual(self.api.get(self.clinic_url(case)).data, before)
        for action in ["", "messages", "events"]:
            response = self.api.get(self.clinic_url(case, action))
            self.assertNotIn(b"INTERNAL-SECRET-PHRASE", response.content)
            self.assertNotIn(b"internal_notes", response.content)
        self.assertEqual(self.api.get(self.clinic_url() + "&search=INTERNAL-SECRET-PHRASE").data["count"], 0)

    def test_message_field_injection_cannot_publish_or_create_private_note(self):
        case = self.create()
        for extra in [{"internal": True}, {"author": self.owner.pk}, {"case": 999}, {"source": "platform"}]:
            response = self.api.post(self.clinic_url(case, "messages"), {"text": "injected", **extra}, format="json", HTTP_IDEMPOTENCY_KEY="inject")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(case.public_messages.count(), 1)
        self.assertFalse(InternalNote.objects.exists())

    def test_public_reply_unread_count_and_read_cursor(self):
        case = self.create()
        self.api.force_authenticate(self.platform_manager)
        self.assertEqual(self.api.get(self.platform_url(case)).data["unread_count"], 1)
        reply = self.api.post(self.platform_url(case, "messages"), {"text": "The answer"}, format="json", HTTP_IDEMPOTENCY_KEY="answer")
        self.assertEqual(reply.status_code, 201, reply.data)
        self.assertEqual(self.api.post(self.platform_url(case, "messages"), {"text": "The answer"}, format="json", HTTP_IDEMPOTENCY_KEY="answer").data["id"], reply.data["id"])
        self.api.force_authenticate(self.employee)
        self.assertEqual(self.api.get(self.clinic_url(case)).data["unread_count"], 1)
        self.assertEqual(self.api.get(self.clinic_url() + "&unread=true").data["count"], 1)
        read = self.api.post(self.clinic_url(case, "read"), {"through_id": reply.data["id"]}, format="json")
        self.assertEqual(read.status_code, 200, read.data)
        self.assertEqual(self.api.get(self.clinic_url(case)).data["unread_count"], 0)
        self.assertEqual(self.api.get(self.clinic_url() + "&unread=true").data["count"], 0)

    def test_platform_mutations_version_conflict_resolution_and_clinic_reopen(self):
        case = self.create()
        self.api.force_authenticate(self.platform_manager)
        assigned = self.api.post(self.platform_url(case, "assign"), {"assigned_to": self.platform_manager.pk, "version": 1}, format="json")
        self.assertEqual(assigned.status_code, 200, assigned.data)
        stale = self.api.post(self.platform_url(case, "assign"), {"assigned_to": None, "version": 1}, format="json")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.data["code"], "support_version_conflict")
        resolved = self.api.post(self.platform_url(case, "transition"), {"status": "resolved", "reason": "Fixed configuration", "version": 2}, format="json")
        self.assertEqual(resolved.status_code, 200, resolved.data)
        self.api.force_authenticate(self.employee)
        reopened = self.api.post(self.clinic_url(case, "reopen"), {"reason": "Still failing", "version": 3}, format="json")
        self.assertEqual(reopened.status_code, 200, reopened.data)
        self.assertEqual(reopened.data["status"], "in_progress")
        self.assertTrue(any(row["reason"] == "Fixed configuration" for row in self.api.get(self.clinic_url(case, "events")).data["results"]))

    def test_role_loss_and_disabled_membership_revoke_api_access(self):
        case = self.create()
        BusinessMember.objects.filter(user=self.employee).update(is_active=False)
        self.assertEqual(self.api.get(self.clinic_url(case)).status_code, 404)
        self.api.force_authenticate(self.platform_manager)
        get_user_model().objects.filter(pk=self.platform_manager.pk).update(role="staff")
        self.assertEqual(self.api.get(self.platform_url(case)).status_code, 403)
        self.assertEqual(self.api.get("/api/platform/support-cases/staff/").status_code, 403)

    def test_list_filters_page_size_and_scoped_query_count(self):
        for index in range(23):
            self.create(key=f"page-{index}")
        self.api.force_authenticate(self.platform_manager)
        with CaptureQueriesContext(connection) as queries:
            response = self.api.get(self.platform_url() + "?page_size=10&status=new&assignee=unassigned")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 23)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertLessEqual(len(queries), 8)
        following = self.api.get(response.data["next"])
        self.assertFalse({row["id"] for row in response.data["results"]} & {row["id"] for row in following.data["results"]})
        for query in ["page_size=101", "page=0", "status=invalid", "assignee=not-a-user", "unknown=1"]:
            self.assertEqual(self.api.get(self.platform_url() + "?" + query).status_code, 400)

    def test_inactive_assignments_are_visible_for_manual_reassignment(self):
        case = self.create()
        assign_case(actor=self.platform_admin, case_id=case.pk, assignee_id=self.platform_manager.pk, version=1)
        get_user_model().objects.filter(pk=self.platform_manager.pk).update(is_active=False)
        self.api.force_authenticate(self.platform_admin)
        result = self.api.get(self.platform_url() + "?assignee=unavailable")
        self.assertEqual(result.data["count"], 1)
        self.assertFalse(result.data["results"][0]["assignee"]["available"])
        staff = self.api.get("/api/platform/support-cases/staff/")
        self.assertNotIn(self.platform_manager.pk, [row["id"] for row in staff.data["results"]])
        self.assertNotIn(self.employee.pk, [row["id"] for row in staff.data["results"]])

    def test_append_pages_are_bounded_and_cannot_be_edited_or_deleted(self):
        case = self.create()
        for index in range(3):
            append_message(actor=self.employee, case_id=case.pk, text=f"Message {index}", idempotency_key=f"m-{index}")
        response = self.api.get(self.clinic_url(case, "messages") + "&page_size=2")
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertGreater(response.data["results"][0]["id"], response.data["results"][1]["id"])
        self.assertEqual(self.api.patch(self.clinic_url(case), {"status": "resolved"}).status_code, 405)
        self.assertEqual(self.api.delete(self.clinic_url(case)).status_code, 405)
        self.assertEqual(PublicMessage.objects.count(), 4)

    def test_anonymous_and_clinic_users_cannot_enter_platform_queue(self):
        self.assertEqual(self.api.get(self.platform_url()).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(self.clinic_url()).status_code, 401)
        self.assertEqual(self.api.get(self.platform_url()).status_code, 401)
