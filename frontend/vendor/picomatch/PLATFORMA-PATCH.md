# Maintained picomatch patch

Owner-approved local patch for GHSA-fc5q-39xc-vjpf / CVE-2026-112366.
Upstream npm package: `picomatch@4.0.7`, MIT license retained.
Original archive SHA-512:
`qcJu88Q2IWqJsDD529JKMdwGm/dvInW4HvQnRwiH9JtihJvzGOscDtHE3x1pBKeUOTysQ8kVmLnJ2kJu7yhcGA==`.

Only `lib/parse.js` and package identity differ from the upstream source.
The guard examines the parser's existing tokens before emitting a repeated
extglob. Wildcard stars, globstars and negated extglobs inside a `+(...)` or
`*(...)` use the existing escaped-literal fallback. Escaped/quoted stars,
character classes and fixed-text extglobs retain their matching behavior.
This safeguard also applies with `maxExtglobRecursion: false`.

Compatibility boundary: formerly accepted repeated wildcard expressions such as
`+(*.js)` now match their literal text. Ordinary `**/*.js`, non-repeated negations
and fixed-text extglobs remain supported. This does not promise bounded execution
for arbitrary raw regular expressions supported by picomatch.

The root dev dependency and `$picomatch` override make every build consumer use
the committed tarball. Its integrity is pinned in `package-lock.json`. The source
is committed for review; CI compares installed runtime files with this source and
checks hostile patterns in a child process with a deadline. The normal npm audit
remains enabled, but cannot independently audit this private local fork.

Repack after a reviewed source change from this directory:
`npm pack --ignore-scripts --pack-destination ..`.
Then regenerate the root lock, run `node --test scripts/tests/picomatch-security.test.mjs`,
build the application/widget, verify the bundle budget and run the dependency audit.
Replace the override with an upstream release only after it passes these regressions.

Advisory: https://github.com/advisories/GHSA-fc5q-39xc-vjpf
