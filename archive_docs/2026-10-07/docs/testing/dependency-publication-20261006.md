# PUBLICATION-20261006 — dependency remediation and accumulated changes

## Scope and ownership

Owner requests publication of all accumulated uncommitted work, followed by actual
GitHub CI. The owner corrected the initial CD request: **no deployment**. After
reviewing the known dependency blocker, the owner chose remediation and verified
UI compatibility before publication, including the required Tailwind migration.
New AI memory/orchestration implementation is not part of this delivery phase.

Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; registered generation3 owner;
branch `codex/ui-testing-toolkit`; starting HEAD and remote main:
`9ff366207e73472cda71ca3b9113ca4f9f305af9`. All 193 initially changed/new paths are
included by explicit owner authorization. Initial per-file hashes and tracked
patch are retained under `output/publication-20261006`. No other writer, branch
switch, alternate source tree or working-database operation was used.

## Dependency repair

The read-only npm audit reproduced the old failure and newer advisories. `braces`
3.0.3 has no published patched release; its Tailwind3 dependency chain cannot be
fixed by a patch update. See the
[upstream advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).

- Tailwind3.4.19 → **4.3.3**, with `@tailwindcss/postcss`4.3.3.
- PostCSS8.5.23 → **8.5.29**, DOMPurify3.4.13 → **3.4.16**,
  source-map-js1.2.1 → **1.2.2**. Lockfile changes include required transitive updates.
- Removed the old braces/micromatch/fast-glob chain. No audit exclusions,
  vulnerability suppression, renamed vulnerable packages or forced incompatible
  overrides. npm audit reports **zero vulnerabilities**, including low severity.
- Removed redundant autoprefixer; Tailwind4's PostCSS plugin handles prefixing.

The official upgrade tool migrated CSS/config loading but stopped during template
conversion with a module-resolution error. Its partial changes were inspected;
remaining template conversion and PostCSS setup were completed explicitly. This
failed attempt remains in `tailwind-upgrade.log`, not represented as a clean run.

## UI compatibility

Preserved the semantic JSON palette and existing TypeScript theme adapter through
`@config`. Automatic source scanning is disabled; the existing configured source
paths remain authoritative. Components use Tailwind4 utility names, including
`shadow-xs`, `rounded-sm` and `outline-hidden`. These are name migrations, not a
visual redesign. All 79 template changes were compared against the reviewed staged
source; the additional Button change resolves caller/base utility conflicts using
the existing tailwind-merge dependency, so explicit compact sizes keep precedence.

The first comparison exposed changed mobile input typography, inherited line
height and ActionMenu button size. Fixed these rather than accepting new screenshots
as a baseline. Explicit line-height compatibility preserves the prior text rhythm;
CSS layers preserve the former selector precedence. Existing semantic color values
and radii are retained. New shadow/color serialization can differ while rendering
the same pixels.

Baseline generated CSS plus 12 screenshots/computed-style snapshots were captured
**before** changing dependencies: shared controls and feedback catalog, RU/KK/EN,
1440×1000 and390×844. After fixes, every captured element's geometry, font size and
line height match. Pixel comparison at threshold0.1: 11 exact rendered comparisons,
one with2 differing pixels. This is representative shared-component evidence,
not a claim that every page or older browser was visually certified.

Five action-button keyboard focus states and input focus in forced-colors mode
passed. Existing screenshot fixtures are development evidence, not merchant data.
The app's own frontend was restarted after dependency changes (PID15372); source
root and HTTP200 CSS readback were checked. Backend runtime was unchanged.

Tailwind4 requires Safari16.4+, Chrome111+ or Firefox128+ per its
[upgrade guide](https://tailwindcss.com/docs/upgrade-guide). These are upstream
minimums, not browser versions exercised in this run. Older-browser support and
Safari/Firefox rendering were not certified here.

## Verification

- `npm run build` through the project's `isolated_runtime`: **PASS**, including
  i18n, TypeScript, app and widget builds. `npm run check:bundle`: **PASS**.
- Focused action-color, feedback, fallback, sidebar and notification policy suites:
  **24 PASS** (`frontend-policy.log`).
- Python/frontend lock validators and working/index diff hygiene: **PASS**.
- `npm audit --audit-level=moderate --json`: **PASS**, zero vulnerabilities
  (`npm-audit-final.json`). Python audit also passed with no known vulnerabilities (`python-audit.json`);
  final browser readback is recorded below.
- No paid model calls, new migrations, working-DB writes or external message sends.
  Current AI/backend code hashes match the final behavioral evaluation; its affected
  backend checks are retained. GitHub CI will independently run the full backend.

The initial combined browser invocation had20 PASS,4 skipped and4 failed fixture
setups: tests shared a business, accumulating CRM agents and exceeding its plan
quota. This repeats the documented fixture-isolation boundary, not a CSS failure.
The failed cases passed against fresh independent databases: **24 unique browser
checks PASS** in total. Permission and quota assertions were not relaxed. The4 skips are viewport-specific smoke cases. Two local attempts timed out during
server preparation before the test body; a temporary evidence-only configuration
increased server startup allowance from120s to300s and exposed startup output.
The test timeouts and assertions stayed unchanged; the final mobile CRM test
passed. One combined grep selected only actions, so CRM was explicitly rerun
with `crm: every profile`; results are counted by actual executed case names.

Commands and exact filter evidence are in `browser-migration.log` and
`browser-isolated-retest.log`. The latter uses the existing isolated helper:

```text
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py PROJECT SPEC --grep FILTER --output=../output/publication-20261006/RESULT
```

Results, screenshots, first failures, audit JSON, lock delta and source snapshots
are local ignored evidence under `output/publication-20261006`.

## Publication and limits

All selected local checks passed. The accumulated snapshot is commit `5febd35`;
the dependency migration is `426b330279213558ca76542c8c445bc133f62f28`.
The real committed-range gate passed:

```text
.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref 9ff366207e73472cda71ca3b9113ca4f9f305af9
```

After fetching main and proving ancestry, normal `git push origin HEAD:main`
succeeded. Independent `git ls-remote origin refs/heads/main` returned the exact
application commit above. [Application CI run37493074978](https://github.com/999MAX20/PlatformaCRM/actions/runs/37493074978)
has frontend SUCCESS (installation, build/widget, bundle and dependency audit).
At receipt time backend schema/system/static/readiness checks passed and its full
test suite was still running. This observation is not full CI PASS.

This receipt changes only STATUS, PRIMARY-SESSION and this report. Its gate is
link/consistency review plus working/index/actual committed-range diff hygiene;
application inputs and validated local evidence remain unchanged. The final
receipt commit is identified by this file's Git history. Actual final CI results
and remote SHA are reported in the task response and retained under local ignored
`output/publication-20261006`; no additional receipt commit is needed to describe
the receipt itself. CI remains inspectable in [GitHub Actions](https://github.com/999MAX20/PlatformaCRM/actions).

This delivery does **not** close the six failed real-model scenarios or the manual
quality limitations in the [AI behavior report](ai-agents-behavior-20261006.md).
Memory, model-control design and orchestration proposals remain the next product
discussion; green infrastructure CI does not turn those scenarios into PASS.
