from datetime import datetime, timezone
from decimal import Decimal
from ipaddress import ip_address
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import local_postgres as pg
from scripts.cleanup_local_tokens import check_local_database
from scripts.sqlite_to_postgres import canonical, convert, digest


class LocalPostgresTests(unittest.TestCase):
    def setUp(self):
        self.identity = {"database": "platformacrm", "user": "crm_app", "port": 55432, "bin": "C:/PostgreSQL/bin"}
        self.database = dict(ENGINE="django.db.backends.postgresql", HOST="127.0.0.1", PORT="55432", NAME="platformacrm", USER="crm_app")

    def test_profile_guards_host_database_user_port(self):
        with patch.object(pg, "profile", return_value=self.identity):
            pg.validate_database(self.database)
            for key, value in [("HOST", "remote.example"), ("PORT", "5432"), ("NAME", "postgres"), ("USER", "postgres")]:
                with self.subTest(key=key), self.assertRaises(RuntimeError):
                    pg.validate_database({**self.database, key: value})

    def test_cleanup_accepts_only_pinned_local_postgres(self):
        with patch.object(pg, "profile", return_value=self.identity):
            check_local_database(self.database, "development")
            with self.assertRaises(RuntimeError):
                check_local_database(self.database, "production")

    def test_missing_data_does_not_initialize_or_start(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pg, "STATE", Path(folder)), \
                patch.object(pg, "profile", return_value=self.identity), patch.object(pg.subprocess, "run") as run:
            with self.assertRaises(RuntimeError):
                pg.ensure_running(self.database)
            run.assert_not_called()

    def test_profile_rejects_unexpected_identity(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pg, "STATE", Path(folder)):
            (Path(folder) / "identity.json").write_text(json.dumps({**self.identity, "database": "other"}))
            with self.assertRaises(RuntimeError):
                pg.profile()

    def test_transfer_normalizes_types_without_losing_values(self):
        self.assertEqual(canonical("2026-11-06 12:00:00", "timestamptz", None),
                         canonical(datetime(2026, 11, 6, 12, tzinfo=timezone.utc), "timestamptz", None))
        self.assertEqual(canonical(12.5, "numeric", 2), canonical(Decimal("12.50"), "numeric", 2))
        self.assertEqual(canonical('{"b":1,"a":"text"}', "jsonb", None), {"a": "text", "b": 1})
        self.assertEqual(canonical("127.0.0.1", "inet", None), canonical(ip_address("127.0.0.1"), "inet", None))
        self.assertFalse(convert(0, "bool"))
        self.assertIsNone(convert(None, "bool"))
        with self.assertRaises(ValueError):
            convert(2, "bool")

    def test_hash_detects_value_changes_even_with_same_count(self):
        fields = [("id", "int8", 0), ("amount", "numeric", 2)]
        self.assertNotEqual(digest([(1, 10)], fields), digest([(1, 11)], fields))


if __name__ == "__main__":
    unittest.main()
