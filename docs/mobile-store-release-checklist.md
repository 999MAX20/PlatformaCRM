# Native Mobile Release Checklist

Updated: 2026-10-29. Runtime: Swift/SwiftUI iOS + Kotlin/Jetpack Compose Android.
This is an acceptance checklist, not evidence that builds or release gates passed.
Owner currently requests local implementation; commit/push/remote CI/deploy/store
publication are deferred. Keep environment credentials separate and out of artifacts.

## Current evidence boundary

- Latest source84 Android Debug: one guarded offline assembleDebug PASS (830s).
  Separate APK SHA256 `977863a06e9b7a2b4067cee2072c1e6437ad815dcffb9090f76ff87307f230be`,
  9866966 bytes, package kz.zani.mobile, version0.1.0/build1, SDK26/35, debuggable.
  Actual DEX/read-flow, current56 fixture files/86 locale keys, ZIP CRC and existing
  debug-certificate equality verified. No installation or device/live acceptance.
  Fresh unsigned Release NOT_RUN: required existing Gradle native-console cache
  files are dataless again. No retry/download/cache deletion or policy change;
  previous APKs/receipts remain preserved as prior-source evidence. Shared synthetic
  Release assets/API-not-configured remain an existing limitation, not a live client.
  Full receipt: native-build/android-current-artifacts in the task checkpoint.
- The following foundation/early continuation results are historical prior-source
  evidence; they do not replace the current packet above.
- PASS locally: 71 Swift native core checks, actual SwiftUI ViewModel host macOS
  typecheck and 11 headless checks; shared payload/copy checks and SwiftUI syntax.
  Actual Android Gradle unit tests (24, including four ViewModel regressions) and
  debug assemble passed. The APK's package/version/SDK, debuggable flag, selected
  fixture/copy assets and ZIP integrity were checked without installing it.
  Unsigned Android Release assembly and lintVitalRelease also passed. DEBUG=false,
  no debuggable flag, and compiled MainActivity's API-not-configured branch were
  checked; it has no FixtureTransport reference. Shared synthetic assets are still
  packaged from main assets, and no live release configuration is accepted.
  Existing unchanged project plist/XML and local CI structure evidence is retained.
- PASS locally: Xcode 27.1 / build 27A9275 compiled Debug and Release for the generic
  iOS Simulator destination (arm64 and x86_64), without developer signing or launch.
  Bundle ID/version/deployment floor and copied contracts were verified. Compiled
  Release App body constructs API-not-configured text with DEBUG absent. Unused
  fixture helper symbols and shared synthetic assets remain packaged; this is not
  a live-configured store candidate. Linker-generated ad-hoc Mach-O signatures have
  no developer identity, team or provisioning profile.
- Latest offline continuation: 25 Android unit tests and current Debug APK assembly
  passed with cached dependencies/offline mode. SwiftUI startup coalescing reproduced
  a failure before its guard fix; 16 host ViewModel checks and a current arm64 generic
  iOS Simulator Debug build now pass. Android Back and status semantics bindings were
  inspected. Earlier universal/Release builds remain prior-source evidence, not new
  Release verification. Device gestures/reader and live acceptance are still separate.
- NOT_RUN: device/visual/reader,
  real API/provider/push/load, remote CI and store verification.
- Live integration is not configured; debug compositions explicitly identify synthetic
  fixtures. Release compositions report API-not-configured. Fixtures are never a
  fallback after a real API error.
- Local iOS prerequisite resolved: matching Xcode 27.1 and iOS SDK 27.1 were installed
  after exact Apple agreement consent, archive/app integrity and full disk-budget
  verification. First-launch status passed; global developer selection is unchanged.
  JDK17, Gradle8.11.1, Android SDK35 rev.2/build-tools35.0.0 and CLI19.0 are installed;
  the owner explicitly accepted the exact Android SDK license before installation.
  Recheck complete disk peak/reserve before further installations or builds.

## Native candidate configuration

