from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.crm.models import Deal, Pipeline, PipelineStage, StageTransition


class PipelineRelationshipBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="pipeline-owner", email="pipeline-owner@example.test", role="business_owner")
        cls.foreign_owner = User.objects.create_user(username="pipeline-foreign", email="pipeline-foreign@example.test", role="business_owner")
        cls.business = Business.objects.create(owner=cls.owner, name="Own", slug="pipeline-own")
        cls.foreign_business = Business.objects.create(owner=cls.foreign_owner, name="Foreign", slug="pipeline-foreign")
        cls.pipeline = Pipeline.objects.create(business=cls.business, name="First", slug="first")
        cls.second = Pipeline.objects.create(business=cls.business, name="Second", slug="second")
        cls.foreign = Pipeline.objects.create(business=cls.foreign_business, name="Foreign", slug="foreign")
        cls.start = PipelineStage.objects.create(business=cls.business, pipeline=cls.pipeline, name="Start")
        cls.finish = PipelineStage.objects.create(business=cls.business, pipeline=cls.pipeline, name="Finish", order=1)
        cls.second_stage = PipelineStage.objects.create(business=cls.business, pipeline=cls.second, name="Other")
        cls.foreign_stage = PipelineStage.objects.create(business=cls.foreign_business, pipeline=cls.foreign, name="Foreign")
        cls.transition = StageTransition.objects.create(business=cls.business, pipeline=cls.pipeline, from_stage=cls.start, to_stage=cls.finish)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_stage_create_rejects_foreign_pipeline_without_polluting_board(self):
        before = list(self.foreign.stages.values_list("pk", flat=True))
        response = self.api.post("/api/pipeline-stages/", {
            "business": self.business.pk, "pipeline": self.foreign.pk, "name": "Injected",
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(list(self.foreign.stages.values_list("pk", flat=True)), before)

    def test_transition_create_rejects_stage_from_another_pipeline(self):
        response = self.api.post("/api/stage-transitions/", {
            "business": self.business.pk, "pipeline": self.pipeline.pk,
            "from_stage": self.start.pk, "to_stage": self.second_stage.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(StageTransition.objects.count(), 1)

    def test_partial_transition_change_revalidates_existing_endpoints(self):
        response = self.api.patch(f"/api/stage-transitions/{self.transition.pk}/", {"pipeline": self.second.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.transition.refresh_from_db()
        self.assertEqual(self.transition.pipeline_id, self.pipeline.pk)

    def test_stage_cannot_move_and_break_existing_transition(self):
        response = self.api.patch(f"/api/pipeline-stages/{self.start.pk}/", {"pipeline": self.second.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.start.refresh_from_db()
        self.assertEqual(self.start.pipeline_id, self.pipeline.pk)

    def test_every_transition_link_is_checked_on_create_and_partial_update(self):
        base = {"business": self.business.pk, "pipeline": self.pipeline.pk,
                "from_stage": self.finish.pk, "to_stage": self.start.pk}
        invalid = ({"pipeline": self.foreign.pk}, {"pipeline": self.second.pk},
                   {"from_stage": self.foreign_stage.pk}, {"to_stage": self.foreign_stage.pk},
                   {"from_stage": self.second_stage.pk}, {"to_stage": self.second_stage.pk})
        before = (StageTransition.objects.count(), AuditLog.objects.count(), ActivityEvent.objects.count())
        for change in invalid:
            with self.subTest(change=change):
                response = self.api.post("/api/stage-transitions/", {**base, **change}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                response = self.api.patch(f"/api/stage-transitions/{self.transition.pk}/", change, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.transition.refresh_from_db()
        self.assertEqual((self.transition.pipeline_id, self.transition.from_stage_id, self.transition.to_stage_id),
                         (self.pipeline.pk, self.start.pk, self.finish.pk))
        self.assertEqual((StageTransition.objects.count(), AuditLog.objects.count(), ActivityEvent.objects.count()), before)

    def test_put_and_foreign_stage_reparent_leave_nested_boards_unchanged(self):
        self.api.force_authenticate(self.foreign_owner)
        before = self.api.get(f"/api/pipelines/{self.foreign.pk}/board/").data
        self.api.force_authenticate(self.owner)
        for method in (self.api.patch, self.api.put):
            response = method(f"/api/pipeline-stages/{self.start.pk}/", {
                "business": self.business.pk, "pipeline": self.foreign.pk, "name": "Changed",
            }, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            response = method(f"/api/stage-transitions/{self.transition.pk}/", {
                "business": self.business.pk, "pipeline": self.pipeline.pk,
                "from_stage": self.start.pk, "to_stage": self.foreign_stage.pk,
            }, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.start.refresh_from_db()
        self.assertEqual((self.start.pipeline_id, self.start.name), (self.pipeline.pk, "Start"))
        self.api.force_authenticate(self.foreign_owner)
        after = self.api.get(f"/api/pipelines/{self.foreign.pk}/board/")
        self.assertEqual(after.status_code, 200)
        self.assertEqual(after.data, before)
        nested = self.api.get(f"/api/pipelines/{self.foreign.pk}/")
        self.assertEqual([stage["id"] for stage in nested.data["stages"]], [self.foreign_stage.pk])

    def test_legacy_mismatched_stage_business_is_not_accepted_as_endpoint(self):
        # An old malformed row must not make a newly created edge valid.
        malformed = PipelineStage.objects.create(business=self.foreign_business, pipeline=self.pipeline, name="Legacy invalid")
        for field in ("from_stage", "to_stage"):
            response = self.api.patch(f"/api/stage-transitions/{self.transition.pk}/", {field: malformed.pk}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn(field, str(response.data))

    def test_valid_create_update_and_deal_move_keep_audit_and_board(self):
        response = self.api.post("/api/pipeline-stages/", {
            "business": self.business.pk, "pipeline": self.pipeline.pk, "name": "Negotiation", "order": 2,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        stage_id = response.data["id"]
        response = self.api.patch(f"/api/pipeline-stages/{stage_id}/", {
            "pipeline": self.pipeline.pk, "name": "Review", "probability": 40,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.post("/api/stage-transitions/", {
            "business": self.business.pk, "pipeline": self.pipeline.pk,
            "from_stage": self.start.pk, "to_stage": stage_id,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        transition_id = response.data["id"]
        response = self.api.patch(f"/api/stage-transitions/{transition_id}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.patch(f"/api/stage-transitions/{transition_id}/", {"from_stage": self.finish.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(AuditLog.objects.filter(entity_type="PipelineStage", entity_id=str(stage_id), action="create").exists())
        self.assertTrue(AuditLog.objects.filter(entity_type="StageTransition", entity_id=str(transition_id), action="update").exists())
        customer = Client.objects.create(business=self.business, full_name="Deal client")
        deal = Deal.objects.create(business=self.business, pipeline=self.pipeline, stage=self.start,
                                   client=customer, title="Normal deal", owner=self.owner)
        response = self.api.post(f"/api/deals/{deal.pk}/move-stage/", {"stage": stage_id}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        deal.refresh_from_db()
        self.assertEqual(deal.stage_id, stage_id)
        self.assertEqual(deal.stage_history.count(), 1)
        board = self.api.get(f"/api/pipelines/{self.pipeline.pk}/board/")
        self.assertEqual(board.status_code, 200, board.data)
        row = next(stage for stage in board.data["stages"] if stage["id"] == stage_id)
        self.assertEqual([item["id"] for item in row["deals"]], [deal.pk])

    def test_transition_can_change_all_links_to_another_consistent_pipeline(self):
        other_finish = PipelineStage.objects.create(business=self.business, pipeline=self.second, name="Second finish")
        response = self.api.put(f"/api/stage-transitions/{self.transition.pk}/", {
            "business": self.business.pk, "pipeline": self.second.pk,
            "from_stage": self.second_stage.pk, "to_stage": other_finish.pk,
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.transition.refresh_from_db()
        self.assertEqual((self.transition.pipeline_id, self.transition.from_stage_id, self.transition.to_stage_id),
                         (self.second.pk, self.second_stage.pk, other_finish.pk))

    def test_read_only_role_cannot_create_or_change_configuration(self):
        actor = User.objects.create_user(username="pipeline-reader", email="pipeline-reader@example.test", role="business_operator")
        role = BusinessRole.objects.create(business=self.business, name="Read deals only")
        for action in ("view", "create", "update", "delete"):
            RolePermission.objects.create(business_role=role, resource="deals", action=action, scope="business", is_allowed=action == "view")
        BusinessMember.objects.create(business=self.business, user=actor, role="operator", business_role=role)
        self.api.force_authenticate(actor)
        self.assertEqual(self.api.get(f"/api/pipelines/{self.pipeline.pk}/board/").status_code, 200)
        for path, instance, payload in (
            ("pipeline-stages", self.start, {"business": self.business.pk, "pipeline": self.pipeline.pk, "name": "Forbidden"}),
            ("stage-transitions", self.transition, {"business": self.business.pk, "pipeline": self.pipeline.pk,
                                                   "from_stage": self.finish.pk, "to_stage": self.start.pk}),
        ):
            self.assertEqual(self.api.post(f"/api/{path}/", payload, format="json").status_code, 403)
            self.assertEqual(self.api.patch(f"/api/{path}/{instance.pk}/", {"is_active": False}, format="json").status_code, 403)
            self.assertEqual(self.api.delete(f"/api/{path}/{instance.pk}/").status_code, 403)
        self.start.refresh_from_db()
        self.transition.refresh_from_db()
        self.assertTrue(self.start.is_active)
        self.assertTrue(self.transition.is_active)

    def test_foreign_objects_are_hidden_and_business_cannot_be_reassigned(self):
        foreign_transition = StageTransition.objects.create(business=self.foreign_business, pipeline=self.foreign,
                                                            from_stage=self.foreign_stage, to_stage=self.foreign_stage)
        for path, instance in (("pipeline-stages", self.foreign_stage), ("stage-transitions", foreign_transition)):
            self.assertEqual(self.api.get(f"/api/{path}/{instance.pk}/").status_code, 404)
            self.assertEqual(self.api.patch(f"/api/{path}/{instance.pk}/", {"is_active": False}, format="json").status_code, 404)
        BusinessMember.objects.create(business=self.foreign_business, user=self.owner, role="admin")
        response = self.api.patch(f"/api/stage-transitions/{self.transition.pk}/", {
            "business": self.foreign_business.pk, "pipeline": self.foreign.pk,
            "from_stage": self.foreign_stage.pk, "to_stage": self.foreign_stage.pk,
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.transition.refresh_from_db()
        self.assertEqual(self.transition.business_id, self.business.pk)

    def test_missing_null_and_unknown_links_have_controlled_validation_errors(self):
        for field in ("pipeline", "from_stage", "to_stage"):
            for value in (None, 99999999):
                response = self.api.patch(f"/api/stage-transitions/{self.transition.pk}/", {field: value}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.api.post("/api/pipeline-stages/", {"name": "Missing"}, format="json").status_code, 400)
        self.assertEqual(self.api.post("/api/stage-transitions/", {}, format="json").status_code, 400)
