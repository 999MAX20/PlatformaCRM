# Google button appearance and spacing, 19 November 2026

Scope: user chose white rounded official Google button on login/signup, centered on the form axis; then requested equal top/bottom gaps. Source base a932b58a. No auth behavior, business data or deployment changes.

Changed shared Google renderer to outline/large/pill with official left-aligned G; centered the mount and loading label. Preserved 44px reserved mount, nonce renewal, static label, disabled/retry/callback behavior. Shared social-row top margin and divider margin are 16px; including mount inset, measured visible button gaps are 18px above and below.

Checks: npm --prefix frontend run build PASS after final CSS edit (i18n, TypeScript, Vite app/widget); eight token-csrf Node tests PASS; scoped diff hygiene PASS. Full CI not required for this local styling change.

Chrome extension inspection used real Google SDK with a synthetic preview API on 127.0.0.1:18590, no login/registration supported by preview. Desktop and 390x844 mobile login/signup screenshots captured and inspected. Equal vertical gaps:18px. Desktop login horizontal gaps11.20px/11.20px; signup120.875px/120.888px (subpixel rounding). Mobile login0.40px/0.40px; signup0.30px/0.30px relative to form content. No page horizontal overflow. Official G and full Russian label visible. Keyboard Shift+Tab from email reaches Google button and shows focus outline. No new live OAuth sign-in is claimed.

Applied Anti Slop during, UI/human/layoutmobile: scoped geometry, official logo, responsive width, keyboard focus PASS. Provider-controlled official outline/40px button retained; SDK styling is not overridden to impose a different border/tap height. Existing reserved mount remains44px. No new motion, copy, assets or dialogs. Other locales and a full live OAuth round trip were not rerun for presentation-only options.

Screenshots and build log: output/google-button-design-20261119/. Existing unrelated WIP is excluded from this change. Local preview remains available for owner review; no server deployment performed.