- iOS source: `mobile/ios/PlatformaCRM.xcodeproj`, scheme `PlatformaCRM`.
- Android source: `mobile/android`, app module `app`.
- Existing identifiers remain `kz.zani.mobile` on both platforms.
- iOS marketing version/build and Android versionName/versionCode are explicit.
  Initial 0.1.0/build1 are compilation inputs, not an accepted store allocation.
  Verify actual prior store build history and allocate appropriate numbers before upload.
- Deployment floors (iOS17/Android26) are initial build settings, not a completed
  supported-device matrix. Confirm target devices before pilot acceptance.
- Accepted backend SHA, API version/read projections, role/object/field/branch access,
  null semantics and staging/production origin isolation are required before live binding.
  Historical RN URLs/EAS profile names are not a native environment contract.
- Version/update policy, signing identities, store ownership and recovery roles must be
  explicitly configured and evidenced. No keys/accounts/entitlements are inferred.
- Review debug fixture resources/mode and ensure the release candidate has approved
  real configuration. Shared RU/KK/EN first-slice labels have key parity; six new
  system-status translations and full device/reader/layout review remain open.

## Local automated commands

From the repository root, without API credentials or server/provider calls:

```bash
python3 mobile/scripts/check_contracts.py
bash mobile/scripts/check_swift_core.sh
swiftc -frontend -parse mobile/ios/CRMApp/*.swift
plutil -lint mobile/ios/PlatformaCRM.xcodeproj/project.pbxproj
git diff --check
```

The Swift script compiles/runs pure core checks on the macOS host; it is not an
app build or a simulator launch. The SwiftPM entry point also passed 71 checks under
the provisioned Xcode 27.1 toolchain; the earlier installed-CLT PackageDescription
linker failure no longer reproduces with this matching toolchain. The actual
SwiftUI ViewModel passed all 11 headless host checks under Xcode as well.

With already provisioned matching toolchains (build only, no device launch):

```bash
xcodebuild -project mobile/ios/PlatformaCRM.xcodeproj -scheme PlatformaCRM \
  -sdk iphonesimulator -configuration Debug \
  -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
gradle -p mobile/android --no-daemon :app:testDebugUnitTest :app:assembleDebug
```

Native CI definitions are in `.github/workflows/mobile-native.yml`, reused by the
root workflow. Workflow presence/local YAML validation is not remote CI PASS.
The existing mobile branch can run only native checks when publishing is separately
permitted. Backend/frontend jobs and shared server configuration are preserved.
The archived RN `npm run release:gate`, Expo/EAS and smoke scripts are historical
artifacts; they are not commands for this native source tree.

Backend checks remain the server owner's scoped acceptance under `docs/testing.md`.
Do not run excluded auth/reset work or provider/live-target tests from this checklist.

## Physical and integration gates

- iOS and Android installed candidate: Business/branch/role scope, denied/redacted data,
  single Appointment identity in list/calendar/details, retry and context-switch recovery.
- Current/previous client compatibility, timestamp/business-timezone and null/version
  semantics, partial result disclosure, and unknown outcome handling are evidenced.
- Existing installed RN credentials/cache/pending commands have an accepted migration,
  retention and ownership policy before any same-identifier update. No silent data
  clearing or blind replay is permitted; old source backup is not device-data recovery.
- Push provider/native token registration, real delivery/open/revoke in required app
  lifecycle states are independently proven. Registration alone is not delivery;
  retained backend Expo settings do not prove native APNS/FCM readiness.
- Deep-link/app/universal-link association and authorization are proven on target devices;
  historical schemes/hostnames do not configure the new apps automatically.
- Existing backend mobile version/rate-limit/worker/push/observability settings must match
  the accepted environment; no server setting is changed by this mobile checklist.
- App Store/TestFlight and Google Play ownership/signing/privacy/reviewer access, upload,
  review and publication are separate explicit gates. No upload/deploy is implied.

A candidate is not release-ready while required evidence is missing or skipped.
