"""Encrypted watchlists and offline content scanning: watch for what matters.

A self-contained engine for the ENVY BLACK VEIL SkyWatch app, packaged as a
standalone app. A *watchlist* holds *terms* to watch for — a case-insensitive
literal keyword, or a file's SHA-256 — sealed in the same AES-256-GCM envelope as
ENVY Vault. A *scan* reads a file or a folder of files and reports every hit: the
term, the file, the line number and a trimmed context snippet (for keywords), or
the matching file (for hashes). Recording a scan appends a summary to a SHA-256
hash-chained journal and writes a new, preserved revision.

Honest by design: a hit is a literal match, not a verdict — it means the term
appeared, not that it matters. Matching is case-insensitive substring, not regex,
fuzzy or semantic. It reads only text it can decode; binary and unreadable files
are skipped for keywords (still hashed for hash terms). Times are assertions from
the machine's clock, and nothing is sent.

Standard library only, apart from ``cryptography`` for the encrypted envelope.
"""

from __future__ import annotations

import datetime
import hashlib
import html
import json
import os
import stat
import uuid
from pathlib import Path

# --- Shared errors and bounds ------------------------------------------------

MAGIC = b"ENVYVAULT2\x00"
MAX_ENVELOPE = 16 * 1024 * 1024        # the encrypted watchlist
MAX_TERMS = 2000
MAX_JOURNAL = 100000
MAX_REVISIONS = 1000000
MIN_PASSPHRASE = 12
MAX_FILES = 50000
MAX_FILE_BYTES = 16 * 1024 * 1024      # per-file ceiling for scanning
MAX_HITS = 50000                        # overall cap per scan
MAX_HITS_PER_TERM_FILE = 1000
CONTEXT = 120                           # characters of context around a keyword hit
CHUNK = 1024 * 1024
KINDS = ("text", "sha256")
SEVERITIES = ("low", "medium", "high")


class SkyWatchError(RuntimeError):
    """A clean, expected error: a bad passphrase, an invalid watchlist, a chain mismatch."""


# --- Safe file primitives (never follow symlinks, never overwrite) -----------

def read_regular(path, limit: int = MAX_ENVELOPE) -> bytes:
    path = Path(path).expanduser()
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        meta = os.fstat(stream.fileno())
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > limit:
            raise SkyWatchError("Expected a regular file within the size limit")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise SkyWatchError("File exceeded the size limit")
    return data


def new_file(path, data: bytes, mode: int = 0o600) -> Path:
    """Write a brand-new file. O_EXCL means an existing file is never overwritten."""
    path = Path(path).expanduser()
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except FileExistsError:
        raise SkyWatchError(f"Refusing to overwrite an existing file: {path}") from None
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return path


# --- Encrypted envelope (byte-compatible with ENVY Vault) --------------------

def _key(secret: bytes, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    return Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1).derive(secret)


def encrypt_bytes(data: bytes, secret: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, nonce = os.urandom(16), os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_key(secret, salt)).encrypt(nonce, data, MAGIC)


def decrypt_bytes(data: bytes, secret: bytes) -> bytes:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if not data.startswith(MAGIC) or len(data) < len(MAGIC) + 44:
        raise SkyWatchError("Not an ENVY encrypted envelope")
    blob = data[len(MAGIC):]
    try:
        return AESGCM(_key(secret, blob[:16])).decrypt(blob[16:28], blob[28:], MAGIC)
    except InvalidTag:
        raise SkyWatchError("Incorrect passphrase or modified encrypted data") from None


def check_passphrase(secret: bytes) -> bytes:
    if not isinstance(secret, (bytes, bytearray)) or len(secret) < MIN_PASSPHRASE:
        raise SkyWatchError(f"Use a passphrase of at least {MIN_PASSPHRASE} bytes")
    return bytes(secret)


# --- Canonical form and field validation -------------------------------------

def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _timestamp(value, field="recorded_utc"):
    if not isinstance(value, str) or len(value) > 64:
        raise SkyWatchError("Invalid " + field)
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SkyWatchError(field + " must be ISO 8601 with a UTC offset") from None
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        raise SkyWatchError(field + " must be expressed in UTC")
    return parsed.isoformat()


