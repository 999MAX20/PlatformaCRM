import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import AuditLog, CRMCommandIdempotency
from apps.support.access import get_case, scoped_cases
from apps.support.messages import append_message, mark_read
from apps.support.models import CaseEvent, InternalNote, PublicMessage, ReadState, SupportCase
from apps.support.services import SupportVersionConflict, assign_case, create_case, reopen_case, transition_case


class SupportFixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(name, role="staff"):
            return get_user_model().objects.create(username=name, email=f"{name}@example.com", full_name=name, role=role)

        cls.owner = user("support-owner", "business_owner")
        cls.other_owner = user("support-other-owner", "business_owner")
        cls.employee = user("support-employee")
        cls.colleague = user("support-colleague")
        cls.clinic_admin = user("support-clinic-admin")
        cls.platform_admin = user("support-platform-admin", "platform_admin")
        cls.platform_manager = user("support-platform-manager", "platform_manager")
        cls.business = Business.objects.create(name="Support clinic", slug="support-clinic", owner=cls.owner)
        cls.other_business = Business.objects.create(name="Other clinic", slug="other-support-clinic", owner=cls.other_owner)
        for actor, role in [(cls.employee, "operator"), (cls.colleague, "manager"), (cls.clinic_admin, "admin")]:
            BusinessMember.objects.create(business=cls.business, user=actor, role=role)

    def create(self, actor=None, business=None, platform=False, key=None):
        result = create_case(
            actor=actor or self.employee, business_id=(business or self.business).pk,
            subject="Need help", text="Please help with settings", platform=platform,
            idempotency_key=key or uuid.uuid4().hex,
        )
        return SupportCase.objects.get(pk=result.data["case_id"])


