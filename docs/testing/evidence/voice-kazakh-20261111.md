# VOICE-KAZAKH-20261111

Owner requested synthetic Kazakh and mixed RU/KK speech verification: exact names,
phones and persisted CRM actions; fix failures and repeat. During this task the
owner explicitly approved reviewing new client names/phones before creation, then
approved reviewing new task titles/details. These supersede the corresponding
parts of the earlier direct-submission policy; other allowed actions remain direct.

Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`.
Original task base `e67116cd`; resumed own implementation began on `ffea10e9`.
Foreign source/docs changes are preserved. No working database, environment,
provider configuration, migrations or deployment changes.

## Findings and implementation

The original 12 ElevenLabs v3 synthetic recordings produced 7 exact end-to-end
passes and 5 failures: russified client names, an incorrect task title, a wrong
phone saved with a booking, and a duplicate client for a mixed-language conflict.
Scribe-v2 with explicit KK and independent Chirp did not consistently recover the
expected text. Re-synthesizing with KK language hints also retained errors. These
results do not establish whether every mismatch originated in TTS or STT.

- Labeled individual RU/KK/EN phone digits normalize exactly; number-label variants
  now include номер/номері. Unresolved spoken numbers cause clarification before
  field planning, with no writes or guessed digit aliases.
- Kazakh/Russian spelling candidates are permission-scoped and only prompt a choice.
  No automatic transliteration or name replacement. Execution rechecks ambiguity.
- New clients and tasks stop at `awaiting_confirmation`, even with `execution=direct`.
  New client + visit/plan is one reviewed, atomic operation. Server rejects an
  internal direct bypass. Existing-client operations retain their normal boundary.
- Preview shows name/phone or task fields. Editing preserves the request; submission
  replaces the old proposal. Cancel/revoked access/old fingerprints cannot create.
  Confirmation/replay uses the existing approval, domain transaction and audit.
- A malformed visit execution result rolls back before saving a recoverable failed
  state. Audit failures retain the original pending proposal and no domain writes.

No STT model/config replacement, arbitrary name repair, new permission framework,
new schema, notification, BusinessEvent or extra paid planning retry was introduced.

## Verification

Commands/scripts, hashes, WAVs, raw outcomes and retained failures are under
`output/voice-kazakh-20261111`. Existing `.venv` and isolated runtime use disposable
SQLite databases; no ordinary database is seeded or migrated. Offline checks deny
external network. Live runs send synthetic audio/data to the configured OpenRouter
gateway with existing ZDR/data-collection-deny policy. API keys remain in memory.

Independent synthesis uses Microsoft's documented KK voices Aigul/Daulet through
`edge-tts`, installed only into the ignored diagnostic output directory, plus ffmpeg
mono PCM16/16k conversion. Product dependencies and lock files are unchanged.
Sources: [voice support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support),
[synthesis client](https://github.com/rany2/edge-tts).

- `check.py focused ...tests_voice_kazakh ...tests_speech_numbers`: initial 7 PASS,
  1 recovery-fixture failure. The fixture said `noon` while its source said `12:00`;
  corrected the fixture, retained strict time evidence. `focused-corrected`: 8 PASS,
  system/migration drift PASS before dependent changes.
- Initial identity-review suite: 64 PASS/3 errors. One fixture expected 403 where
  a foreign conversation safely returns 404. Two tests exposed the changed explicit
  confirmation failure path; rollback/recoverable state fixed and rechecked.
  `review-recovery`: 11 PASS, system/drift PASS.
- `check.py completion`: 145 PASS across speech, voice identity/schedule/direct,
  locations/languages/interface and conversation execution/state/API; system/drift PASS.
  This predates the separately approved task-review extension.
- `check.py task-review`: 38 PASS for task direct/review, KK safeguards, interface
  and languages; system/drift PASS. Existing domain fixtures now simulate the explicit
  owner review before asserting execution; dedicated boundary tests assert zero
  writes beforehand, bypass denial, correction, cancellation and replay.
- First reviewed native corpus: 11/12 scenarios reached the expected outcome;
  4 needed simulated human correction. The remaining existing-client case proposed
  a new spelling and correctly waited for review, so the original automatic-action
  assertion failed. Original outcome remains recorded, not relabeled as a PASS.
- Browser run `1794413992281376400`: 4 PASS against real isolated API, fixture model:
  RU1440/KK320/EN390 review, visible phone, keyboard confirm/cancel, correction,
  sustained 503 with retained input, stale-proposal state and idempotent confirmation.
  KK320 screenshot inspected. App shell and existing components retained.
- Initial frontend audio tests, i18n, forced types, app/widget build and bundle PASS.
  Final affected build and remaining live/browser receipts are recorded at closure.

## Boundary and closure

Final verification complete on task source over `dc6687c8` (same changed source as
verified runs; documentation closure only afterward). PostgreSQL17:25 PASS,
including simultaneous confirmation and schedule concurrency; disposable cluster
stopped and database removed. Final real audio corpus:18/18 reviewed workflows
PASS,9 with simulated human correction (4/12 independent KK-voice recordings,
5/6 original regression recordings). No writes before review, exact persisted fields,
confirmation replay and original request replay checked. These are18 distinct
cases, not18 exact-recognition passes. Initial failures remain recorded.
Final browser task-correction scenario KK320 PASS (5 total distinct browser cases).
Final forced types/i18n/app-widget build/bundle PASS. All task runtimes stopped.
Own task-only commit; push blocked by37 pre-existing foreign outgoing commits;
no new CI or deployment. No scoped implementation/local-workflow evidence remainder.
README/capabilities/access/integration contracts need no change: no setup, new
capability, permission or provider change; voice/AI/roadmap/passport updated. Recognition accuracy and reviewed workflow
correctness are separate: a corrected-and-approved action is not an exact-STT pass.
Human speech, noise, production queue/runtime and full D01 are outside this synthetic
scope. No release acceptance is closed by these checks.
