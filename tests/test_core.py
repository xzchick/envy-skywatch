"""Core SkyWatch tests: encrypted watchlists, terms, offline scanning (keyword and
hash), severity ordering, the scan journal and its hash chain, revision-preserving
saves, export and the no-overwrite guarantee.
"""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from envy_skywatch import core
from envy_skywatch.core import SkyWatchError


class SkyWatchTest(unittest.TestCase):
    SECRET = b"a long private skywatch passphrase"

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="envy-skywatch-"))
        self.addCleanup(__import__("shutil").rmtree, self.dir)
        self.tree = self.dir / "logs"
        self.tree.mkdir()
        (self.tree / "app.log").write_text("INFO ok\nERROR disk full on host alpha\ninfo ERROR again\n")
        (self.tree / "notes.txt").write_text("nothing to see here\n")
        (self.tree / "sub").mkdir()
        (self.tree / "sub" / "secret.txt").write_text("token=ABCD-SECRET-1234\n")
        self._n = 0

    def seq(self):
        self._n += 1
        return self.dir / f"w.r{self._n}.envywatch"

    def watchlist(self, name="w.envywatch", title="Watch"):
        path = self.dir / name
        core.create(path, title, self.SECRET)
        return path

    # ----- envelope / create -------------------------------------------
    def test_encrypted_round_trip_and_magic(self):
        blob = core.encrypt_bytes(b"x", self.SECRET)
        self.assertEqual(blob[:11], b"ENVYVAULT2\x00")
        self.assertEqual(core.decrypt_bytes(blob, self.SECRET), b"x")

    def test_create_empty_watchlist(self):
        path = self.watchlist(title="Incident terms")
        data, _ = core._load(path, self.SECRET)
        self.assertEqual(data["revision"], 0)
        self.assertEqual(data["title"], "Incident terms")
        self.assertEqual(data["terms"], [])

    def test_short_passphrase_rejected(self):
        with self.assertRaises(SkyWatchError):
            core.create(self.dir / "s", "t", b"short")

    # ----- terms -------------------------------------------------------
    def test_add_term_preserves_previous_revision(self):
        p0 = self.watchlist()
        p1 = self.seq()
        res = core.add_term(p0, p1, self.SECRET, "Errors", "error", severity="high")
        self.assertEqual(res["revision"], 1)
        self.assertTrue(p0.exists(), "previous revision preserved")
        data, _ = core._load(p1, self.SECRET)
        self.assertEqual(data["terms"][0]["pattern"], "error")
        self.assertEqual(data["terms"][0]["severity"], "high")

    def test_hash_term_pattern_validated(self):
        p0 = self.watchlist()
        with self.assertRaises(SkyWatchError):
            core.add_term(p0, self.seq(), self.SECRET, "Bad hash", "not-a-hash", kind="sha256")
        good = hashlib.sha256(b"x").hexdigest()
        res = core.add_term(p0, self.seq(), self.SECRET, "Known file", good.upper(), kind="sha256")
        data, _ = core._load(Path(res["output"]), self.SECRET)
        self.assertEqual(data["terms"][0]["pattern"], good)  # lowercased

    def test_bad_severity_and_kind_rejected(self):
        p0 = self.watchlist()
        with self.assertRaises(SkyWatchError):
            core.add_term(p0, self.seq(), self.SECRET, "x", "y", severity="critical")
        with self.assertRaises(SkyWatchError):
            core.add_term(p0, self.seq(), self.SECRET, "x", "y", kind="bogus")

    def test_remove_term(self):
        p0 = self.watchlist()
        p1 = self.seq()
        tid = core.add_term(p0, p1, self.SECRET, "Errors", "error")["term_id"]
        p2 = self.seq()
        core.remove_term(p1, p2, self.SECRET, tid)
        data, _ = core._load(p2, self.SECRET)
        self.assertEqual(data["terms"], [])

    # ----- scanning ----------------------------------------------------
    def _watch_with(self, *terms):
        p = self.watchlist()
        for label, pattern, kind, sev in terms:
            d = self.seq()
            core.add_term(p, d, self.SECRET, label, pattern, kind=kind, severity=sev)
            p = d
        return p

    def test_keyword_scan_finds_hits_with_line_and_context(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        report = core.scan(p, self.SECRET, self.tree)
        self.assertFalse(report["clean"])
        files = {h["file"] for h in report["hits"]}
        self.assertEqual(files, {"app.log"})
        lines = sorted(h["line"] for h in report["hits"])
        self.assertEqual(lines, [2, 3])  # case-insensitive: ERROR and ERROR
        self.assertIn("disk full", report["hits"][0]["context"])

    def test_case_insensitive_and_severity_ordering(self):
        p = self._watch_with(("Secret", "secret", "text", "high"),
                             ("Info", "info", "text", "low"))
        report = core.scan(p, self.SECRET, self.tree)
        # high-severity hits sort before low-severity ones.
        self.assertEqual(report["hits"][0]["severity"], "high")
        self.assertTrue(all(h["severity"] == "high" for h in report["hits"][:report["by_severity"]["high"]]))
        self.assertGreaterEqual(report["by_severity"]["low"], 1)

    def test_hash_term_matches_file_by_content(self):
        payload = (self.tree / "sub" / "secret.txt").read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        p = self._watch_with(("Known bad file", digest, "sha256", "high"))
        report = core.scan(p, self.SECRET, self.tree)
        hit = [h for h in report["hits"] if h["kind"] == "sha256"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["file"], "sub/secret.txt")

    def test_scan_single_file(self):
        p = self._watch_with(("Token", "token=", "text", "medium"))
        report = core.scan(p, self.SECRET, self.tree / "sub" / "secret.txt")
        self.assertEqual(report["hit_count"], 1)
        self.assertEqual(report["files_scanned"], 1)

    def test_binary_file_skips_keywords_but_is_hashed(self):
        binp = self.tree / "blob.bin"
        binp.write_bytes(b"error\x00error")   # contains NUL -> binary
        digest = hashlib.sha256(binp.read_bytes()).hexdigest()
        p = self._watch_with(("Errors", "error", "text", "high"),
                             ("Blob", digest, "sha256", "high"))
        report = core.scan(p, self.SECRET, self.tree)
        # The keyword term must not match inside the binary file...
        self.assertNotIn("blob.bin", {h["file"] for h in report["hits"] if h["kind"] == "text"})
        # ...but the hash term matches it.
        self.assertIn("blob.bin", {h["file"] for h in report["hits"] if h["kind"] == "sha256"})

    def test_scan_ignore_globs(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        (self.tree / "build").mkdir()
        (self.tree / "build" / "out.log").write_text("ERROR in generated output")
        (self.tree / "app.log").write_text("ERROR noise")
        # Baseline: both .log files hit the "error" term.
        base = {h["file"] for h in core.scan(p, self.SECRET, self.tree)["hits"]}
        self.assertIn("app.log", base)
        self.assertIn("build/out.log", base)
        # Ignoring the build dir drops its hit but keeps app.log.
        f1 = {h["file"] for h in core.scan(p, self.SECRET, self.tree, ignore=["build"])["hits"]}
        self.assertIn("app.log", f1)
        self.assertNotIn("build/out.log", f1)
        # Ignoring *.log drops every .log hit -> clean.
        self.assertTrue(core.scan(p, self.SECRET, self.tree, ignore=["*.log"])["clean"])

    def test_clean_scan_when_no_terms_match(self):
        p = self._watch_with(("Nope", "zzxxqq", "text", "low"))
        report = core.scan(p, self.SECRET, self.tree)
        self.assertTrue(report["clean"])
        self.assertEqual(report["hit_count"], 0)

    # ----- record / journal --------------------------------------------
    def test_record_scan_chains_and_preserves(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        p1 = self.seq()
        res = core.record_scan(p, p1, self.SECRET, self.tree)
        self.assertTrue(p.exists(), "previous revision preserved")
        self.assertEqual(res["recorded_scan"]["hits"], 2)
        p2 = self.seq()
        core.record_scan(p1, p2, self.SECRET, self.tree)
        data, _ = core._load(p2, self.SECRET)
        self.assertEqual(data["journal"][1]["previous_sha256"], data["journal"][0]["record_sha256"])

    def test_diff_scan_against_last_recorded(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        # Nothing recorded yet -> no baseline, never a regression.
        first = core.diff_scan(p, self.SECRET, self.tree)
        self.assertFalse(first["has_baseline"])
        self.assertFalse(first["regressed"])
        self.assertIsNone(first["delta"])
        self.assertEqual(first["current"]["hits"], 2)
        # Record a baseline (app.log has two "error" lines), then diff with no change.
        p1 = self.seq()
        core.record_scan(p, p1, self.SECRET, self.tree)
        same = core.diff_scan(p1, self.SECRET, self.tree)
        self.assertTrue(same["has_baseline"])
        self.assertIsNotNone(same["previous_recorded_utc"])
        self.assertEqual(same["delta"]["hits"], 0)
        self.assertFalse(same["regressed"])
        # A new matching file is a regression against the recorded baseline.
        (self.tree / "new.log").write_text("ERROR another one\n")
        worse = core.diff_scan(p1, self.SECRET, self.tree)
        self.assertEqual(worse["delta"]["hits"], 1)
        self.assertEqual(worse["current"]["hits"], 3)
        self.assertTrue(worse["regressed"])

    def test_diff_scan_respects_ignore_globs(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        p1 = self.seq()
        core.record_scan(p, p1, self.SECRET, self.tree)
        # Ignoring the only hit-bearing file drops hits below the baseline -> not a regression.
        rep = core.diff_scan(p1, self.SECRET, self.tree, ignore=["app.log"])
        self.assertEqual(rep["current"]["hits"], 0)
        self.assertEqual(rep["delta"]["hits"], -2)
        self.assertFalse(rep["regressed"])

    def test_tampered_journal_breaks_chain(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        p1 = self.seq()
        core.record_scan(p, p1, self.SECRET, self.tree)
        data, _ = core._load(p1, self.SECRET)
        data["journal"][0]["scan"]["hits"] = 999          # tamper without re-hashing
        forged = self.dir / "forged.envywatch"
        forged.write_bytes(core.encrypt_bytes(core._canonical(data), self.SECRET))
        with self.assertRaises(SkyWatchError):
            core.inspect(forged, self.SECRET)

    # ----- export -------------------------------------------------------
    def test_export_html_and_json(self):
        p = self._watch_with(("Errors", "error", "text", "high"))
        html_out = self.dir / "r.html"
        res = core.export(p, html_out, self.SECRET, "html", target=self.tree)
        text = html_out.read_text(encoding="utf-8")
        self.assertIn("Content-Security-Policy", text)
        self.assertIn("app.log", text)
        self.assertFalse(res["clean"])
        json_out = self.dir / "r.json"
        core.export(p, json_out, self.SECRET, "json", target=self.tree)
        report = json.loads(json_out.read_text(encoding="utf-8"))
        self.assertIn("limitations", report)
        self.assertEqual(len(report["hits"]), 2)

    def test_export_escapes_markup_in_context(self):
        (self.tree / "page.html").write_text("<script>alert('x')</script> error here\n")
        p = self._watch_with(("Errors", "error", "text", "high"))
        out = self.dir / "r.html"
        core.export(p, out, self.SECRET, "html", target=self.tree)
        body = out.read_text(encoding="utf-8").split("<style>")[1]
        self.assertNotIn("<script>alert", body)
        self.assertIn("&lt;script&gt;", body)

    # ----- no overwrite -------------------------------------------------
    def test_new_file_never_overwrites(self):
        keep = self.dir / "keep"
        keep.write_bytes(b"precious")
        with self.assertRaises(SkyWatchError):
            core.new_file(keep, b"clobber")
        self.assertEqual(keep.read_bytes(), b"precious")

    def test_add_term_refuses_to_overwrite(self):
        p0 = self.watchlist()
        dest = self.dir / "exists.envywatch"; dest.write_bytes(b"keep me")
        with self.assertRaises(SkyWatchError):
            core.add_term(p0, dest, self.SECRET, "x", "y")
        self.assertEqual(dest.read_bytes(), b"keep me")

    # ----- regex terms (v0.2) ------------------------------------------
    def test_regex_term_matches_with_line_and_context(self):
        p0 = self.watchlist()
        p1 = self.seq()
        core.add_term(p0, p1, self.SECRET, "Secret token", r"token=[A-Z]+-SECRET-\d+",
                      kind="regex", severity="high")
        report = core.scan(p1, self.SECRET, self.tree)
        regex_hits = [h for h in report["hits"] if h["kind"] == "regex"]
        self.assertEqual(len(regex_hits), 1)
        self.assertEqual(regex_hits[0]["file"], "sub/secret.txt")
        self.assertEqual(regex_hits[0]["line"], 1)
        self.assertIn("token=ABCD-SECRET-1234", regex_hits[0]["context"])

    def test_regex_is_case_insensitive(self):
        p0 = self.watchlist()
        p1 = self.seq()
        core.add_term(p0, p1, self.SECRET, "errors", r"error", kind="regex")
        report = core.scan(p1, self.SECRET, self.tree)
        lines = sorted(h["line"] for h in report["hits"] if h["kind"] == "regex")
        self.assertEqual(lines, [2, 3])  # matches both ERROR lines in app.log

    def test_invalid_regex_rejected_at_add(self):
        p0 = self.watchlist()
        with self.assertRaises(SkyWatchError):
            core.add_term(p0, self.seq(), self.SECRET, "bad", "(unclosed", kind="regex")

    # ----- allowlist (v0.2) --------------------------------------------
    def test_allowlist_moves_hits_to_allowed(self):
        p0 = self.watchlist()
        p1 = self.seq(); core.add_term(p0, p1, self.SECRET, "Errors", "error", severity="high")
        report = core.scan(p1, self.SECRET, self.tree)
        self.assertFalse(report["clean"])                 # ERROR lines in app.log
        self.assertEqual(report["allowed_count"], 0)
        p2 = self.seq(); res = core.allow(p1, p2, self.SECRET, "app.log")
        self.assertIn("app.log", res["allowlist"])
        report2 = core.scan(p2, self.SECRET, self.tree)
        self.assertTrue(report2["clean"])                 # the only hits were in app.log
        self.assertEqual(report2["hit_count"], 0)
        self.assertEqual([h["file"] for h in report2["allowed"]], ["app.log", "app.log"])

    def test_allow_then_unallow(self):
        p0 = self.watchlist()
        p1 = self.seq(); core.allow(p0, p1, self.SECRET, "*.log")
        self.assertEqual(core._load(p1, self.SECRET)[0]["allowlist"], ["*.log"])
        p2 = self.seq(); core.unallow(p1, p2, self.SECRET, "*.log")
        self.assertEqual(core._load(p2, self.SECRET)[0]["allowlist"], [])
        with self.assertRaises(SkyWatchError):
            core.unallow(p2, self.seq(), self.SECRET, "*.log")   # no longer present

    def test_pre_allowlist_watchlist_migrates(self):
        p0 = self.watchlist()
        data, _ = core._load(p0, self.SECRET)
        del data["allowlist"]                              # simulate a pre-v0.2 watchlist
        legacy = self.dir / "legacy.envywatch"
        core.new_file(legacy, core.encrypt_bytes(core._canonical(data), self.SECRET))
        reloaded, _ = core._load(legacy, self.SECRET)      # must not raise
        self.assertEqual(reloaded["allowlist"], [])


    # ----- CSV export of hits (v0.2) -----------------------------------
    def test_export_csv_hits(self):
        import csv as _csv
        p0 = self.watchlist()
        p1 = self.seq(); core.add_term(p0, p1, self.SECRET, "Errors", "error", severity="high")
        out = self.dir / "hits.csv"
        res = core.export(p1, out, self.SECRET, "csv", target=self.tree)
        self.assertEqual(res["format"], "csv")
        rows = list(_csv.reader(out.read_text(encoding="utf-8").splitlines()))
        self.assertEqual(rows[0], ["severity", "kind", "term", "file", "line", "context"])
        data_rows = rows[1:]
        self.assertEqual(len(data_rows), 2)                       # two ERROR lines in app.log
        self.assertTrue(all(r[0] == "high" for r in data_rows))
        self.assertTrue(all(r[3] == "app.log" for r in data_rows))


    # ----- Markdown export (v0.2) --------------------------------------
    def test_export_markdown_hits(self):
        p0 = self.watchlist()
        p1 = self.seq(); core.add_term(p0, p1, self.SECRET, "Errors", "error", severity="high")
        out = self.dir / "r.md"
        res = core.export(p1, out, self.SECRET, "md", target=self.tree)
        self.assertEqual(res["format"], "md")
        text = out.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Watch — scan"))
        self.assertIn("## Hits (2)", text)
        self.assertIn("app.log", text)
        self.assertIn("| Severity | Term |", text)


if __name__ == "__main__":
    unittest.main()
