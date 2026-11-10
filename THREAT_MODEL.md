# Threat model — ENVY SkyWatch

What ENVY SkyWatch (watchlists and offline content scanning) protects, and — just as importantly — what it does **not**. Read this
before trusting it with anything whose exposure would actually harm you.

## What it protects

- **Confidentiality and integrity of your data at rest.** Everything is sealed with
  **AES-256-GCM** (authenticated encryption) under a **256-bit key derived from your
  passphrase with scrypt** (`n=2^15, r=8, p=1`). Each write uses a **fresh random 16-byte
  salt and 12-byte nonce**, and the envelope header is bound in as AEAD *associated data*,
  so a truncated or altered file fails to decrypt rather than returning wrong data.
- **Tamper-evidence of the event history.** Changes are appended to a **SHA-256
  hash-chained journal**: editing or reordering past entries breaks the chain and is
  detectable.
- **No silent overwrites.** Every change writes a **new file** (revision-preserving); the
  previous revision is never overwritten in place.
- **No remote exposure from the app itself.** It is **offline by construction** — no
  network, no accounts, no telemetry — so the application has no path to exfiltrate your
  data.

## What it does NOT protect against

- **A weak passphrase.** scrypt raises the cost of guessing, but it cannot save a passphrase
  a motivated attacker with a GPU can brute-force. Choose a long, high-entropy passphrase.
  **There is no recovery** — lose it and the data is unrecoverable, by design.
- **A compromised machine.** If your computer is running malware, a keylogger can capture
  your passphrase and memory-scraping or screen capture can read plaintext while a file is
  open. The passphrase and decrypted data necessarily live in RAM while you're using them.
- **Metadata.** The encrypted file's size roughly reveals the plaintext size, and
  filenames, file timestamps, and the number of records/revisions may be visible on disk.
- **Residual plaintext.** It is **not a secure-delete tool.** Original plaintext you
  imported, earlier copies, OS swap, and freed disk space may still hold recoverable data.
  Deleting the app's files does not wipe them from the drive.
- **Supply-chain and dependency trust.** It relies on the `cryptography` library (OpenSSL),
  CPython, and Qt/PyQt6; a compromise in those is outside its control.
- **Sophisticated side-channel or physical attacks.** It is not hardened against timing,
  power, cold-boot, or coercion ("rubber-hose") attacks.
- **Identity.** The hash chain proves the *order and integrity* of records, **not who wrote
  them.** There are no per-entry digital signatures or user authentication.

## Specific to ENVY SkyWatch

- **A "hit" is a literal match (keyword, regex, or file hash) — presence, not significance.** Matching is not fuzzy or semantic; binary and unreadable files are skipped for keyword scanning (still hashed). Scan times are assertions from your clock.

## Reporting

Found a way the protections above fail short of what's described here? That's a security
issue — see **[SECURITY.md](SECURITY.md)**.
