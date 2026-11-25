# Changelog

All notable changes to this project. This project adheres to semantic versioning.

## Unreleased

- Window: add regular-expression terms. Patterns that could hang a scan, like `(a+)+`, are refused
  with an explanation (a new slow-regex guard, also applied by the CLI when adding terms)
- Window: an Allowlist tab to allow and un-allow reviewed file globs; allowed hits are listed in grey
- Window: Compare scans now and shows how hits moved since the last recorded scan
- Fix: the Watchlist tab labelled regex terms as "file SHA-256"
- Offscreen GUI tests that drive the real window

## v0.2.2 — 2026-11-16

- Attach a CycloneDX SBOM to each release (covered by the signed checksums)

## v0.2.1 — 2026-11-15

- Sign release checksums with Sigstore (keyless) and attach the `.sigstore.json` bundle
- Add property/fuzz hardening tests for the AES-256-GCM + scrypt envelope

## v0.2.0 — 2026-11-14

- Read exported files as UTF-8 in tests (Windows cp1252 fix)
- Add a scan diff against the last recorded scan
- Add Markdown export of a scan
- Add CSV export of scan hits
- Add an allowlist to suppress reviewed-benign hits
- Add regex watch terms alongside keywords and hashes
- Add ignore globs to scan
- Add --json output to the scan command
- Docs: point install at the live v0.1.0 release

## v0.1.0

- Initial public release.
