# Google button appearance and spacing, 19 November 2026

Scope: user chose white rounded official Google button on login/signup, centered on the form axis; then requested equal top/bottom gaps. Source base a932b58a. No auth behavior, business data or deployment changes.

Changed shared Google renderer to outline/large/pill with official left-aligned G; centered the mount and loading label. Preserved 44px reserved mount, nonce renewal, static label, disabled/retry/callback behavior. Shared social-row top margin and divider margin are 16px; including mount inset, measured visible button gaps are 18px above and below.

Checks: npm --prefix frontend run build PASS after final CSS edit (i18n, TypeScript, Vite app/widget); eight token-csrf Node tests PASS; scoped diff hygiene PASS. Full CI not required for this local styling change.

Chrome extension inspection used real Google SDK with a synthetic preview API on 127.0.0.1:18590, no login/registration supported by preview. Desktop and 390x844 mobile login/signup screenshots captured and inspected. Equal vertical gaps:18px. Desktop login horizontal gaps11.20px/11.20px; signup120.875px/120.888px (subpixel rounding). Mobile login0.40px/0.40px; signup0.30px/0.30px relative to form content. No page horizontal overflow. Official G and full Russian label visible. Keyboard Shift+Tab from email reaches Google button and shows focus outline. No new live OAuth sign-in is claimed.

Applied Anti Slop during, UI/human/layoutmobile: scoped geometry, official logo, responsive width, keyboard focus PASS. Provider-controlled official outline/40px button retained; SDK styling is not overridden to impose a different border/tap height. Existing reserved mount remains44px. No new motion, copy, assets or dialogs. Other locales and a full live OAuth round trip were not rerun for presentation-only options.

Screenshots and build log: output/google-button-design-20261119/. Existing unrelated WIP is excluded from this change. Local preview remains available for owner review; no server deployment performed.

## Pre-deployment correction after manager coordination

2032202e was not deployed. Manager identified that large may restore personalized name/avatar for an approved Google session; official Google documentation confirms only medium/small exclude personalization: https://developers.google.com/identity/gsi/web/guides/personalized-button . Returned renderer to medium and narrowed its type accordingly; kept pill, outline, full official G, center,16px margins and44px reserved mount. Final visible gaps are22px above/below on both forms (medium32px height centered in44px mount); earlier18px measurements describe the superseded large preview only.

Final local build/i18n/types/app+widget PASS (build-static.log). RealSDK local login/signup inspected: static labels, complete G, equal22px vertical gaps, equal horizontal margins. Server deployment will be combined with manager's multitab auth candidate; no independent server change made.

## Server acceptance after coordinated deployment

Manager deployed combined source cba360ca, runtime tree 64d29158, opened at 2026-11-19 16:56:30 UTC. Includes final button correction a0dfb128. No separate deployment was performed by this side conversation.

Live https://platformacrm.kz/login and /signup: real Google SDK medium/outline/pill confirmed; static labels without account name/photo, complete G, centered button, equal visible vertical gaps of 22px. Desktop and 390x844 mobile inspected; no horizontal overflow. Keyboard focus visible; Enter opened Google account chooser. /ready/ returned healthy at 16:58:33 UTC. Final full-page screenshot live-signup-final.png captured and visually inspected successfully; earlier repeated viewport captures had repaint artifacts and are not the preferred final proof.

Actual OAuth round trip NOT VERIFIED: accounts.google.com account chooser stayed on the visible Loading state after account selection, with no visible error or consent prompt. Manager observed no /verify callback reaching CRM. Closed the stalled agent popup; subsequent signup Enter attempt timed out and no new Google popup remained. No further unchanged retries, account creation, linking, consent acceptance or user-session logout performed. No specific user action is requested for this presentation acceptance; an actual OAuth round trip remains a separate unverified result.

Final screenshot: output/google-button-design-20261119/live-signup-final.png. Other live captures: live-login-desktop.png, live-signup-desktop.png, live-login-mobile.png, live-signup-mobile.png. Server signup left open for user review.

### Reopened first-paint acceptance

After the settled-layout checks above, manager reproduced real GIS bootstrap expanding the min-height slot 44 -> 64 -> 44px and shifting the card 10px. Thus overall motion acceptance is pending a manager-owned fixed-height patch and deployment; the above screenshots only verify settled layout. This side conversation does not edit the shared component during that fix.

### Final fixed-slot deployment

Manager deployed frontend 002d8f2b / tree 11c15d12 via static-only switch; backend cba360ca remained running. Reopened both live forms after switch and visually inspected complete static medium/pill button and centered spacing. Login DOM: iframe 44px, heading-to-iframe and iframe-to-divider each16px, yielding visible22px gaps; no horizontal overflow. Final signup screenshot captured AND inspected: output/google-button-design-20261119/live-signup-fixed-slot.png. Manager reports exact-artifact real GIS first-load/reload four desktop/mobile tests (eight navigations) with card y/height changes zero and12 enhanced bootstrap checks PASS; deployed first-paint recheck is manager-owned. Actual OAuth round-trip limitation above remains unchanged.
