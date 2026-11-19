# VOICE-SCRIBE-V3-20261117: прямое подключение и synthetic-проверка

## Pilot candidate follow-up 20261119

Local follow-up authorized through Manager; starting source `b9415d71e89167fcbf74c55187009481da066389`, current branch `codex/ui-testing-toolkit`, canonical checkout. Subsequently the user explicitly authorized the exact D01–D04 live repeat within 200 ElevenLabs credits and $0.15 OpenRouter, after local PASS. No customer activation, commit/push or shared STATUS/PRIMARY edits authorized. Results below do not replace the historical live FAIL.

| Historical failure | Current boundary / candidate work |
| --- | --- |
| D01 initial surname inflection/drop, even on reference text | Live19Nov attempts1/2 FAIL: identical initial phrase varies between Сынақ and Сынақты. Final bounded D01/D02 reference repeat passes2/2, without triggering clarification; stability/audio remain open. Final local guard asks full name for a bounded ambiguity signal; it does not rewrite names or establish initial-name accuracy. Dropped surname and ASR ambiguity remain open. |
| D02 illegal visit-level client_name patch | 476342c1 scheduling schema plus server rejection; included in current local regression gate. Initial full-name reliability remains separate. |
| D03 negation becomes booking proposal | 476342c1 bounded main-route and stored-confirmation guards; current gate covers recognized negative text. If ASR removes/reverses negation, these guards cannot reconstruct the speaker's intent. |
| D04 unchanged phone presented as corrected | Existing full-phone clarification preserved. New live defect: correctly changed phone plus repeated unchanged visit time was rejected. Retained time fields now accepted; changed time/basis still need latest evidence. D04 reference passes after this fix. |
| Surname correction ignored while another field changes | Reproduced with time change: awaiting_confirmation instead of clarification. Added RU/KK/EN surname words. A second reproducer showed a changed phone could hide an ignored surname; independently check each recognized identity field. Existing full-name clarification, retained draft and new approval are reused. |

### Exact repeat matrix (authorized 19Nov, execution recorded separately)

Reuse the immutable D01–D04 utterances and expected fields in [the original corpus](voice-scribe-v3-dialogues-20261118.json). Fixed clock `2030-11-06T10:00:00+05:00`, Asia/Qyzylorda, synthetic catalog and isolated Business/DB per case and track. Three tracks per case: reference text, saved Aigul WAV, saved Daulet WAV. D01/D02 share the initial phrase deliberately; no population accuracy claim.

| Case | First turn | Second turn | Required judgment |
| --- | --- | --- | --- |
| D01 / reference,f,m | Full name Әсел Сынақ; 7Nov2030 12:00; Консультация; Анна | 13:00 only | Exact full name and unchanged date/service/staff; old approval denied, fresh review. |
| D02 / reference,f,m | Same initial booking | Әсем Сынақ | Correct full name, no visit.client_name, all visit fields retained. |
| D03 / reference,f,m | Explicit refusal to book | Cancel pending only | No appointments/create or client prerequisite proposal, no schedule draft/prepared tool; cancellation must not become creation. No-write alone is insufficient. |
| D04 / reference,f,m | Full name and +77012345678 booking | Last digit 8→9 | Exact corrected +77012345679 is strict success; asking for the full number is safe clarification, not strict success. Never confirm the old number. |

Maximum comparative run: 12 case/track combinations, 24 scored turns, 16 STT requests using existing WAVs. Stop each case after the first wrong critical field, unintended proposal, unexpected clarification, provider failure or ambiguous outcome; do not consume its later turns. The initially proposed three extra text recovery turns are excluded from the authorized exact 24-turn run. Recovery is covered locally; any wrong live proposal remains unconfirmed.

Execute reference tracks first. If critical initial-name/intent failures persist, stop before STT and report the exact blocker. Audio tracks pass unedited transcript through the production normalizer. Report raw transcript, exact name/phone/date/time/negation, strict dialogue success, safe clarification, wrong proposal and unauthorized-write counts separately. WER does not replace critical-span/intent judgment. Current local mock PASS cannot authorize or substitute for this run.

