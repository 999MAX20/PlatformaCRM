# Public CRM landing

The owner-supplied `Platforma_CRM_landing_source/dist` was imported on 2026-11-06.
Maintained source is now `frontend/public/landing`; the sibling folder is not a build dependency.
Edit its HTML/CSS/JS directly. Assets, local fonts and legal downloads are included.
Legal documents retain their draft status; importing them is not legal approval.
The marketing site deliberately targets dentistry; authenticated CRM terminology is unchanged.

`npm run dev`, `npm run build` and `npm run preview` use the ordinary frontend pipeline.
The build copies public assets to `dist/landing`. `dist/index.html` remains the React SPA.
`plugin.ts` maps exact `/` and `/index.html` to the landing in dev/preview.
The production edge must use the equivalent handlers in `deploy/stand-access/Caddyfile`:
landing home first, `/landing/*` static files next, SPA fallback last.
A generic host that serves only `dist/index.html` at `/` will show the SPA instead.
React navigation to `/` reloads the separate landing document through LandingHome.

Sign-in links target `/login` and carry the chosen RU/KK/EN locale through
`ai_smb_language`. Landing pages retain `platforma-crm-language` and `?lang=`.
Digital links use `https://platformadigital.kz/`; contact links open the selected
external client and do not submit a server-side lead form.

The existing protected stand gate precedes every landing handler. This change
neither deploys nor makes the stand public. API, tenant authorization and MFA remain unchanged.
Verification and hosting proposal: [evidence](../../docs/testing/evidence/crm-landing-integration-20261106.md).
