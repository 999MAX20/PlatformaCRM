from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.leads.models import Lead, LeadForm, LeadFormSubmission, LeadFormSubmissionError
from apps.leads.forms_service import submit_lead_form


class FormWriteBoundaryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="form-owner", email="form-owner@example.test", role="business_owner")
        self.other = User.objects.create_user(username="form-other", email="form-other@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Forms", slug="write-forms")
        self.foreign = Business.objects.create(owner=self.other, name="Foreign", slug="write-forms-foreign")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        BusinessMember.objects.create(business=self.foreign, user=self.other, role="owner")
        self.staff = User.objects.create_user(username="form-staff", email="form-staff@example.test")
        self.member = BusinessMember.objects.create(business=self.business, user=self.staff, role="operator")
        self.form = LeadForm.objects.create(business=self.business, name="Capture", title="Contact", default_responsible_user=self.owner)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def payload(self, user):
        return {"business": self.business.pk, "name": "New form", "title": "Contact", "default_responsible_user": user}

    def assert_default_rejected(self, user, statuses=(400,)):
        before = LeadForm.objects.count()
        response = self.api.post("/api/lead-forms/", self.payload(user.pk), format="json")
        self.assertIn(response.status_code, statuses, response.data)
        self.assertEqual(LeadForm.objects.count(), before)
        response = self.api.patch(f"/api/lead-forms/{self.form.pk}/", {"default_responsible_user": user.pk}, format="json")
        self.assertIn(response.status_code, statuses, response.data)
        self.form.refresh_from_db()
        self.assertEqual(self.form.default_responsible_user_id, self.owner.pk)

    def test_create_and_partial_update_reject_foreign_disabled_and_ineligible_defaults(self):
        self.assert_default_rejected(self.other)
        self.staff.is_active = False
        self.staff.save()
        self.assert_default_rejected(self.staff)
        self.staff.is_active = True
        self.staff.save()
        self.member.is_active = False
        self.member.save()
        self.assert_default_rejected(self.staff)
        self.member.is_active = True
        self.member.role = "accountant"
        self.member.save()
        self.assert_default_rejected(self.staff)
        self.member.role = "operator"
        self.member.availability_status = BusinessMember.AvailabilityStatuses.UNAVAILABLE
        self.member.save()
        self.assert_default_rejected(self.staff, statuses=(409,))

    def test_valid_default_and_null_owner_default_preserve_capture(self):
        response = self.api.post("/api/lead-forms/", self.payload(self.staff.pk), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        form = LeadForm.objects.get(pk=response.data["id"])
        self.api.force_authenticate(None)
        response = self.api.post(f"/api/public/forms/{form.public_id}/submit/", {"full_name": "Visitor", "phone": "+77012345670"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Lead.objects.get(pk=response.data["lead_id"]).responsible_user_id, self.staff.pk)
        self.api.force_authenticate(self.owner)
        response = self.api.patch(f"/api/lead-forms/{form.pk}/", {"default_responsible_user": None}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.api.force_authenticate(None)
        response = self.api.post(f"/api/public/forms/{form.public_id}/submit/", {"full_name": "Visitor", "phone": "+77012345671"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Lead.objects.get(pk=response.data["lead_id"]).responsible_user_id, self.owner.pk)

    def test_capture_rechecks_stale_defaults_without_creating_partial_records(self):
        self.api.force_authenticate(None)
        for user in (self.other, self.staff):
            with self.subTest(user=user.pk):
                self.form.default_responsible_user = user
                self.form.save()
                self.member.is_active = False
                self.member.save()
                before = (Client.objects.count(), Lead.objects.count(), LeadFormSubmission.objects.count())
                response = self.api.post(f"/api/public/forms/{self.form.public_id}/submit/", {"full_name": "Visitor", "phone": "+77012345672"}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(before, (Client.objects.count(), Lead.objects.count(), LeadFormSubmission.objects.count()))
                self.assertNotIn(user.email, str(response.data))
        self.assertEqual(LeadFormSubmissionError.objects.filter(form=self.form).count(), 2)

    def test_submission_and_error_logs_are_read_only_including_inherited_actions(self):
        submission = LeadFormSubmission.objects.create(form=self.form, business=self.business)
        error = LeadFormSubmissionError.objects.create(form=self.form, business=self.business, error_message="Invalid input")
        for endpoint, record in (("lead-form-submissions", submission), ("lead-form-submission-errors", error)):
            with self.subTest(endpoint=endpoint):
                url = f"/api/{endpoint}/{record.pk}/"
                self.assertEqual(self.api.get(url).status_code, 200)
                self.assertEqual(self.api.post(f"/api/{endpoint}/", {"business": self.business.pk, "form": self.form.pk}, format="json").status_code, 405)
                for method in (self.api.patch, self.api.put, self.api.delete):
                    self.assertEqual(method(url, {"business": self.foreign.pk}, format="json").status_code, 405)
                for action in ("archive", "restore"):
                    self.assertEqual(self.api.post(f"{url}{action}/", {}, format="json").status_code, 405)
                self.assertTrue(type(record).objects.filter(pk=record.pk).exists())
                self.api.force_authenticate(self.other)
                self.assertEqual(self.api.get(url).status_code, 404)
                self.api.force_authenticate(self.owner)

    def test_assignment_scope_and_business_ownership_cannot_be_bypassed(self):
        role = BusinessRole.objects.create(business=self.business, name="Own assignments")
        self.member.business_role = role
        self.member.save()
        for action, scope in (("view", "business"), ("create", "business"), ("update", "own")):
            RolePermission.objects.create(business_role=role, resource="leads", action=action, scope=scope)
        self.api.force_authenticate(self.staff)
        response = self.api.post("/api/lead-forms/", self.payload(self.owner.pk), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        response = self.api.post("/api/lead-forms/", self.payload(self.staff.pk), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.api.force_authenticate(self.owner)
        response = self.api.patch(f"/api/lead-forms/{self.form.pk}/", {"business": self.foreign.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.form.refresh_from_db()
        self.assertEqual(self.form.business_id, self.business.pk)

    def test_capture_does_not_trust_a_previously_loaded_active_user(self):
        self.form.default_responsible_user = self.staff
        self.form.save()
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        self.assertTrue(self.form.default_responsible_user.is_active)
        with self.assertRaisesMessage(ValueError, "responsible user is not available"):
            submit_lead_form(lead_form=self.form, payload={"full_name": "Visitor", "phone": "+77012345673"})
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_foreign_and_missing_default_errors_are_indistinguishable(self):
        errors = []
        for user_id in (self.other.pk, 999999):
            response = self.api.post("/api/lead-forms/", self.payload(user_id), format="json")
            self.assertEqual(response.status_code, 400, response.data)
            errors.append(response.data["errors"])
        self.assertEqual(errors[0], errors[1])

    def test_admin_can_inspect_but_cannot_write_submission_logs(self):
        self.owner.is_staff = True
        self.owner.is_superuser = True
        self.owner.save()
        self.client.force_login(self.owner)
        submission = LeadFormSubmission.objects.create(form=self.form, business=self.business)
        error = LeadFormSubmissionError.objects.create(form=self.form, business=self.business, error_message="Invalid input")
        for model_name, record in (("leadformsubmission", submission), ("leadformsubmissionerror", error)):
            base = f"/admin/leads/{model_name}/"
            self.assertEqual(self.client.get(f"{base}{record.pk}/change/").status_code, 200)
            self.assertEqual(self.client.post(f"{base}{record.pk}/change/", {"business": self.foreign.pk}).status_code, 403)
            self.assertEqual(self.client.post(f"{base}{record.pk}/delete/", {"post": "yes"}).status_code, 403)
            self.assertEqual(self.client.post(f"{base}add/", {"business": self.business.pk}).status_code, 403)
            self.assertTrue(type(record).objects.filter(pk=record.pk).exists())
