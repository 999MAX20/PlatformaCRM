from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import ensure_default_roles
from apps.businesses.models import Business, BusinessMember, BusinessRole


class BookingSettingsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="booking-settings-owner", email="booking-owner@example.test")
        self.member = User.objects.create_user(username="booking-settings-member", email="booking-member@example.test", full_name="Booking assignee")
        self.other = User.objects.create_user(username="booking-settings-foreign", email="booking-foreign@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Booking settings", slug="booking-settings")
        ensure_default_roles(self.business)
        self.membership = BusinessMember.objects.create(business=self.business, user=self.member, role="specialist",
            business_role=BusinessRole.objects.get(business=self.business, preset_key="specialist"))
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = f"/api/businesses/{self.business.pk}/"

    def test_owner_selects_and_clears_explicit_default(self):
        response = self.api.patch(self.url, {"ai_booking_responsible_user": self.member.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data.get("ai_booking_responsible_user"), self.member.pk)
        self.business.refresh_from_db()
        self.assertEqual(self.business.ai_booking_responsible_user_id, self.member.pk)
        response = self.api.patch(self.url, {"ai_booking_responsible_user": None}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["ai_booking_responsible_user"])

    def test_foreign_unknown_and_inactive_defaults_are_rejected(self):
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])
        for pk in (self.other.pk, self.member.pk, 999999):
            with self.subTest(pk=pk):
                response = self.api.patch(self.url, {"ai_booking_responsible_user": pk}, format="json")
                self.assertEqual(response.status_code, 400, response.data)

    def test_inactive_membership_rejected(self):
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        response = self.api.patch(self.url, {"ai_booking_responsible_user": self.member.pk}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_setting_and_options_require_settings_update(self):
        self.api.force_authenticate(self.member)
        self.assertEqual(self.api.patch(self.url, {"ai_booking_responsible_user": self.member.pk}, format="json").status_code, 403)
        self.assertEqual(self.api.get(self.url + "booking-responsible-options/").status_code, 403)

    def test_options_are_active_business_candidates_only(self):
        response = self.api.get(self.url + "booking-responsible-options/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({item["id"] for item in response.data}, {self.owner.pk, self.member.pk})
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.get(self.url + "booking-responsible-options/").status_code, 404)

    def test_unavailable_default_is_not_offered_or_accepted(self):
        self.membership.availability_status = "unavailable"
        self.membership.save(update_fields=["availability_status"])
        response = self.api.patch(self.url, {"ai_booking_responsible_user": self.member.pk}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        response = self.api.get(self.url + "booking-responsible-options/")
        self.assertEqual({item["id"] for item in response.data}, {self.owner.pk})

    def test_validated_default_is_rechecked_at_save(self):
        from apps.businesses.serializers import BusinessSerializer
        from rest_framework.exceptions import ValidationError
        serializer = BusinessSerializer(self.business, data={"ai_booking_responsible_user": self.member.pk}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            serializer.save()
        self.business.refresh_from_db()
        self.assertIsNone(self.business.ai_booking_responsible_user_id)
