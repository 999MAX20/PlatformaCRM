# Provenance and adaptation

Upstream: [anti-slop](https://github.com/miqdadbadjuber/anti-slop), Miqdad Badjuber.
Examined on 2026-11-02 at main commit
`941b1532f9cc8ffde766bca5921d75257c9e5762` (2026-11-01).
[Immutable tree](https://github.com/miqdadbadjuber/anti-slop/tree/941b1532f9cc8ffde766bca5921d75257c9e5762).
Copyright (c) 2026 Miqdad Badjuber (antislop). MIT notice retained in
[LICENSE-upstream](../LICENSE-upstream). Local adaptation: PlatformaCRM, 2026-11-02.
No installer or global original package installed.

Examined core `antislop.md`, skills antislop, antislop-ui, antislop-copywriting,
antislop-code, antislop-human, antislop-layoutmobile and human WCAG/A11Y references.
These are research inputs, not runtime dependencies. The adaptation expresses its
own bounded workflow; it does not vendor the third-party WCAG/A11Y reference text.
The upstream human reference license was inspected; those files are not redistributed.

| Source idea | Local decision and reason |
| --- | --- |
| Purpose test, real metrics, meaningful states | Retain; align with AGENTS section 8 and API-backed CRM workflows. |
| Default during/after question, global mode settings, blocking before read-only review | Omit; user's task already sets scope and permissions. |
| Multi-part all-yes Delivery Gate | Replace with findings/coverage/limitations; a failed or untested item remains visible. |
| Visual rhythm, palette/theme/assets prescriptions | Use existing semantic tokens and shared components; no mandatory redesign or theme toggle. |
| Repeated cards/tables as a tell | Investigate utility; repetition improves CRM scanning and predictability. |
| Comment length maximum two lines; drop issue/version history | Reject; preserve information needed to maintain business and security invariants. |
| Human skill lines 26/65: large text 18px+ | Correct to 18pt regular /14pt bold; 18px regular requires 4.5:1. |
| Copywriting tells and punctuation bans | Adapt to RU/KK/EN grammar and approved copy; no mechanical anglicization. |
| Accessibility/mobile and truthful measurements | Retain with explicit observed/source/untested boundaries. |

Contrast authority: [W3C Understanding SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
checked 2026-11-02. Thresholds apply to computed sizes/weights, not guessed screenshot pixels.
