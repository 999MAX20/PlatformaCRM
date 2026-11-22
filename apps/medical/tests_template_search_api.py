from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import tests_template_search as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateSearchAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateSearchTests.setUpTestData.__func__(cls)

    create = fixtures.TemplateSearchTests.create

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.root = "/api/medical/document-templates/"
        self.scope = {"business_id": self.business.pk}

    def test_approved_search_filters_scope_pagination_and_private_response(self):
        personal = self.create("personal")
        common = self.create("common", common=True)
        params = self.scope | {"q": "КАТЕГОРИЯ", "language": "kk", "service_id": self.service.pk, "limit": 1}
        first = self.api.get(self.root + "approved/", params)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first["Cache-Control"], "no-store, private")
        self.assertEqual(first.data["results"][0]["version_id"], common.pk)
        second = self.api.get(self.root + "approved/", params | {"before_id": first.data["next_before_id"]})
        self.assertEqual(second.data["results"][0]["version_id"], personal.pk)
        own = self.api.get(self.root + "approved/", params | {"scope": "personal"})
        self.assertEqual(own.data["results"][0]["version_id"], personal.pk)
        empty = self.api.get(self.root + "approved/", params | {"specialty": "Missing"})
        self.assertEqual(empty.data["results"], [])

    def test_personal_and_common_draft_search_keep_authorization(self):
        personal = self.create("personal", approved=False)
        common = self.create("common", common=True, approved=False)
        params = self.scope | {"category": "категория", "specialty": "оқу"}
        own = self.api.get(self.root, params)
        self.assertEqual(own.status_code, 200, own.data)
        self.assertEqual(own.data["results"][0]["version_id"], personal.pk)
        self.assertEqual(self.api.get(self.root + "common/", params).status_code, 403)
        self.api.force_authenticate(self.head)
        shared = self.api.get(self.root + "common/", params)
        self.assertEqual(shared.status_code, 200, shared.data)
        self.assertEqual(shared.data["results"][0]["version_id"], common.pk)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.root + "approved/", params).status_code, 403)

    def test_invalid_search_is_strict_and_does_not_enable_other_routes(self):
        for invalid in ({"q": "x" * 256}, {"language": "xx"}, {"service_id": 0},
                        {"scope": "foreign"}, {"patient_id": 1}):
            response = self.api.get(self.root + "approved/", self.scope | invalid)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(self.api.get(self.root + "pending-reviews/", self.scope | {"q": "test"}).status_code, 400)
