# C04 / ARCHIVE-SENSITIVE-ARTIFACTS

Owner explicitly starts C04; no C05, push/merge/deploy, actual checkout archive or
private file inspection. Canonical PlatformaCRM, codex/ui-testing-toolkit,
base6a0dab4cce85b839c0a2a4a44c0f87a98c10c306;233 foreign WIP entries preserved.
Archive shell helper clean at start. Reuse actual rsync selection and existing zani/
archive layout. Baseline helper hash matches retained synthetic audit reproduction:
6fd264bbfce5f7042125e11982389bdeefc66629c5ee5e6fed6d93ee8476ff21.
Installed WSL rsync/python3, no zip. Replace zip executable with real Python standard
ZIP tool (supported dependency, not test shim); keep Bash entrypoint. Add explicit
runtime/private path exclusions, skip symlinks, validate output basename before writes,
build before replacing prior archive; pin this helper to LF for direct WSL execution.
Risk: excluding intended source; positive exact manifest + bytes/CRC, negatives nested
env/DB/browser/session/output, symlink outside fixture, filename rejection and failed
compression preserving prior archive. Run actual script in synthetic temp roots only;
no ordinary DB/backend/UI/build/install needed for packaging-only change. Complete with
shell syntax, repeatable actual archive tests, diff/links/docs/local commit. Dev stays off.
No permission/data/schema/notification/BusinessEvent/AI behavior changes.
