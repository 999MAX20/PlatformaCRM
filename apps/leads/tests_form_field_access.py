from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.models import AuditLog
from apps.leads.models import LeadForm, LeadFormField


class LeadFormFieldAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="field-owner", email="field-owner@example.com", password="test", role="business_owner")
        self.other = User.objects.create_user(username="field-other", email="field-other@example.com", password="test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Fields", slug="fields")
        self.foreign = Business.objects.create(owner=self.other, name="Foreign", slug="foreign-fields")
        self.second = Business.objects.create(owner=self.owner, name="Second", slug="second-fields")
        self.form = LeadForm.objects.create(business=self.business, name="Contact", title="Contact")
        self.foreign_form = LeadForm.objects.create(business=self.foreign, name="Foreign", title="Foreign")
        self.second_form = LeadForm.objects.create(business=self.second, name="Second", title="Second")
        self.field = LeadFormField.objects.create(form=self.form, key="phone", label="Phone", field_type="phone")
        self.foreign_field = LeadFormField.objects.create(form=self.foreign_form, key="phone", label="Foreign")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = f"/api/lead-form-fields/{self.field.pk}/"

    def test_owner_create_detail_patch_put_delete_and_history_tenant(self):
        response = self.api.post("/api/lead-form-fields/", {
            "form": self.form.pk, "key": "message", "label": "Message", "field_type": "textarea",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        url = f"/api/lead-form-fields/{pk}/"
        self.assertEqual(self.api.get(url).status_code, 200)
        self.assertEqual(self.api.patch(url, {"label": "Question"}, format="json").status_code, 200)
        self.assertEqual(self.api.put(url, {
            "form": self.form.pk, "key": "message", "label": "Comment", "field_type": "text",
        }, format="json").status_code, 200)
        self.assertEqual(self.api.delete(url).status_code, 204)
        self.assertFalse(LeadFormField.objects.filter(pk=pk).exists())
        audit = AuditLog.objects.filter(entity_type="LeadFormField", entity_id=str(pk))
        self.assertEqual(audit.count(), 4)
        self.assertEqual(set(audit.values_list("business_id", flat=True)), {self.business.pk})
        activity = ActivityEvent.objects.filter(entity_type="LeadFormField", entity_id=str(pk))
        self.assertEqual(activity.count(), 4)
        self.assertEqual(set(activity.values_list("business_id", flat=True)), {self.business.pk})

    def test_list_and_detail_never_return_foreign_fields(self):
        response = self.api.get("/api/lead-form-fields/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({r["id"] for r in response.data["results"]}, {self.field.pk})
        self.assertEqual(self.api.get(self.url).status_code, 200)
        self.assertEqual(self.api.get(f"/api/lead-form-fields/{self.foreign_field.pk}/").status_code, 404)

    def test_foreign_parent_create_is_denied_before_write(self):
        count = LeadFormField.objects.count()
        response = self.api.post("/api/lead-form-fields/", {
            "form": self.foreign_form.pk, "key": "message", "label": "No",
        }, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(LeadFormField.objects.count(), count)

    def test_editor_form_list_filters_selected_business_and_validates_filter(self):
        response = self.api.get("/api/lead-forms/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["id"] for r in response.data["results"]], [self.form.pk])
        self.assertEqual(self.api.get("/api/lead-forms/", {"business": self.foreign.pk}).data["results"], [])
        self.assertEqual(self.api.get("/api/lead-forms/", {"business": "invalid"}).status_code, 400)

    def test_reparent_cannot_change_business_even_when_actor_owns_both(self):
        for form in (self.foreign_form, self.second_form):
            with self.subTest(form=form.pk):
                response = self.api.patch(self.url, {"form": form.pk}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.field.refresh_from_db()
                self.assertEqual(self.field.form_id, self.form.pk)

    def test_invalid_parent_and_duplicate_key_rejected_without_changes(self):
        for payload in ({"form": None}, {"form": 999999}):
            self.assertEqual(self.api.patch(self.url, payload, format="json").status_code, 400)
        response = self.api.post("/api/lead-form-fields/", {
            "form": self.form.pk, "key": "phone", "label": "Duplicate",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(LeadFormField.objects.filter(form=self.form).count(), 1)

    def test_view_only_role_reads_but_cannot_write(self):
        actor = User.objects.create_user(username="field-reader", email="field-reader@example.com", password="test", role="business_manager")
        role = BusinessRole.objects.create(business=self.business, name="Reader")
        RolePermission.objects.create(business_role=role, resource="leads", action="view", scope="business")
        for action in ("create", "update", "delete"):
            RolePermission.objects.create(business_role=role, resource="leads", action=action, scope="none", is_allowed=False)
        member = BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        self.api.force_authenticate(actor)
        self.assertEqual(self.api.get(self.url).status_code, 200)
        for method, url, payload in (
            (self.api.post, "/api/lead-form-fields/", {"form": self.form.pk, "key": "new", "label": "New"}),
            (self.api.patch, self.url, {"label": "Denied"}),
            (self.api.delete, self.url, {}),
        ):
            self.assertEqual(method(url, payload, format="json").status_code, 403)
        self.field.refresh_from_db()
        self.assertEqual(self.field.label, "Phone")
        member.is_active = False
        member.save(update_fields=["is_active"])
        self.assertEqual(self.api.get(self.url).status_code, 404)

    def test_current_role_actions_allow_editor_without_owner_status(self):
        actor = User.objects.create_user(username="field-editor", email="field-editor@example.com", password="test", role="business_manager")
        role = BusinessRole.objects.create(business=self.business, name="Editor")
        for action in ("view", "create", "update", "delete"):
            RolePermission.objects.create(business_role=role, resource="leads", action=action, scope="business")
        BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        self.api.force_authenticate(actor)
        self.assertEqual(self.api.patch(self.url, {"label": "Allowed"}, format="json").status_code, 200)
        RolePermission.objects.filter(business_role=role, action="update").update(is_allowed=False, scope="none")
        self.assertEqual(self.api.patch(self.url, {"label": "Denied"}, format="json").status_code, 403)
