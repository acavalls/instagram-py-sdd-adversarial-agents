# Cycle 8 audit findings — carried forward

Date: 2026-11-08. Audit verdict: LIGHT DRIFT. Cycle closed by the Sheriff
("cerramos") with the findings below documented. Cycle 8
(2026-11-08-08-style-auth-screens) was a feature change — the auth screens
were restyled with the brand fonts (Grand Hotel + Inter) and brand gradient,
and the visible product name was rebranded from "django_ig" to "Instagram".
The audit verified the new surface fully in sync: fonts link exactly once
per auth page and never elsewhere, the brand gradient confined to auth,
no user-visible "django_ig" anywhere, config claims exact. All carried
findings from cycles 1-7 remain resolved and in sync. Six low findings
remain open (three carried from cycle 7, three new).

| ID    | Type      | Severity | Summary                                                                                                                                          | Recommendation |
| ----- | --------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| C7-01 | TESTS     | low      | The social twin scenario "Topbar links to own profile" still lacks a scenario-named test (behavior covered by the web-ui twin test; 139/140 scenarios traceable) | Add a thin scenario-named alias, or fold the twin scenario into the web-ui one |
| C7-02 | SPEC→CODE | low      | Session-wins-over-foreign-JWT precedence and CSRF enforcement on session-authenticated unsafe methods are attack-pinned but undeclared | Declare precedence + CSRF in the session-fallback requirement |
| C7-03 | SPEC→CODE | low      | Anonymous API requests rejected 403 without a WWW-Authenticate challenge; spec-silent | Declare the surface, or escalate if a 401 + Bearer challenge is wanted |
| C8-01 | PROCESS   | low      | Cycle-8 Bad overran both budgets (8/6 runs, 8/6 min, own fixture bugs) and the final brand-naming group was verified by full suite + Ugly instead of pausing; the honest reporting was correct but the STOP-and-ask rule was substituted | Regularize the post-exhaustion practice (orchestrator full-suite verification) or enforce STOP strictly |
| C8-02 | TESTS     | low (in doubt) | The footer scenario test pins the footer's ABSENCE on non-feed authenticated pages — consistent with the archived rescope but spec-silent | Add "and only on the home feed" to the footer clause |
| C8-03 | SPEC→CODE | low (in doubt) | "Any page of the application" literally reaches Swagger ("Instagram API" title) and admin ("Django administration"), neither of which ends with "· Instagram" | Narrow the scenario to "any page of the web UI" (recommended) or extend branding to Swagger/admin |

Sandbox/verification caveats (not drift): visual rendering (the CSS-generated
wordmark is asserted via stylesheet content, not the DOM), real-browser HTMX
behavior, interactive Swagger UI/admin flows, JWT cryptography and real
elapsed-time expiry, true parallelism (2 thread-race tests skip honestly),
production deployment, real filesystem media storage and offline font
fallback rendering remain unverified.

Project state after cycle 8: 8/8 changes implemented, verified, archived and
audited. Living specs: user-accounts 8 req/34 scen, posts 8/31, social 6/25,
stories 6/21, web-ui 7 req/23 scen, api-docs 1/2, admin-console 1/4 (140
scenarios; 139/140 scenario-named tested). Suite: 539 passed, 2 skipped, 0
xfails, coverage 99.16%. Auth screens ship the brand fonts and gradient;
the product is branded "Instagram" everywhere user-visible.
