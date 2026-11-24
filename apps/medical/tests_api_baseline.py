"""Local query-growth guard, not deployment latency or concurrency acceptance."""
import json
from math import ceil
from time import perf_counter

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from . import tests_clinical_workspace as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class ClinicalWorkspaceQueryGrowthTests(TestCase):
    setUpTestData = classmethod(fixtures.ClinicalWorkspaceAPITests.setUpTestData.__func__)
    setUp = fixtures.ClinicalWorkspaceAPITests.setUp
    append = fixtures.ClinicalWorkspaceAPITests.append
    extra_encounter = fixtures.ClinicalWorkspaceAPITests.extra_encounter
    read = fixtures.ClinicalWorkspaceAPITests.read

    def sample(self, history_size):
        self.assertEqual(self.read(limit=20).status_code, 200)
        timings, queries, sizes = [], [], []
        for _ in range(20):
            with CaptureQueriesContext(connection) as captured:
                started = perf_counter()
                response = self.read(limit=20)
                timings.append((perf_counter() - started) * 1000)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store, private")
            self.assertEqual(len(response.data["encounters"]), 20)
            self.assertIsNotNone(response.data["next_before_id"])
            self.assertNotIn("content", response.data["encounters"][0])
            queries.append(len(captured))
            sizes.append(len(response.content))
        return {"history_size": history_size, "samples": len(timings),
                "p95_ms": round(sorted(timings)[ceil(len(timings) * .95) - 1], 2),
                "max_ms": round(max(timings), 2), "queries_min": min(queries),
                "queries_max": max(queries), "payload_max_bytes": max(sizes)}

    def test_fixed_page_query_count_does_not_grow_with_total_history(self):
        for _ in range(24):
            self.extra_encounter()
        small = self.sample(25)
        for _ in range(75):
            self.extra_encounter()
        large = self.sample(100)
        print("MEDICAL_WORKSPACE_BASELINE " + json.dumps({
            "database": connection.vendor, "transport": "in-process APIClient",
            "authentication": "force_authenticate", "sql_capture": True,
            "concurrency": 1, "measurements": [small, large]}, sort_keys=True))
        self.assertEqual(small["queries_min"], small["queries_max"])
        self.assertEqual(large["queries_min"], large["queries_max"])
        self.assertEqual(large["queries_max"], small["queries_max"])
