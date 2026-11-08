"""CLI tests that need no display. The passphrase prompt is patched."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from envy_skywatch import cli


class CLITest(unittest.TestCase):
    SECRET = b"a long private skywatch passphrase"

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="envy-skywatch-cli-"))
        self.addCleanup(__import__("shutil").rmtree, self.dir)
        self.tree = self.dir / "logs"; self.tree.mkdir()
        (self.tree / "a.log").write_text("all fine\nERROR boom\n")
        self._n = 0

    def seq(self):
        self._n += 1
        return self.dir / f"w.r{self._n}.envywatch"

    def invoke(self, *args, secret=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(cli, "_passphrase", return_value=secret or self.SECRET):
            code = cli.main([str(a) for a in args])
        return code, out.getvalue(), err.getvalue()

    def test_version(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as ctx:
            cli.main(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("envy-skywatch", out.getvalue())

    def test_init_add_scan_flow(self):
        base = self.dir / "w.envywatch"
        code, out, _ = self.invoke("init", base, "--title", "Incident")
        self.assertEqual(code, 0)
        self.assertTrue(base.exists())

        p1 = self.seq()
        code, out, _ = self.invoke("add", base, p1, "--label", "Errors", "--pattern", "error", "--severity", "high")
        self.assertEqual(code, 0)

        # A hit -> exit 1.
        code, out, _ = self.invoke("scan", p1, self.tree)
        self.assertEqual(code, 1)
        self.assertIn("HITS FOUND", out)
        self.assertIn("a.log:2", out)

        # No match -> clean (exit 0).
        p2 = self.seq()
        self.invoke("add", p1, p2, "--label", "None", "--pattern", "zzqq", "--severity", "low")
        base2 = self.dir / "clean.envywatch"
        self.invoke("init", base2, "--title", "Clean")
        p3 = self.seq()
        self.invoke("add", base2, p3, "--label", "None", "--pattern", "zzqq")
        code, out, _ = self.invoke("scan", p3, self.tree)
        self.assertEqual(code, 0)
        self.assertIn("CLEAN", out)

    def test_record_and_inspect(self):
        base = self.dir / "w.envywatch"
        self.invoke("init", base, "--title", "Proj")
        p1 = self.seq()
        self.invoke("add", base, p1, "--label", "Errors", "--pattern", "error")
        p2 = self.seq()
        code, out, _ = self.invoke("record", p1, p2, self.tree)
        self.assertEqual(code, 0)
        code, out, _ = self.invoke("inspect", p2)
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertEqual(parsed["terms"][0]["label"], "Errors")
        self.assertEqual(parsed["journal"][0]["hits"], 1)

    def test_export(self):
        base = self.dir / "w.envywatch"
        self.invoke("init", base, "--title", "Proj")
        p1 = self.seq()
        self.invoke("add", base, p1, "--label", "Errors", "--pattern", "error")
        out_html = self.dir / "r.html"
        code, out, _ = self.invoke("export", p1, out_html, self.tree, "--format", "html")
        self.assertEqual(code, 0)
        self.assertIn("sha256", out)

    def test_bad_passphrase_is_error(self):
        base = self.dir / "w.envywatch"
        self.invoke("init", base, "--title", "Proj")
        code, _, err = self.invoke("scan", base, self.tree, secret=b"the wrong passphrase!")
        self.assertEqual(code, 2)
        self.assertIn("passphrase", err.lower())

    def test_unknown_command(self):
        with self.assertRaises(SystemExit):
            cli.build_parser().parse_args(["seance"])


if __name__ == "__main__":
    unittest.main()