def _sha256(value, field="sha256"):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SkyWatchError(field + " must be 64 lowercase hexadecimal characters")
    return value


def _text(value, field="text", limit=200, allow_empty=False):
    if not isinstance(value, str) or "\x00" in value or len(value) > limit:
        raise SkyWatchError("Invalid " + field)
    if not allow_empty and not value.strip():
        raise SkyWatchError("Invalid " + field)
    return value


def _uuid(value, field="identifier"):
    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        raise SkyWatchError("Invalid " + field) from None
    return value


def _choice(value, allowed, field):
    if value not in allowed:
        raise SkyWatchError(f"{field} must be one of {', '.join(allowed)}")
    return value


# --- Term and journal validation ---------------------------------------------

def _validate_term(value):
    if not isinstance(value, dict) or set(value) != {"id", "label", "pattern", "kind", "severity", "created_utc"}:
        raise SkyWatchError("Invalid watch term")
    kind = _choice(value["kind"], KINDS, "Kind")
    pattern = value["pattern"]
    pattern = _sha256(pattern, "hash pattern") if kind == "sha256" else _text(pattern, "pattern", 200)
    return {"id": _uuid(value["id"], "term id"),
            "label": _text(value["label"], "label", 200),
            "pattern": pattern, "kind": kind,
            "severity": _choice(value["severity"], SEVERITIES, "Severity"),
            "created_utc": _timestamp(value["created_utc"], "created_utc")}


def _validate_scan_summary(value):
    allowed = {"scanned_utc", "target", "files_scanned", "files_skipped", "hits", "high", "medium", "low"}
    if not isinstance(value, dict) or set(value) != allowed:
        raise SkyWatchError("Invalid scan summary")
    _timestamp(value["scanned_utc"], "scanned_utc")
    out = {"scanned_utc": value["scanned_utc"], "target": _text(value["target"], "target", 4096)}
    for key in ("files_scanned", "files_skipped", "hits", "high", "medium", "low"):
        count = value[key]
        if type(count) is not int or count < 0:
            raise SkyWatchError("Scan counts must be non-negative integers")
        out[key] = count
    return out


def _record_digest(record):
    core = {k: v for k, v in record.items() if k != "record_sha256"}
    return hashlib.sha256(_canonical(core)).hexdigest()


def _validate_record(value):
    fields = {"recorded_utc", "scan", "previous_sha256", "record_sha256"}
    if not isinstance(value, dict) or set(value) != fields:
        raise SkyWatchError("Invalid journal record")
    return {"recorded_utc": _timestamp(value["recorded_utc"]),
            "scan": _validate_scan_summary(value["scan"]),
            "previous_sha256": _sha256(value["previous_sha256"], "previous_sha256"),
            "record_sha256": _sha256(value["record_sha256"], "record_sha256")}


def _validate_watchlist(data):
    fields = {"schema", "watch_id", "title", "created_utc", "revision",
              "previous_envelope_sha256", "terms", "journal"}
    if not isinstance(data, dict) or set(data) != fields or type(data["schema"]) is not int or data["schema"] != 1:
        raise SkyWatchError("Unsupported encrypted watchlist schema")
    _text(data["title"], "watchlist title", 200)
    _uuid(data["watch_id"], "watchlist identifier")
    _timestamp(data["created_utc"], "created_utc")

    terms = data["terms"]
    if not isinstance(terms, list) or len(terms) > MAX_TERMS:
        raise SkyWatchError("Invalid term list")
    seen, previous_id = set(), None
    for term in terms:
        if _validate_term(term) != term:
            raise SkyWatchError("Term is not normalized")
        if term["id"] in seen:
            raise SkyWatchError("Duplicate term id")
        if previous_id is not None and term["id"] < previous_id:
            raise SkyWatchError("Terms must be sorted by id")
        seen.add(term["id"]); previous_id = term["id"]

    journal = data["journal"]
    if not isinstance(journal, list) or len(journal) > MAX_JOURNAL:
        raise SkyWatchError("Invalid journal")
    previous = "0" * 64
    for record in journal:
        if _validate_record(record) != record:
            raise SkyWatchError("Journal record is not normalized")
        if record["previous_sha256"] != previous or _record_digest(record) != record["record_sha256"]:
            raise SkyWatchError("Watchlist journal hash chain mismatch")
        previous = record["record_sha256"]

    revision = data["revision"]
    if type(revision) is not int or not 0 <= revision <= MAX_REVISIONS:
        raise SkyWatchError("Invalid revision")
    _sha256(data["previous_envelope_sha256"], "previous_envelope_sha256")
    return data


