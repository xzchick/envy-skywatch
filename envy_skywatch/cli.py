"""Command-line entry point. The SkyWatch window is the default.

Scans are read-only; every mutation (adding a term, removing a term, recording a
scan) writes a brand-new watchlist revision and never overwrites the previous one.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys

from . import __version__
from .core import (KINDS, SEVERITIES, SkyWatchError, add_term, allow, check_passphrase,
                   create, diff_scan, export, inspect, record_scan, remove_term, scan, unallow)


def build_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="envy-skywatch",
        description="Encrypted watchlists and offline content scanning — watch for what matters. Keep terms "
                    "(keywords or file hashes), scan a file or folder, and get every hit with its file, line "
                    "and context. Run with no arguments to open the window. Local only: no network, no accounts.")
    root.add_argument("--version", action="version", version=f"envy-skywatch {__version__}")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("gui", help="open the SkyWatch window (default)")

    new = commands.add_parser("init", help="create a new, empty encrypted watchlist")
    new.add_argument("destination", help="a new watchlist file; never overwritten")
    new.add_argument("--title", required=True, help="a name for this watchlist")

    add = commands.add_parser("add", help="add a watch term (writes a new revision)")
    add.add_argument("watchlist")
    add.add_argument("destination", help="a new watchlist file; never overwritten")
    add.add_argument("--label", required=True, help="a name for this term")
    add.add_argument("--pattern", required=True,
                     help="a keyword (text), a regular expression (regex), or a 64-hex SHA-256 (sha256)")
    add.add_argument("--kind", default="text", choices=KINDS)
    add.add_argument("--severity", default="medium", choices=SEVERITIES)

    rm = commands.add_parser("remove", help="remove a term (writes a new revision)")
    rm.add_argument("watchlist")
    rm.add_argument("destination", help="a new watchlist file; never overwritten")
    rm.add_argument("--term", required=True, help="the term id")

    al = commands.add_parser("allow", help="mark a file glob as reviewed-benign (writes a new revision)")
    al.add_argument("watchlist")
    al.add_argument("destination", help="a new watchlist file; never overwritten")
    al.add_argument("--pattern", required=True, metavar="GLOB",
                    help="hits in files matching this glob are reported as allowed, not as alerts")

    ual = commands.add_parser("unallow", help="remove a glob from the allowlist (writes a new revision)")
    ual.add_argument("watchlist")
    ual.add_argument("destination", help="a new watchlist file; never overwritten")
    ual.add_argument("--pattern", required=True, metavar="GLOB")

    sc = commands.add_parser("scan", help="scan a file or folder (read-only; exit 1 if any hits)")
    sc.add_argument("watchlist")
    sc.add_argument("target", help="a file or folder to scan")
    sc.add_argument("--json", action="store_true", help="emit the full hit report as JSON")
    sc.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                    help="skip paths matching this glob (repeatable, .gitignore-style)")

    rec = commands.add_parser("record", help="scan and append the summary to the journal (new revision)")
    rec.add_argument("watchlist")
    rec.add_argument("destination", help="a new watchlist file; never overwritten")
    rec.add_argument("target", help="a file or folder to scan")

    df = commands.add_parser("diff", help="scan and compare against the last recorded scan "
                                          "(read-only; exit 1 only if hits increased)")
    df.add_argument("watchlist")
    df.add_argument("target", help="a file or folder to scan")
    df.add_argument("--json", action="store_true", help="emit the full diff as JSON")
    df.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                    help="skip paths matching this glob (repeatable, .gitignore-style)")

    insp = commands.add_parser("inspect", help="print the decrypted watchlist and journal (read-only)")
    insp.add_argument("watchlist")

    exp = commands.add_parser("export", help="scan and write a plaintext HTML or JSON report")
    exp.add_argument("watchlist")
    exp.add_argument("destination", help="a new report file; never overwritten")
    exp.add_argument("target", help="a file or folder to scan")
    exp.add_argument("--format", default="html", choices=("html", "json", "csv", "md"))
    return root


def _passphrase(confirm: bool = False) -> bytes:
    if not sys.stdin.isatty():
        raise SkyWatchError("Open this action in a terminal so the passphrase is not echoed")
    value = getpass.getpass("Watchlist passphrase: ").encode()
    if confirm and value != getpass.getpass("Repeat passphrase: ").encode():
        raise SkyWatchError("Passphrases do not match")
    return check_passphrase(value)


def _run(args) -> int:
    if args.command == "init":
        result = create(args.destination, args.title, _passphrase(confirm=True))
        print(f"watchlist created → {result['output']} (revision 0)")
        return 0
    if args.command == "add":
        result = add_term(args.watchlist, args.destination, _passphrase(), args.label,
                          args.pattern, args.kind, args.severity)
        print(f"term added {result['term_id']} → {result['output']} (revision {result['revision']})")
        return 0
    if args.command == "remove":
        result = remove_term(args.watchlist, args.destination, _passphrase(), args.term)
        print(f"removed {result['removed_term']} → {result['output']} (revision {result['revision']})")
        return 0
    if args.command == "allow":
        result = allow(args.watchlist, args.destination, _passphrase(), args.pattern)
        print(f"allowlisted “{args.pattern}” ({len(result['allowlist'])} total) → {result['output']} "
              f"(revision {result['revision']})")
        return 0
    if args.command == "unallow":
        result = unallow(args.watchlist, args.destination, _passphrase(), args.pattern)
        print(f"removed “{args.pattern}” from the allowlist → {result['output']} (revision {result['revision']})")
        return 0
    if args.command == "scan":
        report = scan(args.watchlist, _passphrase(), args.target, ignore=args.ignore)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["clean"] else 1
        for h in report["hits"]:
            where = h["file"] if h["kind"] == "sha256" else f"{h['file']}:{h['line']}"
            print(f"  [{h['severity']:>6}] {h['label']}  {where}  {h['context']}")
        s = report["by_severity"]
        allowed = f", {report['allowed_count']} allowed" if report["allowed_count"] else ""
        print(f"scanned {report['files_scanned']} files ({report['files_skipped']} skipped) — "
              f"{report['hit_count']} hit(s): {s['high']} high, {s['medium']} medium, {s['low']} low{allowed}")
        print("CLEAN" if report["clean"] else "HITS FOUND")
        return 0 if report["clean"] else 1
    if args.command == "record":
        result = record_scan(args.watchlist, args.destination, _passphrase(), args.target)
        s = result["recorded_scan"]
        print(f"recorded scan → {result['output']} (revision {result['revision']})  "
              f"{s['hits']} hit(s) over {s['files_scanned']} files")
        return 0
    if args.command == "diff":
        rep = diff_scan(args.watchlist, _passphrase(), args.target, ignore=args.ignore)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
            return 1 if rep["regressed"] else 0
        cur = rep["current"]
        if not rep["has_baseline"]:
            print(f"No earlier recorded scan to compare against — {cur['hits']} hit(s) now "
                  f"({cur['high']} high, {cur['medium']} medium, {cur['low']} low). "
                  f"Record one with `skywatch record`.")
            return 0
        d = rep["delta"]
        def sgn(n):
            return f"{n:+d}"
        print(f"since the last recorded scan ({rep['previous_recorded_utc']}):")
        print(f"  hits {rep['previous']['hits']} → {cur['hits']} ({sgn(d['hits'])}); "
              f"high {sgn(d['high'])}, medium {sgn(d['medium'])}, low {sgn(d['low'])}")
        print("REGRESSED — more hits than before" if rep["regressed"]
              else ("no change" if d["hits"] == 0 else "improved — fewer hits than before"))
        return 1 if rep["regressed"] else 0
    if args.command == "export":
        result = export(args.watchlist, args.destination, _passphrase(), args.format, args.target)
        print(f"export ({result['format']}): wrote {result['output']}  sha256 {result['sha256']}")
        return 0
    if args.command == "inspect":
        print(json.dumps(inspect(args.watchlist, _passphrase()), indent=2, ensure_ascii=False))
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in (None, "gui"):
        from .gui import run_app
        return run_app()
    try:
        return _run(args)
    except SkyWatchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
