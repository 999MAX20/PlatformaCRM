from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_core.history import operational_period
from apps.ai_core import tests_conversation_memory as fixtures
from apps.businesses.models import BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.tasks.models import Task


class HistoricalStatusScopeTests(TestCase):
    def setUp(self):
        fixtures.ConversationMemoryTests.setUp(self)
        self.actor = User.objects.create_user(username="history-own", email="history-own@example.com")
        self.role = BusinessRole.objects.create(business=self.business, name="Own history")
        RolePermission.objects.create(business_role=self.role, resource="tasks", action="view", scope="own", is_allowed=True)
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="manager", business_role=self.role)

    def test_status_groups_count_each_visible_record_once_despite_watchers_and_ordering(self):
        statuses = ["open"] * 6 + ["in_progress"] * 3 + ["done"] * 4
        for index, status in enumerate(statuses):
            task = Task.objects.create(business=self.business, title=f"Task {index}", status=status,
                assignee=self.actor if index % 2 else self.owner, created_by=self.owner,
                due_at=timezone.now() + timedelta(hours=index), is_archived=index % 3 == 0)
            task.watchers.add(self.actor, self.owner)
        Task.objects.create(business=self.business, title="Hidden", assignee=self.owner, created_by=self.owner)
        Task.objects.create(business=self.other_business, title="Foreign", assignee=self.actor)
        result = operational_period(self.business, self.actor, date(2000, 1, 1), date(2099, 1, 1), ["tasks"])["tasks"]
        self.assertEqual(result["count"], 13)
        self.assertEqual(result["current_statuses"], {"open": 6, "in_progress": 3, "done": 4})
        self.assertEqual(sum(result["current_statuses"].values()), result["count"])

    def test_team_scope_deduplicates_overlapping_assignment_and_watchers(self):
        teammate = User.objects.create_user(username="history-teammate", email="history-teammate@example.com")
        member = BusinessMember.objects.create(business=self.business, user=teammate, role="manager")
        team = Team.objects.create(business=self.business, name="Analysts")
        TeamMember.objects.create(team=team, member=self.member)
        TeamMember.objects.create(team=team, member=member)
        RolePermission.objects.filter(business_role=self.role, resource="tasks").update(scope="team")
        for index in range(3):
            task = Task.objects.create(business=self.business, title=f"Team {index}", assignee=teammate,
                status="done", due_at=timezone.now() + timedelta(hours=index), is_archived=index == 0)
            task.watchers.add(self.actor, teammate)
        Task.objects.create(business=self.business, title="Outside team", assignee=self.owner, created_by=self.owner)
        result = operational_period(self.business, self.actor, date(2000, 1, 1), date(2099, 1, 1), ["tasks"])["tasks"]
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["current_statuses"], {"done": 3})