# --- Load / write ------------------------------------------------------------

def _load(source, secret):
    encrypted = read_regular(source, MAX_ENVELOPE)
    try:
        data = json.loads(decrypt_bytes(encrypted, secret))
    except (json.JSONDecodeError, UnicodeError, RecursionError):
        raise SkyWatchError("Encrypted watchlist does not contain valid JSON") from None
    return _validate_watchlist(data), hashlib.sha256(encrypted).hexdigest()


def _write(destination, data, secret):
    check_passphrase(secret)
    encoded = _canonical(_validate_watchlist(data))
    if len(encoded) + 128 > MAX_ENVELOPE:
        raise SkyWatchError("Watchlist exceeds the encrypted size limit")
    new_file(destination, encrypt_bytes(encoded, secret))
    return {"output": str(destination), "watch_id": data["watch_id"], "revision": data["revision"],
            "terms": len(data["terms"]), "encrypted": True, "previous_revision_preserved": True}


def _save_revision(data, previous_envelope, destination, secret):
    data["revision"] += 1
    data["previous_envelope_sha256"] = previous_envelope
    return _write(destination, data, secret)


def create(destination, title, secret):
    data = {"schema": 1, "watch_id": str(uuid.uuid4()), "title": _text(title, "watchlist title", 200),
            "created_utc": _utc(), "revision": 0, "previous_envelope_sha256": "0" * 64,
            "terms": [], "journal": []}
    return _write(destination, data, secret)


# --- Mutations (each writes a new, preserved revision) -----------------------

def add_term(source, destination, secret, label, pattern, kind="text", severity="medium"):
    data, envelope = _load(source, secret)
    if len(data["terms"]) >= MAX_TERMS:
        raise SkyWatchError(f"A watchlist holds at most {MAX_TERMS} terms")
    pattern = pattern.lower() if kind == "sha256" else pattern
    term = _validate_term({"id": str(uuid.uuid4()), "label": label, "pattern": pattern,
                           "kind": kind, "severity": severity, "created_utc": _utc()})
    data["terms"] = sorted(data["terms"] + [term], key=lambda t: t["id"])
    result = _save_revision(data, envelope, destination, secret)
    return dict(result, term_id=term["id"])


def remove_term(source, destination, secret, term_id):
    data, envelope = _load(source, secret)
    term_id = _uuid(term_id, "term id")
    kept = [t for t in data["terms"] if t["id"] != term_id]
    if len(kept) == len(data["terms"]):
        raise SkyWatchError("No such term in this watchlist")
    data["terms"] = kept
    result = _save_revision(data, envelope, destination, secret)
    return dict(result, removed_term=term_id)


# --- Scanning ----------------------------------------------------------------

