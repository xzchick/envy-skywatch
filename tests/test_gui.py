"""Offscreen GUI tests: drive the real ENVY SkyWatch window without a display."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import PyQt6.QtWidgets  # noqa: F401
    HAVE_QT = True
except Exception:  # pragma: no cover - PyQt6 missing
    HAVE_QT = False

from envy_skywatch import core

SECRET = b"a long private skywatch passphrase"


@unittest.skipUnless(HAVE_QT, "PyQt6 is not installed")
class SkyWatchWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from envy_skywatch.gui import _build
        app_cls, cls.Window = _build()
        cls.app = app_cls.instance() or app_cls([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.tree = self.root / "logs"
        (self.tree / "vendor").mkdir(parents=True)
        (self.tree / "app.log").write_text("INFO ok\nkey AKIAABCDEFGHIJKLMNOP leaked\n")
        (self.tree / "vendor" / "fixture.txt").write_text("sample AKIAZZZZZZZZZZZZZZZZ for tests\n")
        watch = self.root / "w.envywatch"
        core.create(watch, "Secrets", SECRET)
        self.w = self.Window()
        self.warnings = []
        self.w._warn = lambda message, icon=None, title="SkyWatch": self.warnings.append(message)
        self.w._open_path(watch, SECRET)

    def tearDown(self):
        self.w.timer.stop()
        self.w.close()
        self.tmp.cleanup()

    def cells(self, table, col):
        return [table.item(r, col).text() for r in range(table.rowCount()) if table.item(r, col)]

    def test_regex_term_is_added_and_labelled_as_regex(self):
        self.assertTrue(self.w.add_term_values("AWS key", "regex", r"AKIA[0-9A-Z]{16}", "high"))
        self.assertEqual(self.cells(self.w.t_terms, 2), ["regular expression"])
        self.w._run_scan(str(self.tree))
        self.assertEqual(self.w.report["hit_count"], 2)
        self.assertEqual(sorted(self.cells(self.w.t_hits, 3)), ["app.log", "vendor/fixture.txt"])
        rows = dict(zip(self.cells(self.w.t_hits, 3), self.cells(self.w.t_hits, 4)))
        self.assertEqual(rows["app.log"], "2")   # regex hits show their line number, not "—"

    def test_slow_regex_is_refused_with_an_explanation(self):
        self.assertFalse(self.w.add_term_values("slow", "regex", r"(a+)+$", "low"))
        self.assertIn("catastrophic backtracking", self.warnings[-1])
        self.assertEqual(self.w.data["terms"], [])

    def test_allowlist_moves_hits_and_can_be_undone(self):
        self.w.add_term_values("AWS key", "regex", r"AKIA[0-9A-Z]{16}", "high")
        self.assertTrue(self.w.allow_pattern("vendor/*"))
        self.assertEqual(self.cells(self.w.t_allow, 0), ["vendor/*"])
        self.w._run_scan(str(self.tree))
        self.assertEqual(self.w.report["hit_count"], 1)
        self.assertEqual(self.cells(self.w.t_hits, 0), ["high", "allowed"])
        self.assertIn("1 allowed", self.w.mon_header.toPlainText())
        self.assertTrue(self.w.unallow_pattern("vendor/*"))
        self.assertEqual(self.w.t_allow.rowCount(), 0)
        self.w._run_scan(str(self.tree))
        self.assertEqual(self.w.report["hit_count"], 2)

    def test_compare_needs_a_record_then_reports_the_change(self):
        self.w.add_term_values("AWS key", "regex", r"AKIA[0-9A-Z]{16}", "high")
        diff = self.w.compare(str(self.tree))
        self.assertFalse(diff["has_baseline"])
        self.assertIn("no recorded scan", self.w._diff_text(diff))
        self.w._run_scan(str(self.tree))
        self.w.record()
        (self.tree / "new.txt").write_text("AKIAQQQQQQQQQQQQQQQQ\n")
        diff = self.w.compare(str(self.tree))
        self.assertTrue(diff["regressed"])
        self.assertEqual(diff["delta"]["hits"], 1)
        self.assertIn("▲ 1 more hit than the last record", self.w.mon_header.toPlainText())
        self.assertIn("+1 total", self.w._diff_text(diff))


if __name__ == "__main__":
    unittest.main()
