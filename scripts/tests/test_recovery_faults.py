import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from scripts.recovery_faults import failure_boundary


class RecoveryFaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original = Mock(return_value="effect")
        self.wait = Mock()
        self.execute = failure_boundary(self.original, self.directory, self.wait)
        self.action = SimpleNamespace(pk=7, config={"title": "Valid task"})

    def target(self, kind):
        (self.directory / "fault-actions.json").write_text(json.dumps({kind: 7}), encoding="utf-8")

    def test_ordinary_action_passes_through_without_mutating_config(self):
        self.assertEqual(self.execute(self.action, business="synthetic"), "effect")
        self.original.assert_called_once_with(self.action, business="synthetic")
        self.wait.assert_not_called()
        self.assertEqual(self.action.config, {"title": "Valid task"})

    def test_crash_holds_after_effect_and_release_bypasses_hold(self):
        self.target("crash")
        self.wait.side_effect = lambda *a, **k: self.original.assert_called_once()
        self.execute(self.action)
        self.assertTrue((self.directory / "held").exists())
        self.wait.assert_called_once()
        (self.directory / "release").touch()
        self.execute(self.action)
        self.assertEqual(self.wait.call_count, 1)

    def test_transient_fault_prevents_effect_then_retries_unchanged_action(self):
        self.target("transient")
        with self.assertRaisesRegex(RuntimeError, "Synthetic S04"):
            self.execute(self.action)
        self.original.assert_not_called()
        self.assertTrue((self.directory / "transient-raised").exists())
        (self.directory / "retry-release").touch()
        self.assertEqual(self.execute(self.action), "effect")
        self.original.assert_called_once()

    def test_non_target_action_is_not_interrupted(self):
        self.target("transient")
        self.assertEqual(self.execute(SimpleNamespace(pk=8)), "effect")


if __name__ == "__main__":
    unittest.main()
