# Security Policy

ENVY SkyWatch is an independent, open-source project. It handles data you consider
sensitive, so security reports are taken seriously and handled in good faith.

## Reporting a vulnerability

**Please report security issues privately — do not open a public issue with exploit
details.**

- Preferred: use GitHub's **“Report a vulnerability”** button on this repository's
  [Security tab](https://github.com/xzchick/envy-skywatch/security) (private vulnerability
  reporting is enabled). This opens a private advisory only the maintainer can see.
- If that is unavailable to you, open a normal issue that says only *“I’d like a private
  channel to report a security issue”* — without any details — and you'll get one.

Please include enough to reproduce: version, OS, steps, and the impact you observed.

## What to expect

This is a solo-maintained project with no bug-bounty programme. Reports are handled on a
best-effort basis: acknowledgement as soon as reasonably possible, a fix or mitigation for
confirmed issues, and coordinated disclosure — please allow up to **90 days** before
public disclosure, and credit is gladly given unless you prefer otherwise.

## Supported versions

Only the latest released version receives security fixes.

| Version | Supported |
|---|---|
| latest `0.x` release | ✅ |
| older | ❌ (please upgrade) |

## Scope

**In scope:** this application's own code, and how it uses cryptography — key derivation,
the encryption envelope, the integrity/journal design, file handling, and input parsing.

**Out of scope (report upstream):** vulnerabilities in dependencies such as
[`cryptography`](https://github.com/pyca/cryptography)/OpenSSL, CPython, or Qt/PyQt6; and
attacks that assume an already-compromised host or physical access — these are described,
not treated as app bugs, in [THREAT_MODEL.md](THREAT_MODEL.md). If you're unsure, report it
anyway and we'll triage together.

See **[THREAT_MODEL.md](THREAT_MODEL.md)** for exactly what ENVY SkyWatch does and does not
protect against.
