from types import SimpleNamespace
from django.test import SimpleTestCase
from apps.accounts.serializers import system_role_key


class SystemRoleCopyTests(SimpleTestCase):
    def test_only_unchanged_system_presets_are_localizable(self):
        role = SimpleNamespace(is_system=True, name="Владелец", preset_key="owner")
        self.assertEqual(system_role_key(role), "owner")
        role.name = "Our owner"
        self.assertEqual(system_role_key(role), "")
        role.name, role.is_system = "Владелец", False
        self.assertEqual(system_role_key(role), "")
        self.assertEqual(system_role_key(None), "")