def _iter_files(target):
    target = Path(target).expanduser()
    if target.is_file():
        yield target
        return
    if not target.is_dir():
        raise SkyWatchError("The scan target must be an existing file or directory")
    count = 0
    for dirpath, dirnames, filenames in os.walk(target, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            full = Path(dirpath) / name
            try:
                meta = full.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(meta.st_mode):
                continue  # skip symlinks, sockets, devices
            count += 1
            if count > MAX_FILES:
                raise SkyWatchError(f"More than {MAX_FILES} files under the target; narrow the scope")
            yield full


def _read_for_scan(path):
    """Return (sha256, text_or_None, skipped_reason). Text is None for binary/oversize/unreadable."""
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None, None, "unreadable"
    try:
        with os.fdopen(fd, "rb") as stream:
            meta = os.fstat(stream.fileno())
            if not stat.S_ISREG(meta.st_mode):
                return None, None, "not a regular file"
            if meta.st_size > MAX_FILE_BYTES:
                return None, None, "too large"
            data = stream.read(MAX_FILE_BYTES + 1)
    except OSError:
        return None, None, "unreadable"
    digest = hashlib.sha256(data).hexdigest()
    if b"\x00" in data:
        return digest, None, "binary"
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        return digest, None, "undecodable"
    return digest, text, None


def _scan_text(text, needle_lower):
    hits = []
    for lineno, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if needle_lower in low:
            idx = low.index(needle_lower)
            start = max(0, idx - CONTEXT // 2)
            snippet = line[start:start + CONTEXT].strip()
            if start > 0:
                snippet = "…" + snippet
            hits.append((lineno, snippet))
            if len(hits) >= MAX_HITS_PER_TERM_FILE:
                break
    return hits


def scan(source, secret, target):
    """Scan a file or folder against the watchlist. Read-only. Returns detailed hits."""
    data, _ = _load(source, secret)
    terms = data["terms"]
    text_terms = [t for t in terms if t["kind"] == "text"]
    hash_terms = [t for t in terms if t["kind"] == "sha256"]
    root = Path(target).expanduser()
    hits, files_scanned, files_skipped, truncated = [], 0, 0, False
    for path in _iter_files(target):
        digest, text, skipped = _read_for_scan(path)
        rel = _rel(path, root)
        if digest is None:
            files_skipped += 1
            continue
        files_scanned += 1
        for term in hash_terms:
            if term["pattern"] == digest:
                hits.append({"term_id": term["id"], "label": term["label"], "severity": term["severity"],
                             "kind": "sha256", "file": rel, "line": 0, "context": digest})
        if text is not None:
            needles = {t["id"]: t["pattern"].lower() for t in text_terms}
            for term in text_terms:
                for lineno, snippet in _scan_text(text, needles[term["id"]]):
                    hits.append({"term_id": term["id"], "label": term["label"], "severity": term["severity"],
                                 "kind": "text", "file": rel, "line": lineno, "context": snippet})
                    if len(hits) >= MAX_HITS:
                        truncated = True
                        break
                if truncated:
                    break
        if truncated:
            break
    order = {"high": 0, "medium": 1, "low": 2}
    hits.sort(key=lambda h: (order[h["severity"]], h["file"], h["line"]))
    by_sev = {s: sum(1 for h in hits if h["severity"] == s) for s in SEVERITIES}
    return {"watch_id": data["watch_id"], "title": data["title"], "revision": data["revision"],
            "target": str(root), "scanned_utc": _utc(), "files_scanned": files_scanned,
            "files_skipped": files_skipped, "hits": hits, "hit_count": len(hits), "truncated": truncated,
            "by_severity": by_sev, "clean": not hits,
            "basis": "A hit is a literal, case-insensitive match — it means the term appeared, not that it "
                     "matters. Matching is not regex, fuzzy or semantic, and skipped files were not searched."}


def _rel(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def record_scan(source, destination, secret, target):
    """Run a scan and append its summary to the journal as a new revision."""
    data, envelope = _load(source, secret)
    report = scan(source, secret, target)
    summary = {"scanned_utc": report["scanned_utc"], "target": report["target"],
               "files_scanned": report["files_scanned"], "files_skipped": report["files_skipped"],
               "hits": report["hit_count"], "high": report["by_severity"]["high"],
               "medium": report["by_severity"]["medium"], "low": report["by_severity"]["low"]}
    record = {"recorded_utc": _utc(), "scan": _validate_scan_summary(summary),
              "previous_sha256": data["journal"][-1]["record_sha256"] if data["journal"] else "0" * 64}
    record["record_sha256"] = _record_digest(record)
    data["journal"].append(_validate_record(record))
    result = _save_revision(data, envelope, destination, secret)
    return dict(result, recorded_scan=summary)


def inspect(source, secret):
    data, envelope = _load(source, secret)
    return {"watch_id": data["watch_id"], "title": data["title"], "revision": data["revision"],
            "created_utc": data["created_utc"], "envelope_sha256": envelope,
            "terms": data["terms"],
            "journal": [{"recorded_utc": r["recorded_utc"], **r["scan"]} for r in data["journal"]],
            "warning": "A hit is a literal match, not a verdict. The journal is append-only and hash-chained, "
                       "so scan summaries cannot be reordered or edited without breaking the chain — but the "
                       "chain does not prove when a scan ran, and skipped files were never searched."}


# --- Plaintext export --------------------------------------------------------

def export(source, destination, secret, format="html", target=None):
    if format not in ("html", "json"):
        raise SkyWatchError("Export format must be html or json")
    data, envelope = _load(source, secret)
    if target is None:
        raise SkyWatchError("Export needs a scan target (a file or folder to scan)")
    report = scan(source, secret, target)
    out = {"watchlist": {"watch_id": data["watch_id"], "title": data["title"], "revision": data["revision"],
                         "created_utc": data["created_utc"]},
           "scanned_utc": report["scanned_utc"], "target": report["target"], "clean": report["clean"],
           "files_scanned": report["files_scanned"], "files_skipped": report["files_skipped"],
           "by_severity": report["by_severity"], "hits": report["hits"], "truncated": report["truncated"],
           "envelope_sha256": envelope,
           "limitations": "Plaintext export. A hit is a literal, case-insensitive match, not a verdict; "
                          "matching is not regex, fuzzy or semantic; skipped files were not searched, and "
                          "times are assertions from the operator's clock."}
    if format == "json":
        output = (json.dumps(out, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    else:
        def esc(v):
            return html.escape(str(v), quote=True)

        body = "".join(
            "<tr><td>" + esc(h["severity"]) + "</td><td>" + esc(h["label"]) + "</td><td>" + esc(h["kind"]) +
            "</td><td>" + esc(h["file"]) + "</td><td>" + (esc(h["line"]) if h["kind"] == "text" else "—") +
            "</td><td><code>" + esc(h["context"]) + "</code></td></tr>" for h in report["hits"])
        verdict = "CLEAN — no hits" if report["clean"] else \
            f"{report['hit_count']} hit(s): {report['by_severity']['high']} high, " \
            f"{report['by_severity']['medium']} medium, {report['by_severity']['low']} low"
        # No external content, executable script, clickable operator-supplied URLs, or active HTML.
        output = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
                  "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
                  "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                  "<title>" + esc(data["title"]) + "</title><style>body{max-width:78rem;margin:2rem auto;padding:0 1rem;font:16px system-ui;line-height:1.5}"
                  "table{border-collapse:collapse;width:100%;margin:0 0 2rem}th,td{border:1px solid #777;padding:.4rem .6rem;text-align:left;vertical-align:top}"
                  "th{background:#eee}code{word-break:break-all;font-size:.85em}</style></head><body><h1>" + esc(data["title"]) +
                  "</h1><p>" + esc(out["limitations"]) + "</p><p>Watchlist: " + esc(data["watch_id"]) +
                  " · Revision: " + str(data["revision"]) + " · Target: " + esc(report["target"]) +
                  "</p><p>Scanned UTC: " + esc(report["scanned_utc"]) + " · Files scanned: " + str(report["files_scanned"]) +
                  " · Skipped: " + str(report["files_skipped"]) + " · Encrypted watchlist SHA-256: " + envelope +
                  "</p><h2>" + verdict + "</h2>"
                  "<table><thead><tr><th>Severity</th><th>Term</th><th>Kind</th><th>File</th><th>Line</th>"
                  "<th>Context</th></tr></thead><tbody>" + body + "</tbody></table>"
                  + ("<p>Results were truncated at the hit limit.</p>" if report["truncated"] else "") +
                  "</body></html>").encode("utf-8")
    new_file(destination, output)
    return {"output": str(destination), "format": format, "plaintext": True,
            "sha256": hashlib.sha256(output).hexdigest(),
            "clean": report["clean"], "hit_count": report["hit_count"]}
