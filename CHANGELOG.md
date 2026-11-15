# Changelog

All notable changes to this project. This project adheres to semantic versioning.

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
