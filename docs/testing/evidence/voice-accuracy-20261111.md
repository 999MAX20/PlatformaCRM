# VOICE-ACCURACY-20261111

Status: **partial; continuation finished with exact accuracy acceptance FAIL**.
Latest12November: phone-before-date parser fixed; single-recognizer API10/12PASS,
2provider timeouts, all3 conflict-number checks exact. No majority correction.
Targeted timeout investigation repeated only those2 failures; now both blocked by
HTTP402 minimum audio balance, so their live acceptance remains open (details below).
Owner requested a continuation of VOICE-KAZAKH: analyze all9 manually corrected
Kazakh/mixed RU/KK samples, eliminate causes and repeat verification without manual
correction. Original task base2b732fe4, canonical PlatformaCRM, branch
`codex/ui-testing-toolkit`. Concurrent business/analytics changes were preserved;
continuation source is over `286c9cf6` (shared checkout). No workingDB, .env, migrations, deployment or external
CRM communication changes. There is no task commit/push: the required exact gate
failed. Foreign outgoing history is an additional publication boundary, not the
reason to call an inaccurate candidate complete.

## Owner-requested continuation after the partial report

The owner explicitly requested further work on names/repeated digits and another
no-correction verification. Resume base `f01d2d8b`, same canonical checkout/branch.
Additional bounded probes compared specialized STT and multimodal models,
tempo0.8/1.15, disjoint audio segments, duplicate original/slowed views and higher
reasoning. Tempo0.8 initially fixed the booking name but repeated verification
returned the wrong name again. Segmentation corrupted names/dates; additional
models were unavailable under unchanged privacy or inaccurate. These failures
remain in `resume-probe`, `tempo-full`, `omni-probe`, `segment-probe`,
`reasoned-probe` and `multiview-probe` JSON receipts under the existing output folder.

The new candidate uses the original WAV, a static Kazakh instruction and medium
reasoning,4096 output tokens. It has no expected names, phones, CRM context,
audio preprocessing, correction pass or retry. Six selected speech probes passed;
focused20/system/drift PASS. The frozen31-case API run includes the original18,
prior7 controls and6 fresh controls, including distinct Әбілев/Әбілов surnames.
The frozen API run finished **28/31 PASS,3FAIL**: reserved model tokens on one
case and two provider timeouts. A subsequent12-case run finished **9/12 PASS,3FAIL**:
timeout, an em-dash phone-label parsing gap, and one added phone digit. The original9
were8/9 in that run; this does not establish stable9/9 acceptance. Separate10/12-digit
controls both became11 digits. Strict rejection of model control tokens is now
implemented and tested; the label parser now accepts typographic separators while
preserving every dictated digit. These fixes do not solve provider accuracy.
Default remains Scribe; no workingDB/.env/deployment change.

The owner explicitly retained **OpenRouter only**. All continuation calls preserve
ZDR/data_collection=deny; no direct ElevenLabs account or relaxed privacy route was
used. Unavailable Scribe v3 and GPT Transcribe endpoints were not treated as usable
providers. Native/Flash/Pro, cropped numeric audio and repeated-digit probes remain
in the output receipts, including every timeout and inaccurate result.

A numeric-consensus feasibility probe used a primary Carbon transcript, independent
Scribe transcription and, on disagreement, Flash decoding of a timestamped numeric
audio segment. It initially passed21/22; correcting generic segment boundaries
passed22/22 using cached primary/Scribe observations. This was not fresh acceptance.
The fresh run then disproved automatic majority correction: on `kk-conflict-native`,
Carbon correctly returned77022222222, while Scribe and the cropped Flash decode both
returned770222222222. Majority voting would corrupt the correct number. Therefore
consensus/cropping is **not implemented in product code**, regardless of aggregate
success rates. Another fresh case timed out. Receipts: `consensus-probe.json`,
`consensus-boundary-recheck.json`, `fresh-consensus.json`; scripts contain no expected
answers in provider prompts. The initial fresh harness had a Django settings/thread
initialization error; its log is retained separately from the corrected run.

Fresh feasibility completed **29/33 PASS,4FAIL**, original9 **8/9**. Failures are
the booking timeout, the majority-added digit, and two mixed conflict transcripts
whose phone spans were not resolved unambiguously. All32 completed primary
responses retained the expected name/title substrings; that lexical check is not
an end-to-end CRM field or morphology certificate. No cached transcripts or manual
corrections were used in this run. Maximum elapsed time56.14s; reported successful
request cost about$0.17852 (does not claim billing for timed-out requests). Full
receipts and source hashes: `continuation-result.json`. No majority candidate was
integrated, so no end-to-end acceptance was claimed for it.

