# Security Policy

AI Tabletop World Builder is a security-training platform, so we take
vulnerabilities in it seriously. Thank you for helping keep its users safe.

## Supported versions

Security fixes are released for the latest minor version. Older versions do not
receive backports; please upgrade.

| Version | Supported |
|---------|-----------|
| 1.x (latest release) | Yes |
| < 1.0 | No |

## Reporting a vulnerability

**Please do not open a public issue, pull request, or discussion for a
security problem.**

Report it privately through GitHub:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability** to open a private security advisory.

Include as much of the following as you can:

- The affected version, commit, or container image tag
- The component (API endpoint, Streamlit page, Docker Compose setup, …)
- Steps to reproduce, or a proof of concept
- The impact you expect (data exposure, privilege escalation, SSRF, …)
- Any configuration that matters (for example `REQUIRE_AUTH`, database type)

## What to expect

- We acknowledge a report within **3 business days**.
- We aim to confirm the issue and share a remediation plan within
  **10 business days**.
- We coordinate a disclosure date with you. By default we publish an advisory
  when a fixed release is available, and no later than 90 days after the report.
- We credit reporters in the advisory unless you ask us not to.

## Scope

In scope: the code in this repository and the container images published from
it (`ghcr.io/ap6pack/ai-tabletop-api`, `ghcr.io/ap6pack/ai-tabletop-frontend`).

Out of scope:

- Findings that need `REQUIRE_AUTH=false` (development mode, where the API is
  intentionally open) or a deliberately weakened configuration
- Content produced by an LLM provider itself, unless the platform fails to apply
  its documented content policy or prompt-injection protections
- Vulnerabilities in third-party dependencies without a demonstrated impact on
  this project (please report those upstream; the weekly `pip-audit` scan in CI
  tracks known vulnerabilities in our pinned dependencies)
- Denial of service through sheer request volume

## Safe harbor

We will not pursue legal action against anyone who researches and reports a
vulnerability in good faith, avoids privacy violations and data destruction,
does not degrade services for others, and gives us reasonable time to fix the
issue before disclosing it.