class SupportDomainTests(SupportFixture):
    def test_clinic_creation_is_atomic_and_idempotent(self):
        case = self.create(key="create-once")
        again = self.create(key="create-once")
        self.assertEqual(case.pk, again.pk)
        self.assertEqual(case.requester, self.employee)
        self.assertEqual(case.source, "clinic")
        self.assertEqual(case.public_messages.count(), 1)
        self.assertEqual(case.events.count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="SupportCase").count(), 1)

    def test_platform_creation_keeps_actual_author_and_owner_contact(self):
        case = self.create(actor=self.platform_manager, platform=True)
        self.assertEqual(case.created_by, self.platform_manager)
        self.assertEqual(case.requester, self.owner)
        self.assertEqual(case.public_messages.get().author, self.platform_manager)
        self.assertEqual(case.source, "platform")

    def test_clinic_visibility_and_cross_business_denial(self):
        own = self.create()
        colleague = self.create(actor=self.colleague)
        foreign = self.create(actor=self.other_owner, business=self.other_business)
        for actor, ids in [(self.employee, [own.pk]), (self.colleague, [colleague.pk]), (self.owner, [own.pk, colleague.pk]), (self.clinic_admin, [own.pk, colleague.pk])]:
            with self.subTest(actor=actor.username):
                self.assertSetEqual(set(scoped_cases(actor).values_list("pk", flat=True)), set(ids))
                with self.assertRaises(Http404):
                    get_case(actor, foreign.pk)
        with self.assertRaises(Http404):
            get_case(self.employee, colleague.pk)

    def test_platform_role_does_not_grant_clinic_membership(self):
        case = self.create()
        with self.assertRaises(Http404):
            get_case(self.platform_admin, case.pk)
        self.assertEqual(get_case(self.platform_manager, case.pk, platform=True), case)
        with self.assertRaises(PermissionDenied):
            get_case(self.employee, case.pk, platform=True)

    def test_create_rechecks_access_before_idempotency_replay(self):
        self.create(key="revoke-create")
        BusinessMember.objects.filter(user=self.employee).update(is_active=False)
        with self.assertRaises(Http404):
            self.create(key="revoke-create")
        self.assertEqual(SupportCase.objects.count(), 1)

    def test_payload_collision_and_missing_keys_are_rejected(self):
        self.create(key="collision")
        with self.assertRaises(IdempotencyConflict):
            create_case(actor=self.employee, business_id=self.business.pk, subject="Different", text="Text", idempotency_key="collision")
        with self.assertRaises(ValidationError):
            create_case(actor=self.employee, business_id=self.business.pk, subject="Subject", text="Text", idempotency_key="")
        self.assertEqual(SupportCase.objects.count(), 1)

    def test_invalid_case_content_and_foreign_business(self):
        for subject, text in [(" ", "text"), ("x" * 201, "text"), ("subject", " "), ("subject", "x" * 6001)]:
            with self.subTest(subject=subject[:10], size=len(text)), self.assertRaises(ValidationError):
                create_case(actor=self.employee, business_id=self.business.pk, subject=subject, text=text, idempotency_key=uuid.uuid4().hex)
        with self.assertRaises(Http404):
            self.create(business=self.other_business)
        self.assertFalse(SupportCase.objects.exists())

    def test_assignment_only_to_active_platform_employee_and_stale_version(self):
        case = self.create()
        with self.assertRaises(ValidationError):
            assign_case(actor=self.platform_admin, case_id=case.pk, assignee_id=self.employee.pk, version=1)
        updated = assign_case(actor=self.platform_manager, case_id=case.pk, assignee_id=self.platform_admin.pk, version=1)
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.status, "new")
        with self.assertRaises(SupportVersionConflict):
            assign_case(actor=self.platform_admin, case_id=case.pk, assignee_id=None, version=1)
        get_user_model().objects.filter(pk=self.platform_admin.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            assign_case(actor=self.platform_manager, case_id=case.pk, assignee_id=self.platform_admin.pk, version=2)
        self.assertEqual(case.events.filter(kind="assigned").count(), 1)

    def test_platform_role_loss_and_disabled_actor_are_immediate(self):
        case = self.create(actor=self.platform_manager, platform=True, key="platform-replay")
        get_user_model().objects.filter(pk=self.platform_manager.pk).update(role="staff")
        with self.assertRaises(PermissionDenied):
            self.create(actor=self.platform_manager, platform=True, key="platform-replay")
        with self.assertRaises(PermissionDenied):
            get_case(self.platform_manager, case.pk, platform=True)
        get_user_model().objects.filter(pk=self.employee.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.create()

    def test_resolution_requires_outcome_and_explicit_reopen_requires_reason(self):
        case = self.create()
        with self.assertRaises(ValidationError):
            transition_case(actor=self.platform_manager, case_id=case.pk, status="resolved", reason=" ", version=1)
        case = transition_case(actor=self.platform_manager, case_id=case.pk, status="resolved", reason="Settings restored", version=1)
        self.assertIsNotNone(case.resolved_at)
        append_message(actor=self.employee, case_id=case.pk, text="One more question", idempotency_key="after-resolved")
        case.refresh_from_db()
        self.assertEqual(case.status, "resolved")
        with self.assertRaises(ValidationError):
            reopen_case(actor=self.employee, case_id=case.pk, reason="", version=2)
        case = reopen_case(actor=self.employee, case_id=case.pk, reason="The issue returned", version=2)
        self.assertEqual(case.status, "in_progress")
        self.assertIsNone(case.resolved_at)
        self.assertEqual(case.events.get(kind="reopened").reason, "The issue returned")

    def test_non_author_employee_cannot_reopen_but_owner_and_admin_can(self):
        for authorized in [self.owner, self.clinic_admin]:
            case = self.create()
            transition_case(actor=self.platform_admin, case_id=case.pk, status="resolved", reason="Done", version=1)
            with self.assertRaises(Http404):
                reopen_case(actor=self.colleague, case_id=case.pk, reason="Again", version=2)
            reopened = reopen_case(actor=authorized, case_id=case.pk, reason="Again", version=2)
            self.assertEqual(reopened.status, "in_progress")

    def test_lifecycle_graph_and_clinic_cannot_resolve_or_assign(self):
        case = self.create()
        with self.assertRaises(PermissionDenied):
            transition_case(actor=self.employee, case_id=case.pk, status="resolved", reason="Done", version=1)
        with self.assertRaises(PermissionDenied):
            assign_case(actor=self.owner, case_id=case.pk, assignee_id=None, version=1)
        for status in ["in_progress", "waiting_clinic", "in_progress", "waiting_internal", "resolved"]:
            case = transition_case(actor=self.platform_admin, case_id=case.pk, status=status, reason="Handled", version=case.version)
        with self.assertRaises(InvalidTransition):
            transition_case(actor=self.platform_admin, case_id=case.pk, status="in_progress", reason="", version=case.version)

    def test_failed_audit_rolls_back_case_and_idempotency_claim(self):
        with patch("apps.support.services.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.create(key="rollback")
        self.assertFalse(SupportCase.objects.exists())
        self.assertFalse(PublicMessage.objects.exists())
        self.assertFalse(CaseEvent.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.create(key="rollback")
        self.assertEqual(SupportCase.objects.count(), 1)

    def test_failed_transition_audit_rolls_back_state_and_history(self):
        case = self.create()
        with patch("apps.support.services.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                transition_case(actor=self.platform_admin, case_id=case.pk, status="resolved", reason="Done", version=1)
        case.refresh_from_db()
        self.assertEqual(case.status, "new")
        self.assertEqual(case.version, 1)
        self.assertEqual(case.events.count(), 1)

    def test_public_message_retry_and_role_loss_do_not_duplicate_or_leak(self):
        case = self.create()
        kwargs = dict(actor=self.employee, case_id=case.pk, text="Follow-up", idempotency_key="message-once")
        first = append_message(**kwargs)
        self.assertEqual(append_message(**kwargs).data, first.data)
        self.assertEqual(case.public_messages.count(), 2)
        BusinessMember.objects.filter(user=self.employee).update(is_active=False)
        with self.assertRaises(Http404):
            append_message(**kwargs)

    def test_internal_notes_are_separate_and_do_not_change_public_case_state(self):
        case = self.create()
        before = (case.updated_at, case.version, case.last_public_message_at)
        with self.assertRaises(PermissionDenied):
            append_message(actor=self.employee, case_id=case.pk, text="secret", idempotency_key="bad-note", internal=True)
        args = dict(actor=self.platform_manager, case_id=case.pk, text="private operational note", idempotency_key="note-once", internal=True, platform=True)
        append_message(**args)
        append_message(**args)
        case.refresh_from_db()
        self.assertEqual(before, (case.updated_at, case.version, case.last_public_message_at))
        self.assertEqual(InternalNote.objects.count(), 1)
        self.assertEqual(case.public_messages.count(), 1)
        self.assertNotIn("private operational note", json.dumps(list(AuditLog.objects.values("metadata"))))

    def test_read_cursor_is_monotonic_and_cannot_use_other_case_message(self):
        case = self.create()
        first = case.public_messages.get()
        append_message(actor=self.platform_manager, case_id=case.pk, text="Response", idempotency_key="reply", platform=True)
        last = case.public_messages.last()
        mark_read(actor=self.employee, case_id=case.pk, through_id=last.pk)
        mark_read(actor=self.employee, case_id=case.pk, through_id=first.pk)
        self.assertEqual(ReadState.objects.get().last_read_message_id, last.pk)
        other = self.create(actor=self.colleague)
        with self.assertRaises(ValidationError):
            mark_read(actor=self.employee, case_id=case.pk, through_id=other.public_messages.get().pk)
        with self.assertRaises(Http404):
            mark_read(actor=self.employee, case_id=other.pk, through_id=other.public_messages.get().pk)