Final affected suites: **115PASS,1PostgreSQL skip**, system check and migration
drift PASS in isolated runtime (`continuation-dependent-0/1/2.log`). Exact command:
`.venv/Scripts/python.exe output/voice-accuracy-20261111/check.py continuation-dependent
apps.ai_core.tests_speech_audio apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers
apps.ai_core.tests_speech_formatting apps.ai_core.tests_voice_kazakh
apps.ai_core.tests_voice_direct apps.ai_core.tests_voice_schedule
apps.ai_core.tests_voice_identity apps.ai_core.tests_voice_interface
apps.ai_core.tests_voice_policy`. PostgreSQL-only concurrency was not repeated for
this recognition/parser change. No frontend build/full-project/browser gate: capture,
UI and endpoint schema are unchanged. Live recognition scripts exited; isolated
runtime removed its database. No owned server or ongoing provider request remains.
No own commit/push/new CI: the required exact recognition gate remains failed.
Further work needs a materially different, evidenced recognition approach; repeated
calls with the rejected profiles cannot justify promotion. OpenRouter-only and
privacy constraints remain in force. Human recordings and production are untested.

The following original comparison and low-profile results remain historical
evidence for the first attempt, not certification of the new candidate.

## Findings and nine-case comparison

### Owner-requested date-boundary fix, 12 November

The owner requested fixing phone extraction before a date, excluding majority
correction, and repeating OpenRouter tests without manual edits. The product
adapter already made exactly one recognition call; consensus/cropping existed
only in diagnostic scripts. Those historical scripts/receipts remain evidence,
and are not used by the new `exact-date-single` API run.

The parser now recognizes an explicit date after comma/semicolon: day+RU/KK/EN
month name or day.month.year. It preserves the date and every dictated phone digit.
Arbitrary numeric continuations, incomplete/grouped dictation and6/16 digit word
sequences remain unchanged. This is a boundary detector, not calendar validation.
Focused RED reproduced4 date cases; GREEN6 tests/system/drift PASS. Replaying the
two previously failed primary transcripts now yields exactly77022222222 and the
unchanged date/time (`date-recorded-regression.json`). No name/number hints or
expected outputs are sent to the provider. Default Scribe/settings/privacy unchanged.

Fresh single-Carbon OpenRouter API run finished **10/12 PASS,2FAIL** (original9:
7PASS,2timeouts). All3 conflict cases have the exact77022222222 transcript, clarify
the identity conflict and write nothing. The other successful cases prove exact
proposed/persisted names, numbers or task title, confirmation and replay without
manual correction. `mixed-digits-original` and `mixed-booking-original` returned
provider_unavailable after60.859s/61.797s before any transcript; protected counts
remained1client/0appointments/0tasks. No corrective extra recognizer or automatic
retry was called. Failed receipts remain; overall live gate intentionally exits1.

Exact invocation: `exact_live.py --round=date-single --model=google/gemini-4-carbon`
with samples kk-client-auto-native,mixed-client-native,kk-booking-native,
mixed-booking-native,kk-repeated-original,mixed-client-original,mixed-digits-original,
mixed-task-original,mixed-booking-original,kk-conflict-native,mixed-conflict-native,
mixed-conflict-original (each passed using `--sample=`). Isolated runtime/synthetic
fixtures; real provider, no workingDB. `date-source.json` hashes unchanged throughout.
`date-result.json` summarizes the full receipts in `exact-date-single-result.json`.
Affected suite `check.py date-dependent` used the same10 test modules listed above:
**117PASS,1PGskip**, system/drift PASS. No UI/build/full-project gate for this parser
delta. Both owned processes exited; test databases cleaned by isolated_runtime.
Date parser scope is fixed; broader provider reliability/exact acceptance remains
open. No owncommit/push/newCI because the live required gate is not fully passing.

## Targeted timeout investigation, 12 November

Owner explicitly requested only the two failed scenarios, no successful reruns.
No product source/config/env changes were made. `timeout_live.py --round=timeout-only
--model=google/gemini-4-carbon --sample=mixed-digits-original
--sample=mixed-booking-original` reused the isolated API/CRM harness, original WAVs,
same medium4096 profile,60s urllib timeout and privacy restrictions. Temporary
harness-only instrumentation measured HTTPS connection/headers/body; no tokens or
authorization headers were logged. Previously passed suites/cases were not rerun.

Historical failures were generated before transcript/CRM planning at60.859/61.797s.
The adapter catches OSError/JSON errors and discards exception type, returning
provider_unavailable. No HTTP-error warning or generation ID was saved for those
two calls. Timing strongly suggests the60s network wait, but does not prove the
precise old failure phase or a Google/OpenRouter queue/processing root cause.
The frontend speech timeout is65s; these tests used Django APIClient directly,
so a browser timeout did not cause the observed failures. No timeout increase or
automatic paid retry was introduced.

