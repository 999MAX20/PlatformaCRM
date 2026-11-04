import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "make_clean_archive.sh"


class CleanArchiveTests(unittest.TestCase):
    def setUp(self):
        for command in ("bash", "rsync", "python3"):
            if not shutil.which(command):
                raise RuntimeError(f"Run these packaging tests in Linux/WSL with {command} installed")
        self.temp = tempfile.TemporaryDirectory(prefix="crm-c04-archive-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source with spaces"
        self.root.mkdir()
        self.write("scripts/make_clean_archive.sh", SOURCE.read_bytes())
        self.write("README.md", b"Synthetic documentation\n")
        self.scratch = Path(self.temp.name) / "scratch"
        self.scratch.mkdir()
        self.env = {**os.environ, "TMPDIR": str(self.scratch)}

    def write(self, name, value=b"SYNTHETIC_PRIVATE_MARKER"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)

    def run_archive(self, name="fixture.zip", *, env=None):
        return subprocess.run(["bash", str(self.root / "scripts/make_clean_archive.sh"), name],
                              cwd=self.root, env=env or self.env, capture_output=True, text=True, timeout=30)

    def test_actual_zip_manifest_keeps_sources_and_excludes_nested_private_artifacts(self):
        allowed = {"README.md": b"Synthetic documentation\n", "scripts/make_clean_archive.sh": SOURCE.read_bytes(),
                   "apps/example.py": b"print('fixture')\n", "docs/notes with spaces.md": b"Synthetic docs\n",
                   "frontend/src/Пример.ts": "export const label = 'пример';\n".encode(),
                   ".env.example": b"PASSWORD=replace-me\n", "frontend/.env.production.example": b"URL=https://example.invalid\n",
                   "tools/.env.local.example": b"TOKEN=replace-me\n", "frontend/package-lock.json": b"{}\n"}
        for name, data in allowed.items():
            self.write(name, data)
        blocked = [".env", ".env.private", "db.sqlite3", "nested/.env", "nested/.env.production",
                   "nested/.ENV", "nested/issuer.ENV", "nested/backup.SQLite3", "nested/backup.DB",
                   "nested/issuer.env", "nested/issuer.env.old", "nested/pre-change.sqlite3", "nested/cache.db",
                   "nested/cache.db-wal", "nested/database.dump", "nested/backup/data.sql",
                   "output/account-security-backups/qr-issuer.env", "output/backup-before.sqlite3",
                   "output/browser/storage-state.json", "output/arbitrary-private.txt", ".playwright-cli/session.json",
                   "frontend/e2e/.auth/owner.json", "nested/storage-state.json", "nested/storage_state_owner.json",
                   "nested/storageState.json", "nested/owner.storage-state.json", "nested/session.json",
                   "nested/session-owner.json", "nested/cookies.json", "nested/profile.har",
                   "nested/browser-profile/Cookies", "nested/chrome-profile/Preferences", "nested/user-data-dir/Local State",
                   "nested/private_media/file.txt", "nested/backups/anything.txt", ".git/config",
                   ".venv/lib.py", "node_modules/package/index.js", "frontend/dist/app.js",
                   "nested/test-results/state.json", "nested/__pycache__/code.pyc", "nested/old.zip", "nested/error.log"]
        for name in blocked:
            self.write(name)
        result = self.run_archive("result with spaces.zip")
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.root / "result with spaces.zip") as archive:
            self.assertIsNone(archive.testzip())
            files = {item.filename: archive.read(item) for item in archive.infolist() if not item.is_dir()}
        self.assertEqual(files, {"zani/" + name: data for name, data in allowed.items()})
        print("ARCHIVE_MANIFEST " + json.dumps(sorted(files), ensure_ascii=True))
        self.assertNotIn(b"SYNTHETIC_PRIVATE_MARKER", b"".join(files.values()))
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_links_and_special_files_are_not_followed_or_archived(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_bytes(b"SYNTHETIC_OUTSIDE_MARKER")
        (self.root / "linked.txt").symlink_to(outside)
        (self.root / "linked-dir").symlink_to(outside.parent, target_is_directory=True)
        (self.root / "broken-link").symlink_to(self.root / "missing")
        os.mkfifo(self.root / "pipe")
        result = self.run_archive()
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(self.root / "fixture.zip") as archive:
            files = [item.filename for item in archive.infolist() if not item.is_dir()]
        self.assertEqual(set(files), {"zani/README.md", "zani/scripts/make_clean_archive.sh"})
        self.assertEqual(outside.read_bytes(), b"SYNTHETIC_OUTSIDE_MARKER")

    def test_bad_destination_refused_before_modifying_existing_files(self):
        for name in ("../outside.zip", "/tmp/outside.zip", "nested/name.zip", "nested\\name.zip", "README.md", ".hidden.zip", "-flag.zip"):
            with self.subTest(name=name):
                result = self.run_archive(name)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("Archive name must be a plain .zip filename", result.stderr)
        self.assertEqual((self.root / "README.md").read_bytes(), b"Synthetic documentation\n")
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_existing_destination_link_and_directory_are_rejected(self):
        outside = Path(self.temp.name) / "outside.zip"
        outside.write_bytes(b"KEEP_SYNTHETIC_OUTSIDE")
        (self.root / "link.zip").symlink_to(outside)
        (self.root / "directory.zip").mkdir()
        for name in ("link.zip", "directory.zip"):
            result = self.run_archive(name)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Archive destination must not be a symlink or directory", result.stderr)
        self.assertEqual(outside.read_bytes(), b"KEEP_SYNTHETIC_OUTSIDE")

    def test_failed_compression_retains_previous_archive_and_cleans_temp(self):
        self.write("fixture.zip", b"PREVIOUS_SYNTHETIC_ARCHIVE")
        bin_dir = Path(self.temp.name) / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "python3"
        fake.write_text("#!/bin/sh\nexit 17\n")
        fake.chmod(0o755)
        result = self.run_archive(env={**self.env, "PATH": str(bin_dir) + os.pathsep + self.env["PATH"]})
        self.assertEqual(result.returncode, 17)
        self.assertEqual((self.root / "fixture.zip").read_bytes(), b"PREVIOUS_SYNTHETIC_ARCHIVE")
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_repeated_build_has_no_previous_archive_inside(self):
        for _ in range(2):
            result = self.run_archive()
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(self.root / "fixture.zip") as archive:
                self.assertIsNone(archive.testzip())
                self.assertFalse(any(name.endswith(".zip") for name in archive.namelist()))

    def test_helper_has_lf_and_valid_shell_syntax(self):
        self.assertNotIn(b"\r", SOURCE.read_bytes())
        subprocess.run(["bash", "-n", str(SOURCE)], check=True)


if __name__ == "__main__":
    unittest.main()
