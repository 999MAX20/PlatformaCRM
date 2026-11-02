from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import Segment, SegmentFilter, Tag, TaggedObject
from apps.activities.segments import evaluate_segment_queryset
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client


class TaggedClientQueryRegressionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="pg-tag-owner", email="pg-tag-owner@example.com",
            password=None, role=User.Roles.BUSINESS_OWNER,
        )
        self.other_owner = User.objects.create_user(
            username="pg-tag-other", email="pg-tag-other@example.com",
            password=None, role=User.Roles.BUSINESS_OWNER,
        )
        self.business = Business.objects.create(owner=self.owner, name="PG tags", slug="pg-tags")
        self.other = Business.objects.create(owner=self.other_owner, name="Other tags", slug="pg-other-tags")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Roles.OWNER)
        self.client = Client.objects.create(business=self.business, full_name="Tagged")
        self.untagged = Client.objects.create(business=self.business, full_name="Untagged")
        self.foreign_client = Client.objects.create(business=self.other, full_name="Foreign")
        self.tag = Tag.objects.create(business=self.business, name="Scoped")
        self.foreign_tag = Tag.objects.create(business=self.other, name="Foreign")
        TaggedObject.objects.create(business=self.business, tag=self.tag, entity_type="client", entity_id=str(self.client.id))
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_canonical_tag_id_filters_client_list_and_summary(self):
        response = self.api.get("/api/clients/", {"business": self.business.id, "tag": self.tag.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["summary"]["total"], 1)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.client.id])

    def test_malformed_generic_ids_and_other_entity_or_business_do_not_match(self):
        TaggedObject.objects.create(business=self.business, tag=self.tag, entity_type="client", entity_id="not-a-number")
        TaggedObject.objects.create(business=self.business, tag=self.tag, entity_type="lead", entity_id=str(self.untagged.id))
        TaggedObject.objects.create(business=self.other, tag=self.foreign_tag, entity_type="client", entity_id=str(self.foreign_client.id))
        response = self.api.get("/api/clients/", {"business": self.business.id, "tag": self.tag.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.client.id])
        foreign = self.api.get("/api/clients/", {"business": self.business.id, "tag": self.foreign_tag.id})
        self.assertEqual(foreign.status_code, 200)
        self.assertEqual(foreign.data["count"], 0)

    def test_segment_tag_filter_uses_same_tenant_and_text_id_rules(self):
        TaggedObject.objects.create(business=self.business, tag=self.tag, entity_type="client", entity_id="not-a-number")
        segment = Segment.objects.create(business=self.business, name="Tagged segment")
        SegmentFilter.objects.create(
            business=self.business, segment=segment, field=SegmentFilter.Fields.TAG,
            operator=SegmentFilter.Operators.IN, value_json={"values": [self.tag.id]},
        )
        self.assertEqual(list(evaluate_segment_queryset(segment).values_list("id", flat=True)), [self.client.id])