The targeted rerun completed0/2: **both HTTP402**, unlike the original timeouts.
TLS connections completed in0.610/0.219s, requests were rejected in1.968/1.610s;
no transcript or CRM write occurred. A single additional diagnostic of the same
failed mixed-digits audio captured the exact provider error: “This request requires
at least $0.50 in balance for audio”. Read-only account checks showed remaining
balance about$0.26 and no per-key spending limit. No balance, limit, key or account
setting was changed. This is the current blocker, not a retrospective explanation
of the earlier timeout. Further identical audio calls were stopped.

Receipts: `timeout-trace.json`, `exact-timeout-only-result.json`,
`timeout-rejection.json`; account details remain in ignored local output only.
The [official generation metadata endpoint](https://openrouter.ai/docs/api/api-reference/generations/get-generation)
requires a generation ID, unavailable for the historical failures; no speculative
account-wide history access was attempted. The [current-key endpoint](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key)
was used read-only to distinguish a key limit from account balance.
All owned test processes exited and disposable runtime cleaned up. No successful
application tests/builds were repeated; docs hygiene/source-hash checks only.
Remaining: restore sufficient audio balance, then rerun exactly these2 scenarios
with timing instrumentation. Do not rerun passed cases or claim original timeout
root cause/recognition acceptance proven. No product change/owncommit/push/newCI.

## Historical initial nine-case comparison

All9 original mismatches were already present in STT output, before field planning.
The local digit-word conversion preserves every recognized digit; it cannot recover
words/digits omitted or substituted by the provider. The audio bytes were reused,
not replaced by easier recordings. Expected names/phones/titles were never supplied
to the recognition prompt, and no name alias or corpus-specific correction was added.
The syntheses and independent recognizers disagree on some pronunciations; the data
do not establish that every original mismatch was caused exclusively by STT rather
than TTS pronunciation. There are no human reference recordings in this task.

| Sample | Original mismatch | Frozen candidate, both API rounds |
| --- | --- | --- |
| kk-client-auto-native | Алихан instead of Әлихан; omitted phone zero | PASS: exact Әлихан Омаров and77010002030 |
| mixed-client-native | Асель Касымова instead of Әсел Қасымова | PASS: exact Kazakh spelling/phone |
| kk-booking-native | Нұрланована, specialist spelling | FAIL: Әйгерім instead of Айгерім; clarification, no appointment |
| mixed-booking-native | Алихан Умаров instead of Әлихан Омаров | PASS: exact client/phone, service/specialist/time and replay |
| kk-repeated-original | Phone77011111111 instead of77022222222 | PASS: exact digits and name |
| mixed-client-original | Russian spelling of Kazakh name | PASS: exact name/phone |
| mixed-digits-original | Алихан instead of Әлихан | PASS: exact name and mixed digit sequence |
| mixed-task-original | Ертәң / қонау instead of Ертең / қоңырау | Strict FAIL: words corrected, initial letter remains lowercase |
| mixed-booking-original | Wrong name and unresolved жете digit tokens | PASS: exact name/phone and booking/replay |

Thus **7/9 strict exact successes in each unchanged API round**, without simulated
human edits. The title's words are correct in an eighth sample, but the original
case-sensitive assertion remains FAIL; it is not relabeled as an exact PASS.

A required regression control, kk-repeated-native, lost one repeated digit in the
first run:7702222222 rather than77022222222. The unchanged second run recognized
all digits. Both use the same WAV and request configuration. This instability,
not only typography, prevents promoting the candidate as the default.
The booking name remained wrong in both rounds. A fixed seed0 probe repeated the
wrong spelling twice; both repeated-phone probes timed out. Seed is not in product code.

## Candidate and alternatives

An opt-in local adapter for `google/gemini-4-carbon` was prepared under
`apps/ai_core/speech.py`. It sends one audio request through `/chat/completions`:
static mixed-language instruction, explicit RU/KK hint when selected, digit words,
temperature0, reasoning low, max_tokens4096. No CRM context, expected answer, tools,
extra correction model, automatic retry or fallback. Response size remains bounded;
truncation, refusal, tool output and malformed envelopes fail closed before any turn.
Existing upload limits, access recheck and no-store remain. Client/task review remains.

The provisional default change was **reverted after the failed exact gate**.
Final settings and .env.example retain `elevenlabs/scribe-v2`; .env was not edited.
The candidate is uncommitted work, not an accepted or deployed replacement.

Comparisons retained under output/voice-accuracy-20261111:
- Scribe with explicit kk helps some spellings but retains name/digit errors.
- MAI-Transcribe2 and Whisper LargeV3 produced additional errors on these samples.
- Gemini3.5Flash fixed the task words/repeated number but distorted other names.
- Carbon/Argon improved several names; neither gave a stable exact full result.
- Overly forceful Kazakh orthography changed a Russian-only name. The final prompt
  explicitly preserves entirely Russian spelling; explicit RU controls passed.
- A1500-token diagnostic limit exhausted reasoning before returning text twice.
  The adapter uses4096 and rejects incomplete output. Medium reasoning produced
  4timeouts/16 probes; it was not selected.
- GPT4oTranscribe, Gemini3.5Transcribe and GrokSTT2 returned404 with the unchanged
  ZDR/no-data-collection flags. Those flags were never relaxed to obtain a route.

Primary API references used:
[OpenRouter audio inputs](https://openrouter.ai/docs/guides/overview/multimodal/audio),
[transcription API and policy](https://openrouter.ai/blog/tutorials/transcription-on-openrouter/),
[Carbon input/parameters](https://openrouter.ai/google/gemini-4-carbon),
[MAI transcription options](https://openrouter.ai/microsoft/mai-transcribe-2).
Public model/endpoint catalog responses and synthetic call receipts are retained.
Credentials stayed in memory; no secret appears in artifacts or source changes.

## Verification and boundary

Existing .venv and scripts.codex_verify.isolated_runtime; disposable SQLite only.
Exact commands:

```powershell
.venv/Scripts/python.exe output/voice-accuracy-20261111/check.py focused apps.ai_core.tests_speech_audio apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers
.venv/Scripts/python.exe output/voice-accuracy-20261111/check.py selected-adapter apps.ai_core.tests_speech_audio apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers
.venv/Scripts/python.exe output/voice-accuracy-20261111/check.py completion apps.ai_core.tests_speech_audio apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers apps.ai_core.tests_speech_formatting apps.ai_core.tests_voice_kazakh apps.ai_core.tests_voice_direct apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_identity apps.ai_core.tests_voice_interface
.venv/Scripts/python.exe output/voice-accuracy-20261111/exact_live.py --round=1
```

Focused20 PASS, selected-adapter20 PASS; each system/drift PASS. Completion91 tests:
90 PASS/1 PostgreSQL-only concurrency skip, system/drift PASS. Domain transactions
were not changed; previous PostgreSQL concurrency evidence is not rerun or relabeled
as a new check. No frontend/build/browser suite: UI, capture and response contract
are unchanged; the changed reachable path is verified through the real speech and
conversation APIs. No full-project/release/human/noise/production certification. After restoring the
original default, final_checks.py independently proved the Scribe route/policy,
manage.py check and migration-drift PASS in a fresh isolated environment.

Round1: **20/25 strict PASS**, 5FAIL. It includes all18 prior samples and7 new
KK/RU/mixed controls (new names, Russian spelling, task wording and a29-second clip).
Failures: the name and number noted above, plus3 title-capitalization mismatches.
Round2 preselected the9 original failures, the new number regression and2 RU
controls: **10/12 strict PASS**, 2FAIL (same name and lowercase title). The full
--sample command and outcomes are in commands.json, exact_live.py and RESULT.json.
All originally failed samples received two live no-correction checks. Successful
cases compared persisted named fields and replay; unsuccessful proposals were not
approved and wrote no CRM rows. The scripts intentionally exit1 when any exact
assertion fails. Original failures are preserved, not overwritten by later success.

Speech latency in round1: median6.735s, max21.969s; whole-flow median11.578s,
max27.828s. These are measurements of this synthetic run on a shared local host,
not a capacity/SLA benchmark. Round2 speech median20.195s, max45.922s demonstrates
additional latency variability on the same configuration. Old18-sample speech
median2.562s is contextual only;
corpus and manual-review work differ.

Additional boundary: Task previews inherited a client1 link without a request in
some fixtures. This also appears in the prior Scribe evidence; it is not caused by
the new speech adapter. The measured task field here is title, not a certification
of all optional relationship grounding. That separate existing planner behavior
was not rewritten as part of this recognition task.

## Remainder

Final additional diagnostic (`specialized_probe.py`, receipts in
`output/voice-accuracy-20261111/specialized-probe.json`): GPT Transcribe returned404
under the same ZDR/data-collection policy. Gemini3.8Flash recognized the repeated
number in one probe, but again returned Әйгерім instead of Айгерім and Russian
spellings in the mixed booking sample. This is not a replacement acceptance run
or evidence of stable accuracy. No product configuration changed after this probe.

- Code/recognition: no candidate has met the exact acceptance target; stable decoding
  of the name and repeated digits is unresolved. No guessing, dictionary forcing or
  lower assertions were introduced to hide this.
- Evidence: exact9/9 and regression acceptance remain open. Human pronunciation,
  noise and production runtime remain outside the available synthetic evidence.
- Environment: no new provider account, bypass of privacy restrictions, working
  database migration or deployment was performed.
- Owner decision: no new policy is needed to retain the existing review/default.
  Accepting a known accuracy regression as a default would change the acceptance
  target and was not assumed. Scope is not fully complete.