Authorized **new** cumulative ceiling: 200 ElevenLabs credits + $0.15 OpenRouter, including all errors/timeouts. All 16 saved WAV hashes verified19Nov: 97.728 seconds and historical conservative reserve122 (`sum(ceil(seconds+1))`). OpenRouter model `openai/gpt-4o-mini`, at most $0.15/$0.60 per million input/output tokens, 1,200 output tokens/request, no paid retry/fallback. The [official model page](https://openrouter.ai/openai/gpt-4o-mini) confirms these price ceilings on19Nov. Reserve each request from serialized prompt UTF-8 upper bound plus framing before sending; reject when either cap cannot cover it. Actual token sizes depend on dialogue state, so $0.15 is a hard maximum, not a promise all cases will fit. No increase or rollover from old budgets.

Initial preflight19Nov: ElevenLabs subscription GET returned401 `missing_permissions`; this is not proof the key expired. Initial browser account access failed at Page.enable/focus emulation through the documented extension channel. Later19Nov the coordinator reported successful authenticated read-only Chrome access to the ElevenLabs workspace, Free plan and account credit usage counter. Browser/account-counter availability is therefore restored; no balance or account totals are published here. The coordinator observed Scribe v3 API pricing$0.20/hour, keyterm$0.050/hour and FAQ billing per audio minute, but no explicit credits/minute conversion or rounding rule. The actual CRM API key's association with that workspace remains unverified. No settings, key permissions or payments changed and no STT dispatched. The current blocker is proof of a credit upper bound applicable to the actual key, not browser access. Saved subscription401 remains a historical endpoint result; current credit_metering_verified remains false.

New local `candidate_live.py` and `candidate-live/` ledger/results preserve historical artifacts. D03 evaluator now rejects schedule draft or action steps, in addition to no tools/writes and valid state. Reference failures stop audio before spend. Customer runtime/privacy flags stay false; no customer audio, Enterprise activation or human recordings. No secret values stored in evidence.

Intermediate local evidence before the live-discovered fixes: initial2 tests reproduced4 failed assertions; targeted correction suite18 PASS63.442s. Compound name+phone reproducer returned empty instead of client_name; after independent field checks,5 pure focused tests PASS0.003s. Gate238 run234 PASS4 SQLite row-lock skips538.848s/check0issues/driftNoChanges belongs to that earlier source, not final code. Browser3 PASS (1.3m), run1795070107721932200, all5 screenshots inspected. First preparation failed because the new fixture overlapped the existing16:00 appointment; moved only the new fixture to10:00. No product UI/copy change. Build/types/i18n/app/widget/bundle are delegated to the single combined candidate build per Manager's resource instruction; not run here.

Commands from canonical root: `.venv/Scripts/python.exe -m output.voice-scribe-v3-20261117.candidate_checks focused apps.ai_core.tests_voice_corrections`; `candidate_checks compound apps.ai_core.tests_voice_corrections.SchedulePatchTests` with the same module prefix; `candidate_checks final` with the same prefix; `.venv/Scripts/python.exe output/voice-scribe-v3-20261117/candidate_browser.py`; `.venv/Scripts/python.exe output/voice-scribe-v3-20261117/candidate_live.py --dry`. New logs are `candidate-{red,focused,compound,final}-*.log`, `candidate-compound-red.log`, `browser-{prepare,browser,result}-1795070107721932200.*`, `candidate-live-dry.log`; all under existing `output/voice-scribe-v3-20261117/`. Offline harness24/24PASS, zero external calls. Source/dependency manifest: `candidate-manifest.json`. Rerun affected gates if those inputs change; full frontend build remains combined-candidate work.

### Actual live attempts and final local mitigation

[Raw synthetic outcomes, provider responses and cumulative usage](voice-scribe-v3-pilot-20261119.json). No historical result overwritten. Attempts1/2 used the approved D01–D04 reference texts; the second followed a reproduced code fix. Attempt3 repeats only original D01/D02 on the final frozen source, as explicitly authorized after the resource slot opened. The strict expectations remained unchanged.

| Attempt | D01 | D02 | D03 | D04 | Scored turns |
| --- | --- | --- | --- | --- | --- |
| 1 | Both turns PASS; exact persisted fields/replay checked | Initial Сынақты instead of Сынақ; second turn stopped | No booking proposal, then cancel: PASS | Initial PASS; corrected phone rejected due repeated old time fields | 7 of8 |
| 2, after patch-time fix and prompt clarification | Initial Сынақты; second turn stopped | Initial Сынақты; second turn stopped | Both PASS | Both PASS; exact persisted phone/visit and replay checked | 6 of8 |
| 3, final frozen guard, reference only | Both PASS, exact name/time | Both PASS, exact corrected name | Not repeated | Not repeated | 4 of4 |

Attempts1/2 each have2 of4 fully correct reference dialogues; attempt3 has2 of2 selected reference dialogues. This is not comparable to the previous0 of12 result across text and audio as a population improvement rate. In historical attempts1/2, audio tracks were not started because reference critical-name failures persisted. Attempt3 passed its selected reference cases and explicitly excluded STT; the current audio blocker is the unverified account-specific credit upper bound after subscription401 missing_permissions, detailed below. No wrong proposal was confirmed. Exact successful test mutations occurred only in disposable transactions rolled back between cases.

Cumulative total after attempt3: **17 scored user turns /24 ceiling**, **30 successful OpenRouter requests**,72,193 input and2,303 output tokens, provider-reported **$0.00847635 /$0.15 cap**. Latest repeat added4 scored turns,8 provider requests and$0.00233805. **0 STT attempts /0 ElevenLabs credits**. No errors/timeouts/unknown charges. One cumulative ledger; original attempts preserved separately. No account balances in publishable JSON; raw accounting stays in ignored output. Remaining budget does not authorize another corpus or unbounded repeats.

Final repeat details: D01 retains Әсел Сынақ and changes12:00 to13:00; D02 changes to Әсем Сынақ retaining12:00. Both retain7Nov2030/Консультация/Анна, have0 client/appointment/task writes before confirmation, deny stale approval, create exactly1 client/appointment per disposable case, verify exact persisted fields and replay without duplicate. The model returned correct initial names both times, so no safe clarification was observed and no recovery reply was sent. The final safeguard was present but its ambiguity/clarification branch remains mock/browser verified only. These2 selected successes do not erase historical failures or establish full D01 launch acceptance. Output candidate-live-r3/live-results.json and candidate-live-r3-run.log; runner exited0 and isolated DB cleaned up. Resource slot released. App source unchanged; no new model, prompt tuning, STT or corpus.

### Remaining audio boundary after final reference repeat

The latest D01/D02 reference repeat passes; earlier name failures are historical evidence, not a new failed result for this snapshot. Current independent audio blocker: the authenticated workspace credit counter is available (coordinator read-only observation), but actual-key/workspace correspondence and the applicable Scribe v3 credit upper bound remain unverified. The saved subscription401 missing_permissions does not demonstrate an invalid STT key and is not evidence of continued browser unavailability. Historical pilot ledger has10 STT attempts with audio duration and local reserved estimates, but0 provider-reported charged-credit entries. An aggregate seven-day account counter is not a matched per-request receipt: it includes other requests and supplies neither credit conversion nor rounding/minimum/error billing. USD/hour and included allowance do not establish those rules either. Existing receipts therefore cannot prove the proposed run stays within200 credits. Historical ceil(seconds+1) reservations and empirical ratios remain estimates. No scope widening, purchase or new request performed for this analysis.

Remaining cumulative capacity is7 scored turns,200 ElevenLabs credits and$0.14152365 OpenRouter. Full untouched audio matrix is8 dialogues/16turns, so it cannot fit7 turns even if billing is resolved. A useful proposed subset within the original corpus is D01/Aigul + D03/Daulet + D04/Aigul:6turns,6 existing WAVs,39.144seconds; historical heuristic reserve48 credits is NOT verified billing. It covers name/time, negation/cancel and mixed-language phone; D02 audio and other voices remain untested. Reserve the seventh turn rather than start an intentionally incomplete dialogue. This is an analysis-only proposal, not a dispatch or full acceptance plan.

Before any STT dispatch, first establish the actual key/workspace correspondence without exposing the key, then obtain account billing evidence applicable to that key and the scribe_v3 endpoint that yields a conservative per-request upper bound including rounding/errors, or evidence of a hard provider cap <=200 remaining credits for this run. Exact account totals need not enter Git. Then the local ledger can reserve the proven bound before each request; keep timeout/error reservations and stop before either monetary ceiling. OpenRouter remaining budget is enforceable through the existing reservation/max_price mechanism but does not guarantee every call completes. Without that STT bound, audio cannot be shown to respect the credit ceiling; source/text PASS does not close D01/audio acceptance.


The prompt clarification alone did not solve surname normalization. Final local mitigation therefore uses a bounded ambiguity signal: an unselected client's full extracted name exactly appears in a Kazakh booking utterance and ends in one of ны/ні/ды/ді/ты/ті. It requests the full name instead of proposing this uncertain identity, retains phone/visit fields, and permits a subsequent explicit full-name answer with the same ending. No corpus-name lookup or suffix stripping. The counterexample Марат Алтынды is preserved literally after clarification. This may ask an extra question for a real name with those letters; it cannot detect all ASR errors, dropped surnames or other grammatical forms. Historical name-accuracy FAIL remains; the final-source bounded repeat passes2/2 reference dialogues, while the mitigation clarification branch is replay/mock/browser-verified only.

Local tests: retained-time reproducer failed withValueError before fix; correction/scheduling47 PASS53.171s after fix. Initial-name replay reproduced awaiting_confirmation instead of clarification; final name/correction/scheduling50 PASS48.034s. An intermediate full run was intentionally stopped only in its verified owned process tree when the final name guard became necessary; it provides no PASS. Final review also reproduced a regression clearing unknown time; original clearing behavior restored,8 focused pure tests PASS0.003s. Final affected/dependent gate:244 run,240 PASS,4 SQLite row-lock skips232.453s; system check0issues and migration driftNoChanges. Logs candidate-final-{0,1,2}.log. No PostgreSQL concurrency claim. The7 browser screenshots predate only this isolated empty-time fix; their nonempty-time paths are unchanged and covered again by the final backend gate. Final browser **4 PASS42.7s**, run1795071561573584900: initial full-name clarification/recovery, surname correction, short KK-name/RU-time correction, phone correction with repeated unchanged time fields. All7 captured390px screenshots visually inspected, no overflow/clipping, retained values shown, input focus and keyboard approval exercised, no writes before fresh confirmation. Existing UI/components/copy retained; no layout/theme/locale redesign. New runner artifacts live under the existing task output directory; source snapshot `candidate-final-manifest.json`.

Scope/remaining: backend guards and recovery are local candidate work. D01 readiness remains open for initial-name quality outside the bounded guard, ASR/mixed-language ambiguity, audio tracks/human KK and full voice-to-CRM live acceptance. Enterprise privacy/customer activation and deployment remain unapproved/untested. No new lifecycle, permissions, notifications, BusinessEvent, migration or configuration contract. Voice contract updated; README/passport/roadmap still correctly describe open D01 acceptance and are not closed by this slice. Shared STATUS/PRIMARY and publication are left to the candidate coordinator as instructed. Source frozen after the final gate;2097 tracked source/dependency hashes unchanged during verification. Own isolated runners have exited; context-managed temporary databases and browser servers cleaned up. No shared install/build, commit, push or deployment. Final task-owned diff/new JSON, links, registry and provider-secret exclusion checked; no unrelated files claimed.

## Pilot fixes 20261118

Authorized follow-up to the failed live pilot, base19117b41, canonical checkout and
existing branch `codex/ui-testing-toolkit`. No provider requests, credit usage,
customer audio, working-DB migrations or activation changes in this phase.
The historical pilot below remains FAIL; these local checks use fictional fixtures
and substituted provider responses, including the captured incorrect model outputs.

Implemented:

- Explicit recognized booking negations in RU/KK/EN stop a main-route appointment
  or client prerequisite before schedule extraction. Confirmation also rejects a
  stored negated creation plan. Task text and field-level time negation retain their
  existing behavior. This conservative lexical guard is bounded, not universal NLU.
- Scheduling requests use the existing provider JSON-schema capability with a
  named `voice_schedule` envelope. Pending drafts permit either a bounded nullable
  patch or a separate full schedule. Client properties cannot occur inside visit
  objects. Server shape/type/ID/tenant checks remain authoritative, including for
  providers without supported structured output. No automatic paid retries.
- A no-op continuation or a recognized name/phone correction retaining the old or
  empty value asks for clarification without tools or writes. The pending name/phone
  requirement survives another-field correction; successful recovery needs fresh
  review. Explicit separate new bookings can still reuse a client's phone.

Verification: initial pilot regression reproduced five assertions (four negated
main-route drafts and the unchanged phone awaiting confirmation). First correction
gate26 PASS; extended gate31 PASS. Intermediate affected suites201 run/197 PASS,
4 SQLite row-lock skips. Review added a KK time-vs-name regression and narrower
separate-new-booking handling. Final affected/dependent gate235 run/231 PASS,
4 SQLite row-lock skips; system check and migration drift PASS on the final source.
This does not certify PostgreSQL concurrency. Build/types/i18n/app/widget and bundle
gate PASS; existing RU/KK dictionary chunk warnings only.

Initial browser run: existing short-correction flow PASS; new recovery test reached
the correct full-phone clarification with no confirmation action, then timed out
because the test omitted the existing Edit request button before entering its answer.
Test corrected to use the actual UI; no product UI source change was required.
Final browser run `1795020417215060500`:2 PASS in40.9s against the canonical
source with isolated Django/DB and Vite; provider responses substituted. The new
flow proves no confirmation or writes for the old phone, Edit request restores
focused input, corrected phone appears with retained booking details, and keyboard
confirmation creates exactly one visit with the corrected client phone. The existing
KK-name/RU-time correction flow also passes. All three390px screenshots were captured
and visually inspected: readable labels, unclipped values and controls, no horizontal
overflow. Existing components/styles preserved; no visual redesign/theme/layout
acceptance is claimed beyond these affected states. Anti Slop copy gate: specific
RU/KK/EN clarification, neutral client terminology, no invented facts or assets.

Commands: `.venv/Scripts/python.exe output/voice-scribe-v3-20261117/pilot_fixes_checks.py`
(isolated voice/speech/provider, planner JSON/analytics/CRM, memory/state/review/API
suites plus `manage.py check` and `makemigrations --check --dry-run`);
`.venv/Scripts/python.exe output/voice-scribe-v3-20261117/pilot_fixes_browser.py`;
frontend `npm run build` and `npm run check:bundle`. Detailed logs/checkpoint remain
under `output/voice-scribe-v3-20261117/`. Rerun when affected source, dependencies,
configuration or fixtures change; this is a scoped gate, not full release certification.

Remaining code gap: initial name/surname preservation and ASR ambiguity. Remaining
evidence: repeat real-model pilot, larger corpus and human KK recordings. Environment
and owner boundary: Enterprise privacy/no-training and customer activation remain
off/unapproved. No claim that structured output alone improves recognition accuracy,
that all possible corrections are understood, or that full D01 is accepted.
Current voice contract, roadmap, passport, README and task indexes updated together.
Operations/access/CRM/frontend contracts require no change: no new provider setup,
permission, lifecycle, notification, BusinessEvent or UI component was introduced.

## Live dialogue pilot 20261118

Owner explicitly approved200 ElevenLabs credits and$0.15 OpenRouter for the four
pilot dialogues. [Raw results, model outputs, usage and adjudication](voice-scribe-v3-pilot-20261118.json).
Source0dfbffa5; no application source or production settings changed. Only fictional
data, a disposable SQLite DB and the fixed synthetic clock were used. Existing
customer-audio activation/privacy flags remained false. The synthetic-only ElevenLabs
logging exception was applied only to test requests, as previously authorized.

Outcome:12 dialogue/track combinations started,0 fully correct;16 of24 planned
turns scored, with later turns skipped after a mismatch. One male-track cancellation
request timed out and was not retried. The sole not-yet-started male mixed dialogue
was then attempted with the same ledger/caps; no previous request was replayed.
This small deliberately difficult sample is not a population accuracy estimate.

Concrete failures:

- Even perfect text did not produce reliable understanding. The planner retained
  the Kazakh accusative surname `Сынақты` instead of `Сынақ` in one initial request.
  The same initial text in another dialogue was handled correctly, demonstrating
  variation at the configured temperature0.4.
- The name correction produced a top-level client-name patch AND an invalid
  visit-level `client_name`. The server rejected it with `invalid_action_plan`.
- A request to change the final phone digit from8 to9 returned the original full draft;
  the draft still contained the old number. Review prevented execution.
- Negated booking routed to `appointments/create` on reference text and both
  voices. It stopped at a missing-specialist question, not at a semantic rejection.
  No writes is therefore insufficient to call this a correct refusal.
- Six of nine successful STT transcripts have zero normalized word errors, but
  the planner dropped the ambiguous fictional surname in the clean KK examples.
  Mixed RU/KK speech changed `Әсел Сынақ` to `Асель Снаг` / `Осель Снах`.
  Female speech changed `Алдыңғы әрекеттен бас тарт` to `Алдыңғы әрекеттен баста`.
  These are separate ASR and planner failures. Repeated phrases/voices are correlated,
  and `Сынақ` is also a common word: do not generalize this name sample to all KK names.

The D03 runtime evaluator originally checked no writes/tools but missed the booking
route/draft. Manual review tightened scoring to the original `no_booking_proposal`
expectation. The original runtime result is retained next to adjudication. Its second
turn was already executed despite the first semantic failure; this evaluator defect
is disclosed, not hidden by calling the no-write outcome PASS. No further paid rerun.
No incorrect proposal was confirmed and no Client/Appointment/Task was created in
the live runs. Domain confirmation/replay paths were exercised in the offline harness.

Cost/control evidence:

- OpenRouter:31 successful API requests,66,771 prompt tokens +2,316 completion
  tokens; provider-reported total cost$0.00733485, below$0.15. Model fixed to
  `openai/gpt-4o-mini`; max output1,200, provider price ceilings$0.15/$0.60 per million
  input/output tokens, request fee ceiling0 and fallback disabled.
- ElevenLabs:10 attempted requests,9 successful +1 timeout,76.872s attempted audio.
  Conservative reserved credits92, including the timed-out request, below200.
  These reserves are not a claim of exact provider billing.16 prepared WAVs total
  97.728s; only requested clips were charged/reserved. No paid TTS used.
  Final account reconciliation was unavailable: subscription GET timed out at25/60s;
  the old browser showed cached9,070, and after reload the balance field disappeared.
  Do not interpret the cached value as zero spend or invent an exact credit charge.
- Persistent pre-dispatch reservations survive failure/resume. UTF-8 byte count
  plus1,024 framing tokens conservatively bounds input cost; actual provider usage
  settles completed LLM requests. Unknown STT charge remains reserved. No automatic
  retry, redirects, customer-data access or working-database writes.

Verification: budget reserve/reject/settle and resume-preservation checks PASS;
24 mocked harness steps PASS after fixing test-only settings/replay fixtures;
audio hashes/duration, exact persisted fields, stale approval denial, confirmation
replay and transaction rollback checked. Live commands: `pilot_run.py --live`, then
`--resume` for the sole never-started case. Logs and ledger are under the existing
local checkpoint. No application build/full suite rerun for evidence-only changes.

Next code priorities, not implemented in this pilot: reject negated booking at the
main action boundary; constrain the correction schema; detect an unchanged value
after an explicit correction and ask instead of presenting it as fixed; preserve
or clarify ambiguous names. Retest those with reference text before spending more
on speech. Human KK, live accuracy acceptance and production privacy remain open.

## Dialogue preparation 20261118

Prepared, not executed: [24 synthetic dialogues / 48 turns](voice-scribe-v3-dialogues-20261118.json),
16 KK,4 mixed and4 RU. Four pilot dialogues target time correction, Kazakh names,
negation and mixed-language phone correction. Remaining cases cover missing fields,
duplicate names, occupied slots, a selected visit in a plan, cancellation vs starting,
quoted task instructions, forbidden operations, tenant scope and date boundaries.
This is a targeted dialogue sample, not coverage of every possible voice request.

Each dialogue specifies fixture state and per-turn expected fields/status or semantic
outcome. Fixed business clock2030-11-06 10:00 Asia/Qyzylorda makes relative dates
reproducible. Three independent tracks: reference text→real planner, female synthetic
audio→Scribe→planner, male synthetic audio→Scribe→planner. Reset synthetic DB state
between tracks. Unexpected questions stop the case, rather than inventing helpful
answers. Compare raw transcription, normalized critical fields, intent, unchanged
fields, clarification, review and actual isolated mutation. Never confirm an incorrect
proposal. Report ASR and planner failures separately, plus fully correct dialogue rate
per language; no claim about live-human accuracy from synthetic voices.

Read-only account inspection18Nov: ElevenLabs Free10,000 total /9,070 remaining;
OpenRouter credits page displays$0.20. Effective local fast/smart/model settings all
`openai/gpt-4o-mini`; ElevenLabs activation/privacy flags remain false. No billing,
keys, flags or model settings changed. Key validity and per-key cap were not inspected
in this preparation and must be checked before a live run.

Planning estimate (not measured WAV or token usage): two audio voices,2 planner
requests/turn in each of3 tracks;8,000 input and1,200 output tokens/request. Current
[GPT-4o-mini pricing](https://openrouter.ai/openai/gpt-4o-mini) is$0.15/$0.60 per million
input/output tokens. [Scribe v3 PAYG](https://elevenlabs.io/pricing/api) is$0.20/hour;
this is not a conversion rate for the free-credit allocation.

| Set | STT requests / estimated audio | Credit reserve estimate | LLM requests / estimated cost incl.25% reserve | Proposed caps |
| --- | --- | --- | --- | --- |
| Pilot4 dialogues,8 turns |16 /104.4s |126 |48 /$0.1152 |200 ElevenLabs credits +$0.15 OpenRouter |
| Full24 dialogues,48 turns, including pilot |96 /579.6s |710 |288 /$0.6912 |1,000 credits +$0.75 OpenRouter |

Audio estimate assumes2.2 words/s plus1s per clip, minimum3s; credit reserve uses
ceil(estimated_seconds+1) per request from the earlier conservative harness. It is
not a verified billing formula. Full estimate exceeds the current OpenRouter balance;
the pilot fits its displayed balance. No paid TTS is included. Actual WAV durations,
exact prompt tokens and per-request reservation must be checked before calls; never
clip meaningful context merely to fit this estimate. Count attempted requests/errors,
disable automatic retries and stop before either separately approved cap is exceeded.

Preparation checks: JSON parse,24 unique IDs,48 nonempty turns,16/4/4 language split,
4 pilot IDs, fixture references, expected no-write assertions, budget arithmetic,
local links and secret/diff hygiene. No app source changed; app build/backend suites
are not rerun for this corpus/evidence-only change. The four-dialogue pilot budget
was subsequently approved and its execution is recorded above. The full24-dialogue
run remains unexecuted/unapproved; neither the earlier2,000-credit series nor the
pilot approval authorizes that expansion.

## Short corrections 20261118

Owner approved the first two additional improvements: focused clarification and
short corrections. Scope: unconfirmed booking/visit-plan drafts in the existing
voice panel, starting from46443e18 in the canonical checkout. Other integration
WIP is excluded. This does not add a new client/task correction workflow.

The latest open draft is bound to the next turn on the server and read only through
permission-filtered memory. A bounded patch changes client fields or explicitly
indexed visits; omitted fields and visit ordering are retained. Changed time needs
evidence in the latest utterance. Corrected client name/phone invalidates an old
client ID unless a newly supplied ID passes the existing selectable/access checks.
An unnamed replacement specialist asks for a choice even with one catalog option.
Continuation asks one missing field at a time. The old proposal is superseded;
the corrected proposal rechecks scheduling conditions and requires fresh review.
Cancelled/completed/reset/inaccessible drafts cannot supply patch context.

Verification (mocked providers, fictional data, disposable SQLite):

- 9 focused tests PASS,6.342s: RU time, KK name/date, selected visit in a plan,
  specialist clarification, retained fields, replay, stale approval denial,
  completed/cancelled/reset/access-changed context and foreign client denial.
- 194 affected/dependent tests:190PASS/4SQLite row-lock skips,141.739s; voice,
  speech, provider, conversation execution/memory/state/review/API. Django system
  check and migration drift PASS. No working database migrations.
- Chromium reachable flow PASS,18.6s: two successive short RU/KK corrections,
  updated name/time with service/specialist retained, no appointment until review,
  keyboard confirmation and exactly one appointment.390px screenshot captured
  and inspected: labels, wrapping, controls and focus usable, no horizontal overflow.
  Existing panel/layout/copy are unchanged; previous locale/recovery checks remain
  scoped evidence, not new runs. Initial browser failure was the fixture matching
  a prompt example instead of user messages; fixed the fake provider and used a
  distinct fictional name to avoid an unrelated existing-client match.
- Frontend `npm run build` (types/i18n/app/widget) and `npm run check:bundle` PASS.
  Existing dictionary chunk-size warnings remain; app-shell budget passes.

Commands: `.venv/Scripts/python.exe output/voice-scribe-v3-20261117/corrections_checks.py`
and `corrections_browser.py`, with repository PYTHONPATH and UTF-8. The first uses
`scripts.codex_verify.isolated_runtime`; the second starts canonical Vite/Django on
dedicated ports with a fake provider. Logs: `corrections-final-{0,1,2}.log`,
`corrections-narrow.log`, browser run1795017069987136100 under the local checkpoint.
No live STT/LLM requests or credit spend. Production audio activation/privacy flags
remain unchanged/off. Live language interpretation and human KK speech remain open;
these checks prove draft/approval handling, not new ASR accuracy or full D01 readiness.

## Improvements 20261118

Owner annotation authorizes the four follow-up improvements. Implementation is
in the canonical checkout on `codex/ui-testing-toolkit`, starting `e9f45929`;
unrelated integrations/global-search documentation WIP is excluded.

- KK fallback rejects the three reproduced negated/quoted booking examples and
  recognizes `сағат ... жаз`. Router and scheduling prompts explicitly preserve
  corrected names/times and distinguish cancellation from starting.
- Existing-client booking, rescheduling and cancellation now require reviewed
  confirmation. Backend direct-mode bypass is denied; preview shows client and
  date/time, with original/new times for rescheduling. Client references retain
  redaction after access changes. Existing new-client/task review remains.
- Fresh RU/KK UI preferences select an explicit bilingual STT profile. Explicit
  saved auto/RU/KK choices are preserved; English UI still defaults to auto.
- Opted-in card context can supply only the authorized client's name/name parts
  to direct ElevenLabs. Linked task/appointment clients receive a separate access
  check. No tenant directory, phone or notes are supplied. Maximum10 unique terms,
  50characters/5words each, letters/spaces/hyphen/apostrophe only. Foreign/invalid
  context is rejected, archived names omitted, access rechecked after STT.
- Literal phone conversion accepts comma after plus without changing repeated
  digits. Known distorted labels require clarification; grouped numbers are not
  guessed. `numbers_format=words` remains because digits mode had regressions.

Privacy: no live provider calls or credit spending in this implementation cycle.
Existing production activation/privacy flags remain off; logging=false, no audio
storage, no redirects/retries/provider fallback and server-only key remain.
Names are hints, not identity evidence or transcript replacement. Production
usage still requires separate Enterprise STT ZRM/no-training acceptance.

Verification uses isolated SQLite and Chromium with fictional fixtures and mocked
providers. Broad affected/dependent voice/speech/conversation run:156 tests,
152PASS/4SQLite row-lock skips,96.417s; system check and migration drift PASS.
After preview-reference/redaction changes:37 affected tests PASS,45.468s.
Final speech/context validation run:44 tests,43PASS/1SQLite skip,23.083s.
Final name-context run after binding the interface voice runtime:14PASS,5.521s,
including paused-agent independence, linked-client access and archived-name omission.
Frontend `npm run build` (types/i18n/app/widget) PASS after final date formatting.
Chromium:9 scenarios PASS in the combined run, then the remaining recording
scenario PASS with the corrected stable client route (10 distinct scenarios total).
Actual isolated API verifies review/no mutation before confirmation, existing-client
booking, cancelled cancellation proposal, rescheduling, replay, correction of
client/task text and outage input retention. UI locales RU/KK/EN and320/390/1440
widths covered. Synthetic microphone capture verifies KK multipart and context
omitted/included on opt-in, plus retained audio/discard after mocked503.

UI delivery gate (scoped, existing design retained):
- R26/R32/R35 PASS: confirmation/cancel via keyboard and real isolated API; custom
  language selection survives reload; existing edit/retry/input retention exercised.
- R03/R39 PASS: affected320/390/1440 screenshots captured and visually inspected;
  names, original/new local dates and controls remain readable, no page overflow.
  Existing named buttons, focus styles and shared typography/tokens retained.
- R17/R18/R23/R36/R38 PASS: preview uses authorized records; all test identities
  are explicitly fictional. No invented production metrics/assets/content.
- R01/R05/R11/R20/R29/R31 and visual/motion/performance additions N/A: no visual
  redesign, new palette, media, theme or motion. Operational panel retained;
  only target identity/date content and existing settings behavior changed.
- Empty/loading/error/redaction reuse existing components; error retention and
  redaction are exercised. Full-app WCAG, dark-theme recertification and field
  performance are not claimed by this bounded change.

Attempt history: old existing-client-direct test correctly failed under the newly
approved review policy and was replaced with review/no-write/bypass checks. New
transition fixtures first lacked explicit identity and then attached the ID to
the client noun; corrected to explicit appointment ID, preserving the application's
clarification guard. Browser selector initially treated the shared custom Select
as native; fixture initially omitted a synthetic provider base URL. Both fixture
issues corrected without weakening product readiness or privacy checks. Legacy
client query URL redirects to the permanent card route; recording test now opens
that stable route and waits for the actual card before opening the voice panel.

Remaining evidence: no live Scribe/LLM remeasurement after these code changes,
no human KK speech corpus and no production activation. Prompt changes do not
prove live intent accuracy; historical STT accuracy FAIL and full D01 remain open.
No migrations, notification/BusinessEvent behavior or access-policy expansion.
Existing speech/AI/operations contracts updated; CRM lifecycle/access contracts
unchanged because underlying permissions and domain transitions are reused.

Commands/artifacts: `output/voice-scribe-v3-20261117/improvements_checks.py`
(default affected suite; focused labels recorded in checkpoint),
`benchmark_checks.py`, `improvements_browser.py` (then `--grep 'recording sends'`),
`frontend: npm run build`. Logs: `improvements-final-{0,1,2}.log`,
`improvements-speech-final.log`, `improvements-narrow.log` (final14-test run),
`improvements-build-final.log`, `browser-*-1795015422668717800.log` and subsequent
recording-only log.37-test result retained in checkpoint; its temporary log was
overwritten by the final14-test focused run. Screenshots under
`browser-1795015422668717800/` show final localized dates/identity/review UI.

## Обширный синтетический тест, 18.11.2026 — актуальный результат

Проверка выполнена в пределах нового лимита 2000 кредитов. Это тест распознавания
и локальных обработчиков, не сертификация понимания произвольной живой речи.
64 разных вымышленных обращения: 44 KK, 12 mixed, 8 RU. Два Microsoft neural
голоса для KK/mixed (Aigul/Daulet), один подтверждённый локальный Irina для RU.
120 чистых WAV, дополнительные варианты с фиксированным шумом и ускорением.

Матрица покрывает создание клиента/задачи/записи, перенос/отмену, заметки, вопросы
о расписании, относительные/абсолютные/високосные даты, имена, посимвольные и групповые
номера, исправления, отрицания, несколько действий, выбор клиента, неподдерживаемые
деньги/удаление/права, общую речь, тишину и шум без речи. Не все возможные формулировки,
диалекты, микрофоны, реальные шумы и голоса покрыты.

Всего 298 условий: основная матрица 290 и 8 отдельных опытов с keyterms.
295 HTTP200,2 HTTP429, тишина отклонена локально как audio_empty до сети.
Один из 429 содержит system_busy; после паузы серия продолжена с интервалом 4.2 с.
Уже отправленные случаи не повторялись; две неудачи сохранены. Шум без речи дал
пустую строку: рабочий parser отклоняет её как отсутствие речи.
Успешно отправлено 1483.793 с аудио. Продуктовые код/настройки/БД/серверы не менялись;
OpenRouter/planner не вызывались, реальные клиенты не использовались.

### Бюджет и граница атрибуции

Лимит существующего STT-only ключа уменьшен 5000 → 2097 за период:
97 прежних кредитов +2000 на эту серию. Срок и права ключа не расширялись.
Консервативный резерв основной серии и keyterms —1940; это защитная оценка,
не счёт провайдера. Analytics/Usage вырос 97 → 930, то есть на 833 кредита;
остаток этой границы — не менее 1167. Billable Request Count вырос 22 → 327,
тогда как локально подтверждены 295 новых HTTP200: разница 10 запросов
не атрибутирована. Журнал показывает наши последние STT-вызовы и обращения
кабинета, но не доказывает причину расхождения. Поэтому 833 — прирост аккаунта
и верхняя граница расхода серии, не точная отдельная стоимость 295 вызовов.
Лимит соблюдён; дальнейшие STT-вызовы остановлены.

### Точность на чистом аудио

WER — доля вставленных/пропущенных/заменённых слов, ниже лучше; это не доля
неправильно выполненных команд. Пунктуация и регистр исключены, ё/е уравнены,
казахские буквы не заменялись русскими. CER аналогично оценивает символы.
Для KK сравнение строго парное:86 одинаковых аудиофайлов с успешным ответом
в обоих профилях. KK/RU означает language_code=kk и secondary_language_codes=ru;
auto не задаёт оба поля. Имена проверены с границей начала слова и допустимым
падежным окончанием: «Кәсел» не засчитывается как «Әсел».

| Речь / профиль | Записей | WER | CER | Точные имена | Телефон после обработки |
| --- | ---: | ---: | ---: | ---: | ---: |
| KK, KK/RU | 86 | 1.36% | 0.27% | 48/54 | 10/12 |
| KK, auto | 86 | 6.53% | 4.53% | 48/54 | 7/12 |
| Mixed, KK/RU | 24 | 15.98% | 7.26% | 10/20 | 4/6 |
| Mixed, auto | 24 | 19.26% | 8.35% | 9/20 | 4/6 |
| RU, RU/KK | 8 | 0.00% | 0.00% | 4/4 | 2/2 |


Результат чистого KK не распространяется на mixed: имена сохранены лишь
в 10/20 (KK/RU) и 9/20 (auto) проверенных вхождениях. Среди 86 KK-auto метаданные
языка: kaz79, ukr4, rus2, tur1. Часть mixed-цифр передана русскими словами
при правильных значениях: это увеличивает WER без обязательной потери смысла.
Ошибки произношения синтезатора тоже возможны; независимое прослушивание носителями
языка и живые записи ещё не выполнены. Эта выборка не оценивает всю популяцию.

### Что дали настройки и условия

- На 20 одинаковых телефонных записях words + штатная нормализация сохранили номер
  в 16/20, digits —18/20. Три улучшения и одна регрессия: у RU номера 77010002030
  в digits появился лишний ноль —770100002030. У mixed номера 77022222222
  в digits потерялась цифра: +7 [70] 222-22-22. В двух words-ошибках правильные
  групповые числительные сохранены моделью, но намеренно не преобразованы
  приложением без уточнения. Это не ошибка STT.
- На 8 выбранных проблемных примерах имён единый словарь 10 вымышленных имён
  улучшил написание 4/8 → 7/8. Осталось Айгерімнің → Әйгерімнің.
  Это прицельный опыт на известных ошибках, не независимая общая оценка.
- Для 12 одинаковых файлов WER: чистые 9.52%, шум 20dB11.11%, шум 10dB28.57%,
  ускорение 1.25×11.90%. Только KK (8 файлов):20dB2.70%,10dB20.27%,
  ускорение 1.25×1.35%. При 10dB оба KK номера ошибочны. Это искусственный
  белый шум относительно RMS всего WAV и цифровое ускорение, не реальные
  помещения или естественная быстрая речь.
- Вручную сверены 17 чистых транскриптов пяти абсолютных дат:07.11.2030 12:00,
  31.12.2030 23:55,29.02.2032 08:30,08.11.2030 10:00,09.11.2030 10:00.
  Значения сохранены словами; календарный parser/timezone/создание записей
  не проверены. Время 23:55 иногда разделено запятой.

### Что доработать — подтверждённые основания, без реализации в этом тесте

1. **P1: важные поля и смысл исправления.** «бас тарт» стало «баста»
   (отказаться → начать), «Әсел емес, Әсем» теряет отрицание; имена специалиста
   и клиента искажаются в mixed. Сохранять существующие identity review/проверку
   совпадений, усилить проверки исправлений/отмен и конкретного имени, телефона,
   времени перед изменением. Низкий WER не доказывает безопасность действия;
   фактическое опасное изменение CRM здесь не воспроизводилось.
2. **P1: локальный признак команды записи.** На идеальном тексте
   voice_booking_request возвращает True для «Әселді қабылдауға жазып жіберме»,
   «Әселді қабылдауға жаз деп айтқан жоқпын» и «Әселді қабылдауға жазыңыз деген
   тапсырма жаса». Для команды 15 без слова «қабылдауға/консультацияға» — False.
   Это вспомогательный признак восстановления неполного маршрута, не полный NLU;
   используется в conversation_router и validate_voice_plan. Нужны регрессии
   отрицаний, цитируемой команды и явного запроса задачи.
3. **P1: неразобранные номера.** В 09-kk-phone-f-auto язык отмечен tur, текст
   начинается «Telefon nömrə…»: телефон не нормализован,
   ambiguous_spoken_phone=False. Сигнала уточнения также нет у двух KK шумовых
   случаев и одного неверного цифрового mixed номера. Расширить безопасное
   обнаружение диктовки/пунктуации/меток и проверку полного номера по региональному
   формату; цифры не дополнять догадкой. Неверное, но допустимое число всё равно
   требует проверки соответствия клиенту. Существующее уточнение для распознанной
   неоднозначности сохраняется.
4. **P2: язык и словарь.** Для преимущественно KK использовать существующий явный
   выбор KK с дополнительным RU; frontend сейчас default auto. Отслеживать
   неожиданный язык ответа: production speech возвращает text/duration,
   detected_language не передаётся. Keyterms показал пользу; рабочий словарь
   должен быть ограничен Business и прежними условиями приватности.
5. **P2: numbers_format.** Кандидат digits улучшил счёт, но создал регрессию:
   не переключать глобально без проверки цифр, новых регрессий и review.
   Не скрывать ошибку за LLM-«исправлением». Платные повторы автоматически не включать.

Понимание полной команды планировщиком, многотуровый контекст и исполнение на живом
OpenRouter не оценивались; баланс OpenRouter не расходовался. Регрессии используют
mock provider. Далее нужны эти доработки, полный изолированный
voice→plan→review→CRM и живые вымышленные KK-записи 2–3 людей, как согласовано.
Реальные данные по-прежнему требуют Enterprise STT ZRM/no-training;
ENABLED/PRIVACY_CONFIRMED остаются False.

### Воспроизводимость и проверки

Canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit, исходный
HEAD61a7946f; voice-файлы не менялись. Чужие integrations/payments/scheduling/frontend
WIP сохранены. Обычная БД, миграции и deployment не затронуты.

- benchmark_prepare.py: фиксированное synthetic-аудио. Dmitry в online TTS дважды
  не вернул звук; недоступный локальный Pavel не засчитан как отдельный голос.
  Финальный manifest RU содержит только Irina, неиспользованные файлы не отправлены.
  Внешняя TTS-подготовка вымышленных текстов — без ElevenLabs.
- benchmark_manifest.py и benchmark_run.py --preflight: SHA256/WAV/объём/флаги PASS.
  Тишина дала audio_empty и учитывается как локально заблокированная.
- benchmark_run.py --live, затем --continue после паузы:287 HTTP200/2 HTTP429/
  1 local block. Exit2 сохраняет две ошибки; это не 290 успешных вызовов.
- benchmark_keyterms.py --live:8 HTTP200, cumulative reserve1940, exit0.
- benchmark_checks.py через scripts.codex_verify.isolated_runtime: найдено 37,
  36 PASS/1 skipped (SQLite не поддерживает select_for_update),21.137 с;
  Django system check0issues. Модули: tests_elevenlabs_speech, tests_speech_numbers,
  tests_voice_booking_intent.BookingInstructionTests, tests_voice_kazakh,
  tests_voice_identity. Ключ пуст, provider mocked, disposable DB.
- Build/UI/full-project gate/migration drift не запускались заново ради evidence:
  продуктовых изменений нет. PostgreSQL concurrency PASS не заявляется.
  Итоговые docs/artifact checks и publication записываются в checkpoint.

Локальные инструменты/логи находятся в ignored output/voice-scribe-v3-20261117.
Точные строки, профили, SHA аудио, результаты/ошибки и расчёт метрик — в
[JSON-артефакте](voice-scribe-v3-benchmark-20261118.json), без ключа и локальных путей.
Номер оценивается как вся последовательность цифр без пунктуации, не ограниченный
regex форматирования: +7 [70]… не считается ошибкой из-за скобок. Исходный
regex-результат сохранён отдельно. Критичные фрагменты оцениваются буквально,
не как семантическое понимание. Ошибочные транскрипты не исправлялись.

Официальные параметры сверены по
[Create transcript](https://elevenlabs.io/docs/api-reference/speech-to-text/convert):
digits/words, primary/secondary languages и keyterms; последний добавляет 20%
к стоимости STT. В production экспериментальные настройки не включались.
Scope синтетической диагностики завершён; качество mixed/критичных полей не закрыто.
Остаток: код — указанные доработки; доказательства — живые голоса/полный flow;
среда — ZRM и planner; решение — активация отдельно.

## История предыдущих проверок

## Initial three-clip snapshot, 18.11.2026

Подключение Scribe v3 проверено на трёх коротких вымышленных русских фразах.
Рабочая активация для клиентских данных НЕ выполнена. 56 изолированных тестов,
Django system check и migration drift прошли. Ключ сохранён только в локальном
gitignored .env. Ограничения ключа проверены в ElevenLabs: только Speech to Text,
5000 кредитов за период, истечение19Nov15:53 по отображению кабинета, автоотключение
при обнаружении утечки включено. Остальные права No Access.
Владелец разрешил18Nov synthetic-тесты без Zero Retention и максимум5000 кредитов.
В кабинете Analytics/Usage после проверки:3 billable requests,14s,8 credits,
average2.67 credits/request. Остаток согласованного тестового бюджета4992.
Пополнение/подписка/автопополнение не включались.

Начальная подготовка17Nov:4cc19068, без тестов по тогдашнему указанию.
Продолжение18Nov: canonical C:/Users/user/Desktop/PlatformaCRM,
codex/ui-testing-toolkit; HEAD48f201be при старте проверки, затем чужой CI commit
58a6427e. Ранее подготовленный voice diff сохранён; чужие Meta footer PRIMARY
не входят в эту задачу. Текущие проверки относятся к unchanged voice source.

## Реализация и защита реальных данных

- Fixed model scribe_v3, direct HTTPS multipart WAV, bounded in-memory transport.
- Рабочий build_request всегда использует enable_logging=false.
- ELEVENLABS_SCRIBE_ENABLED и ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED default False.
  Ключ сам по себе не включает отправку. Существующий provider=openrouter сохранён.
- Privacy flag фиксирует внешнее подтверждение Enterprise STT ZRM/no-training,
  а не техническое доказательство условий аккаунта. Для текущего free-аккаунта
  такое подтверждение не получено, флаг не установлен.
- Неизвестный provider/выключенный AI/voice/неполная конфигурация дают отказ до сети.
  Прежние backend role/Business permissions и подтверждения CRM сохранены.
- No redirects, retries, fallback, raw audio/text/key logging; response64KB/text4000,
  WAV mono16kHz PCM16 до2MB/60s. Нет SDK/dependency/schema изменений.
- Прямой STT не использует баланс OpenRouter; planner остался отдельным.

Только локальный ignored output/voice-scribe-v3-20261117/live_synthetic.py
строит запрос с enable_logging=true. Это одноразовый инструмент проверки,
не imported application code, не env-флаг и не публичный API.
Он генерирует три фиксированные фразы локальным Microsoft Irina Desktop:
не принимает произвольный файл, текст, микрофон или CRM-сущность.
Повтор отсекается существованием live-20261118.json, не более3 запросов/30с,
ошибка останавливает серию; дополнительный provider cap5000.
Test-only mock is_configured позволяет переиспользовать multipart builder;
настройки ENABLED/PRIVACY остаются False, readiness проверен False до/после.
Эта проверка доказывает transport/model/parse, не рабочий customer API без ZRM.

## Проверки

Из корня, установленный .venv/Scripts/python.exe:
- output/voice-scribe-v3-20261117/verify.py, через scripts.codex_verify.isolated_runtime:
  manage.py check; makemigrations --check --dry-run; test следующих модулей:
  apps.ai_core.tests_elevenlabs_speech, tests_speech, tests_speech_audio,
  tests_speech_diagnostics, tests_speech_numbers, tests_speech_formatting,
  tests_voice_interface. 56 тестов PASS,51.572с; system0issues, drift none.
  Отдельная disposable SQLite, сеть provider mocked, ключ пуст.
- output/voice-scribe-v3-20261117/live_synthetic.py --live:
  отдельный isolated_runtime, реальный ключ только в памяти процесса;
 3 HTTP200, без OpenRouter/TTS API/CRM mutations.
- Source/diff review, git diff --check, registry JSON, local link existence.
  UI Delivery Gate N/A: продуктовый интерфейс не менялся.

| Synthetic case | Seconds | API elapsed | Результат |
| --- | ---: | ---: | --- |
| Создай тестовую задачу проверить расписание завтра | 4.780 | 1.453 | Смысл и слова сохранены |
| Перенеси вымышленную встречу на завтра на пятнадцать тридцать | 5.145 | 1.281 | Завтра и15:30 сохранены словами |
| Тестовый номер ноль ноль один один два два три три | 4.315 | 1.344 | Все восемь цифр и повторы сохранены |

Суммарно14.24с. Полный synthetic transcript в локальном live-20261118.json.
Это не пользовательские данные. Сервис ничего в CRM не создал/не перенёс.
Попытка генерации до сети сначала дала audio_format: System.Speech возвращал PCM
без WAV header. Исправлен только test harness: PCM упакован в WAV через wave.
До исправления запросов провайдеру не было. Живые запросы не повторялись.

Локальные артефакты: CHECKPOINT.md, verify.py, verification-20261118.log,
live_synthetic.py, live-20261118.json/log в output/voice-scribe-v3-20261117.
Секрет не включён в tracked source/evidence; временный ключ переноса удалён.

## Граница приёмки и остаток

Scope подключения и первых synthetic-проверок завершён локально.
Реальные клиенты/аудио не использовались; рабочая БД, миграции, серверы и deployment
не затронуты. Прежние accuracy failures и D01 не закрыты.
Код: нового рабочего privacy bypass нет. Доказательства: широкая точность RU/KK/mixed,
шум/живые голоса/имена/телефоны и полный voice->CRM flow этим набором не покрыты.
Среда: Enterprise STT ZRM/no-training для real data не подтверждены; тестовый ключ
короткоживущий. Решение владельца: рабочая активация и дальнейший объём отдельно.
Frontend/access/CRM contracts без изменений: публичный API/права/flow прежние.
Operations/voice/README/roadmap/passport/STATUS синхронизированы с этим срезом.

Официальные условия:
- https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- https://elevenlabs.io/docs/eleven-api/resources/zero-retention-mode

Publication записывается в checkpoint отдельно; local/live PASS не означает deploy.

## Expanded synthetic acceptance — 18.11.2026

Owner authorized RU/KK/mixed, names, numbers and dates with 4992 credits remaining.
Source a3753708; production voice code unchanged from b5dde74b. Prior56 isolated
tests reused as unchanged-source evidence, not rerun. No production activation.

19/19 HTTP200; 163.111 seconds audio, no retries. Command (PYTHONPATH=root):
`.venv/Scripts/python.exe output/voice-scribe-v3-20261117/expanded_synthetic.py --live`
Exit0 proves transport only. Synthetic corpus:7 RU Microsoft Irina/Pavel clips,
6 KK and6 mixed kk-KZ-AigulNeural/DauletNeural clips, reused from11Nov.
KK/mixed SHA256 verified against historical native-manifest; all WAV hashes pinned.
Fixed two corpus directories; <=24 requests/400seconds, exclusive report marker,
isolated runtime. No new TTS, OpenRouter, real client data, CRM writes or deployment.
Production enable/privacy flags and readiness remain False before/after. Logging=true
exists only in this ignored synthetic harness, not application API/configuration.

| Group | Requests | Exact client names | Normalized phones |
| --- | ---: | ---: | ---: |
| ru | 7 | 6/6 | 4/6 |
| kk | 6 | 4/5 | 4/4 |
| mixed | 6 | 3/5 | 2/5 |

Specialist names3/5; task titles2/3 (RU control reviewed manually).
All5 spoken dates/times preserved by manual transcript comparison:
kk-booking2030-11-07 12:00; mixed-booking2030-11-08 10:00;
kk-conflict2030-11-09 12:00; mixed-conflict2030-11-10 12:00;
ru-booking-two-names2030-11-09 10:00. This does not verify date parser/planner/CRM.

Failures retained without transcript correction:
- kk-client-auto, mixed-booking, mixed-conflict: Kazakh name spelling changed;
  mixed-task: final Kazakh letter in first title word changed.
- mixed-digits: spoken digit values preserved but commas prevent application phone
  normalization. mixed-booking: grouped seventy-seven preserves prefix value but
  compound numbers are unsupported by the normalizer.
- mixed-conflict: repeated Kazakh twos recognized as Russian ones: actual digit error.
- ru-male-voice, ru-eight-prefix: grouped number words change digit sequence as well
  as preventing normalization; blind concatenation cannot repair these safely.
- mixed-eight: command words distorted despite preserved name/phone.

Synthetic pronunciation may contribute; these results do not establish live-human
accuracy or comparative model superiority. Recognition acceptance remains FAIL.
Noise/live voices and full voice-to-CRM flow remain unverified. Follow-up needs phone
handling/ambiguity confirmation and further fictional voice checks; no product fix
was included in this verification scope. Enterprise STT ZRM/no-training and production
activation remain separate. Existing privacy/customer-data protection unchanged.

ElevenLabs authenticated Analytics/Usage:22 billable requests,97credits,3m rounded,
4.41credits/request. Prior3 requests cost8: expanded series89 credits; remaining
5000-97=4903. No additional calls. Budget is cumulative, not reset per run.
Local ignored artifacts: expanded_synthetic.py, expanded-corpus.json,
expanded-live-20261118.json/log under output/voice-scribe-v3-20261117.
No secrets in tracked evidence. Test execution scope complete, quality failures open.

Median request 2.235s; range 1.297–4.641s.
