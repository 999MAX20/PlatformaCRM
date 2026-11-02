#!/usr/bin/env python3
"""One isolated CI-only Android JVM compile/unit attempt; never an APK/device run."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

GRADLE_VERSION = "8.11.1"
GRADLE_SHA256 = "f397b287023acdba1e9f6fc5ea72d22dd63669d59ed4a289a29b1a76eee151c6"
CAP = RESERVE = 2147483648
TOTAL_SECONDS = 1020
GRADLE_SECONDS = 900
PROJECTED_NEW_BYTES = 1932735283  # 1.8 GiB estimate, not a measured maximum.


class Blocked(Exception):
    pass


def junit_summary(paths):
    result = dict(files=0, tests=0, failures=0, errors=0, skipped=0)
    for path in paths:
        root = ET.parse(path).getroot()
        if root.tag != "testsuite":
            raise ValueError("Unexpected JUnit report root")
        result["files"] += 1
        for key in ("tests", "failures", "errors", "skipped"):
            result[key] += int(root.get(key, "0"))
    result["status"] = ("PASS" if result["tests"] > 0 and not any(
        result[key] for key in ("failures", "errors", "skipped")) else "FAIL")
    return result


class Packet:
    def __init__(self, repo, output):
        self.start = time.monotonic()
        self.deadline = self.start + TOTAL_SECONDS
        self.repo, self.output = repo, output
        self.project = repo / "mobile/android"
        self.roots = [output, self.project / ".gradle", self.project / "build", self.project / "app/build"]
        self.storage_baseline = None
        self.charged_high_water = 0
        self.report = {"status": "NOT_RUN", "sourceSha": os.environ.get("GITHUB_SHA"),
                       "limits": {"jobSeconds": 1200, "packetSeconds": TOTAL_SECONDS,
                                  "gradleSeconds": GRADLE_SECONDS, "lanes": 1,
                                  "artifactCapBytes": CAP, "freeReserveBytes": RESERVE,
                                  "projectedNewBytes": PROJECTED_NEW_BYTES,
                                  "estimateIsNotMeasuredMaximum": True},
                       "scope": "Debug main/unit compilation and fixture JVM tests only; no APK/device/live acceptance",
                       "phases": [], "junit": {"status": "NOT_RUN"}}

    def emit(self, event, **fields):
        print(json.dumps({"event": event, "elapsedSeconds": round(time.monotonic()-self.start, 3), **fields}), flush=True)

    def capacity(self):
        sample_deadline = min(self.deadline, time.monotonic()+10)

        def check_budget(measured=None):
            free = shutil.disk_usage(self.output).free
            delta_charge = 0 if self.storage_baseline is None else (
                self.storage_baseline[0]+max(0, self.storage_baseline[1]-free))
            self.charged_high_water = max(self.charged_high_water, delta_charge,
                                          measured if measured is not None else 0)
            if free < RESERVE or self.charged_high_water > CAP:
                raise Blocked("Artifact cap or free-space reserve reached")
            if time.monotonic() >= sample_deadline:
                raise Blocked("Resource sampling or packet deadline reached")
            return free

        # Gradle atomically moves transient cache entries. A failed traversal is
        # never an owned-size sample: remeasure only confirmed descendant ENOENT,
        # at most three reads inside the original ten-second measurement budget.
        for attempt in range(3):
            if not self.output.is_dir():
                raise Blocked("Required owned artifact root disappeared")
            check_budget()
            roots = [p for p in self.roots if p.exists()]
            try:
                sample = subprocess.run(["du", "-sk", *(str(p) for p in roots)], text=True,
                                        capture_output=True, timeout=sample_deadline-time.monotonic(),
                                        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"})
            except subprocess.TimeoutExpired as error:
                raise Blocked("Resource sampling exceeded its ten-second budget") from error
            check_budget()
            if sample.returncode != 0 or sample.stderr.strip():
                errors = sample.stderr.strip().splitlines()
                matches = [re.fullmatch(r"du: (?:cannot access '([^']+)'|(/.+)): No such file or directory", line)
                           for line in errors]
                transient = sample.returncode == 1 and bool(matches) and all(
                    match is not None and any(
                        Path(match[1] or match[2]) != root and
                        Path(match[1] or match[2]).is_relative_to(root) and root.is_dir()
                        for root in roots) for match in matches)
                if not transient:
                    raise Blocked("Resource measurement failed: "+sample.stderr.strip())
                self.emit("RESOURCE_REMEASURE", sample=attempt+1, reason="Owned transient descendant ENOENT")
                continue
            rows = [line.split("\t", 1) for line in sample.stdout.splitlines()]
            if len(rows) != len(roots) or any(
                len(row) != 2 or not row[0].isdigit() or row[1] != str(root)
                for row, root in zip(rows, roots)):
                raise Blocked("Incomplete or malformed resource measurement")
            owned = sum(int(row[0])*1024 for row in rows)
            free = check_budget(owned)
            if self.storage_baseline is None:
                self.storage_baseline = (owned, free)
            state = {"ownedBytes": owned, "chargedBytes": self.charged_high_water,
                     "freeBytes": free, "capHeadroomBytes": CAP-self.charged_high_water,
                     "reserveHeadroomBytes": free-RESERVE,
                     "measurementAttempts": attempt+1, "completeMeasurement": True}
            self.report["lastCapacity"] = state
            return state
        raise Blocked("No complete resource measurement after three bounded reads")

    def run(self, label, args, env, seconds):
        seconds = min(seconds, self.deadline-time.monotonic()-20)
        if seconds <= 0:
            raise Blocked("No remaining packet budget for " + label)
        self.capacity()
        entry = {"name": label, "status": "NOT_RUN", "limitSeconds": round(seconds, 3)}
        self.report["phases"].append(entry)
        self.emit("START", phase=label, limitSeconds=entry["limitSeconds"])
        started = time.monotonic()
        with (self.output / (label + ".log")).open("w") as log:
            process = subprocess.Popen(args, cwd=self.repo, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            try:
                while process.poll() is None:
                    self.capacity()
                    if time.monotonic()-started >= seconds:
                        raise Blocked(label + " wall-clock deadline reached")
                    time.sleep(3)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                entry["status"] = "BLOCKED"
                raise
        entry.update(status="PASS" if process.returncode == 0 else "FAIL", exitCode=process.returncode,
                     elapsedSeconds=round(time.monotonic()-started, 3))
        self.emit("END", **entry)
        return process.returncode

    def execute(self):
        if platform.system() != "Linux" or os.environ.get("GITHUB_ACTIONS") != "true":
            raise Blocked("CI-only stage: requires the authorized isolated Linux runner")
        if os.environ.get("GITHUB_REF") != "refs/heads/codex/mobile-max":
            raise Blocked("Only codex/mobile-max is authorized")
        if not re.fullmatch("[0-9a-f]{40}", self.report["sourceSha"] or ""):
            raise Blocked("Missing immutable source SHA")
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        if head != self.report["sourceSha"]:
            raise Blocked("Checkout SHA mismatch")
        clean = subprocess.check_output(["git", "status", "--porcelain"], cwd=self.repo, text=True)
        if clean:
            raise Blocked("Checkout is not clean before the diagnostic attempt")
        state = self.capacity()
        if state["ownedBytes"] + PROJECTED_NEW_BYTES > CAP or state["freeBytes"]-PROJECTED_NEW_BYTES < RESERVE:
            raise Blocked("Projected packet does not fit cap/reserve")
        sdk = Path(os.environ.get("ANDROID_HOME", "/nonexistent"))
        jdk = Path(os.environ.get("JAVA_HOME_17_X64", "/nonexistent"))
        required = [sdk/"platforms/android-35/android.jar", sdk/"build-tools/35.0.0/aapt2",
                    sdk/"licenses/android-sdk-license", jdk/"bin/java"]
        if not all(p.is_file() for p in required):
            raise Blocked("Preinstalled Java17/SDK35/build-tools35.0.0/accepted license missing; no installation attempted")
        inputs = {}
        for path in sorted((self.repo/"mobile").rglob("*")):
            if path.is_file() and ("android" in path.relative_to(self.repo/"mobile").parts[:1] or
                                   "contracts" in path.relative_to(self.repo/"mobile").parts[:1]):
                inputs[str(path.relative_to(self.repo))] = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.output/"inputs.json").write_text(json.dumps(inputs, indent=2)+"\n")
        self.report["inputHash"] = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        self.report["initialCapacity"] = state
        # Child build receives no GitHub tokens, provider secrets, real API origin, signing or account config.
        env = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR", "LANG") if k in os.environ}
        (self.output/"tmp").mkdir()
        env.update(JAVA_HOME=str(jdk), ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk),
                   GRADLE_USER_HOME=str(self.output/"gradle-user-home"),
                   ANDROID_USER_HOME=str(self.output/"android-user-home"),
                   XDG_CACHE_HOME=str(self.output/"cache"), TMPDIR=str(self.output/"tmp"),
                   JAVA_TOOL_OPTIONS="-Djava.io.tmpdir="+str(self.output/"tmp"), CI="true", LANG="C.UTF-8")
        if self.run("java-version", [str(jdk/"bin/java"), "-version"], env, 15):
            raise Blocked("Java version command failed")
        java = (self.output/"java-version.log").read_text()
        if not re.search(r'version "17\.', java):
            raise Blocked("Expected Java 17")
        self.report["javaVersion"] = java.strip()
        self.emit("PREFLIGHT_PASS", sha=head, inputs=len(inputs), **state)
        archive = self.output / ("gradle-"+GRADLE_VERSION+"-bin.zip")
        self.emit("START", phase="verified-gradle-download")
        download_start = time.monotonic()
        digest = hashlib.sha256()
        with urllib.request.urlopen("https://services.gradle.org/distributions/"+archive.name, timeout=30) as response, archive.open("xb") as dest:
            while chunk := response.read(1024*1024):
                dest.write(chunk); digest.update(chunk)
                if time.monotonic()-download_start > 120:
                    raise Blocked("Gradle download exceeded its 120 second budget")
                self.capacity()
        if digest.hexdigest() != GRADLE_SHA256:
            raise Blocked("Official Gradle archive SHA-256 mismatch; not extracted or executed")
        with zipfile.ZipFile(archive) as bundle:
            if sum(info.file_size for info in bundle.infolist()) > 300*1024*1024:
                raise Blocked("Unexpected Gradle expanded size")
            for info in bundle.infolist():
                target = (self.output/info.filename).resolve()
                if not target.is_relative_to(self.output) or (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise Blocked("Unsafe archive member")
                bundle.extract(info, self.output)
                self.capacity()
        self.report["gradleArchiveSha256"] = digest.hexdigest()
        self.emit("END", phase="verified-gradle-download", sha256=digest.hexdigest())
        gradle = ["/bin/bash", str(self.output/("gradle-"+GRADLE_VERSION)/"bin/gradle")]
        if self.run("gradle-version", gradle+["--version"], env, 30):
            raise Blocked("Gradle metadata preflight failed")
        if "Gradle "+GRADLE_VERSION not in (self.output/"gradle-version.log").read_text():
            raise Blocked("Gradle version mismatch")
        args = gradle+["--no-daemon", "--max-workers=1", "-Dorg.gradle.parallel=false",
                       "-Pkotlin.compiler.execution.strategy=in-process", "-Pandroid.builder.sdkDownload=false",
                       "--console=plain", "--stacktrace", "-p", "mobile/android", ":app:testDebugUnitTest"]
        self.report["command"] = args[2:]
        result = self.run("android-jvm", args, env, GRADLE_SECONDS)
        reports = sorted((self.project/"app/build/test-results/testDebugUnitTest").glob("TEST-*.xml"))
        self.report["junit"] = junit_summary(reports)
        log = (self.output/"android-jvm.log").read_text(errors="replace")
        self.report["taskLines"] = [line for line in log.splitlines() if line.startswith("> Task ")]
        self.capacity()
        self.report["status"] = "PASS" if result == 0 and self.report["junit"]["status"] == "PASS" else "FAIL"

    def main(self):
        self.output.mkdir(parents=True, exist_ok=False)
        try:
            self.execute()
        except Blocked as error:
            self.report.update(status="BLOCKED", reason=str(error))
        except Exception as error:
            self.report.update(status="FAIL", reason=type(error).__name__+": "+str(error))
        finally:
            self.report["elapsedSeconds"] = round(time.monotonic()-self.start, 3)
            (self.output/"report.json").write_text(json.dumps(self.report, indent=2)+"\n")
            self.emit("FINAL", status=self.report["status"], junit=self.report["junit"],
                      reason=self.report.get("reason"))
        return 0 if self.report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(Packet(Path.cwd().resolve(), Path(sys.argv[1]).resolve()).main())
