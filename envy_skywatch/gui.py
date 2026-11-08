"""A native ENVY SkyWatch window: a real desktop app, not a web view.

Built with PyQt6 and styled in the ENVY palette with a live animated header.
Keep an encrypted watchlist of terms — keywords or file hashes — scan a file or
folder offline, and read every hit with its file, line and context. Recording a
scan appends a summary to a hash-chained journal as a new revision; earlier
revisions are never overwritten.

Nothing is sent: no network, no accounts.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

from . import __version__
from . import core
from .core import SkyWatchError

BG = "#050713"
PANEL = "#0a0e22"
PANEL_HI = "#121735"
INK = "#f2f4ff"
MUTED = "#b9c3df"
DIM = "#6f7898"
PINK = "#ff3db4"
CYAN = "#35e8ff"
LAVENDER = "#ac8cff"
VIOLET = "#8547e8"
AMBER = "#ffb347"
GREEN = "#49e3a6"
LINE = "#1f2547"

SEV_COLOR = {"high": PINK, "medium": AMBER, "low": CYAN}


def lerp(a, b, t):
    from PyQt6.QtGui import QColor
    ca, cb = QColor(a), QColor(b)
    return QColor(int(ca.red() + (cb.red() - ca.red()) * t),
                  int(ca.green() + (cb.green() - ca.green()) * t),
                  int(ca.blue() + (cb.blue() - ca.blue()) * t))


def _build():
    from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
    from PyQt6.QtGui import (QColor, QPainter, QLinearGradient, QRadialGradient, QConicalGradient,
                             QFont, QPen, QBrush)
    from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QPlainTextEdit,
                                 QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                                 QAbstractItemView, QVBoxLayout, QHBoxLayout, QInputDialog,
                                 QFileDialog, QMessageBox, QLineEdit as QLE)

    class Header(QWidget):
        def __init__(self):
            super().__init__()
            self.setFixedHeight(172)
            self.phase = 0.0
            self.stars = [(((i * 139 + 37) % 1000) / 1000.0,
                           ((i * 83 + 19) % 172) / 172.0,
                           0.6 + (i % 3) * 0.5, (i % 7) / 7.0) for i in range(60)]
            self.blips = [(0.8, 0.35), (2.1, 0.62), (3.9, 0.5), (5.2, 0.8)]

        def tick(self, phase):
            self.phase = phase
            self.update()

        def paintEvent(self, _event):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            p.fillRect(self.rect(), QColor(BG))
            for cx, cy, rad, col, a in ((w - 120, 60, 250, CYAN, 46),
                                        (60, h, 280, VIOLET, 52), (w * 0.5, -40, 240, PINK, 38)):
                g = QRadialGradient(cx, cy, rad)
                c = QColor(col); c.setAlpha(a); g.setColorAt(0, c)
                c2 = QColor(col); c2.setAlpha(0); g.setColorAt(1, c2)
                p.setBrush(QBrush(g)); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(cx, cy), rad, rad)
            for sx, sy, sr, ph in self.stars:
                tw = 0.5 + 0.5 * math.sin(self.phase / 0.5 + ph * 6.28)
                c = QColor(205, 217, 255); c.setAlphaF(0.15 + 0.6 * tw)
                p.setBrush(c); p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(sx * w, sy * h), sr, sr)
            self._radar(p, 46, 52, 22)
            pulse = 0.5 + 0.5 * math.sin(self.phase)
            p.setFont(QFont("Helvetica", 30, QFont.Weight.Bold))
            grad = QLinearGradient(84, 0, 500, 0)
            grad.setColorAt(0, QColor(CYAN))
            grad.setColorAt(0.5, QColor(lerp(CYAN, "#ffffff", 0.2 * pulse)))
            grad.setColorAt(1, QColor(PINK))
            glow = QColor(VIOLET); glow.setAlpha(int(55 + 55 * pulse))
            p.setPen(QPen(glow, 1))
            for dx, dy in ((1.3, 1.3), (-1.3, 1.3), (1.3, -1.3)):
                p.drawText(QRectF(84 + dx, 38 + dy, 620, 48), Qt.AlignmentFlag.AlignVCenter, "ENVY SKYWATCH")
            p.setPen(QPen(QBrush(grad), 1))
            p.drawText(QRectF(84, 38, 620, 48), Qt.AlignmentFlag.AlignVCenter, "ENVY SKYWATCH")
            p.setFont(QFont("Courier New", 11, QFont.Weight.Bold))
            p.setPen(QColor(LAVENDER))
            p.drawText(QRectF(86, 92, 700, 20), Qt.AlignmentFlag.AlignVCenter,
                       "ENCRYPTED  ·  WATCHLIST  ·  OFFLINE SCAN")
            y = 126
            p.setPen(QPen(QColor(LINE), 2)); p.drawLine(86, y, w - 54, y)
            p.setPen(QPen(QColor(VIOLET), 3)); p.drawLine(86, y, 158, y)
            span = (w - 54) - 86
            x = 86 + span * ((self.phase * 0.12) % 1.0)
            halo = QRadialGradient(x, y, 15)
            hc = QColor(CYAN); hc.setAlpha(170); halo.setColorAt(0, hc)
            hc2 = QColor(CYAN); hc2.setAlpha(0); halo.setColorAt(1, hc2)
            p.setBrush(QBrush(halo)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), 15, 15)
            p.setBrush(QColor("#ffffff")); p.drawEllipse(QPointF(x, y), 2.5, 2.5)
            p.end()

        def _radar(self, p, cx, cy, r):
            # Concentric rings.
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(LAVENDER), 1.1))
            for rr in (r, r * 0.66, r * 0.33):
                p.drawEllipse(QPointF(cx, cy), rr, rr)
            p.setPen(QPen(QColor(LINE), 1))
            p.drawLine(int(cx - r), cy, int(cx + r), cy)
            p.drawLine(cx, int(cy - r), cx, int(cy + r))
            # Rotating sweep.
            ang = (self.phase * 1.1) % (2 * math.pi)
            sweep = QConicalGradient(cx, cy, -math.degrees(ang))
            c0 = QColor(CYAN); c0.setAlpha(150); sweep.setColorAt(0.0, c0)
            c1 = QColor(CYAN); c1.setAlpha(0); sweep.setColorAt(0.18, c1)
            sweep.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(sweep)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r, r)
            ex, ey = cx + r * math.cos(ang), cy + r * math.sin(ang)
            p.setPen(QPen(QColor(CYAN), 1.4)); p.drawLine(QPointF(cx, cy), QPointF(ex, ey))
            # Blips flashing as the sweep passes.
            p.setPen(Qt.PenStyle.NoPen)
            for bang, br in self.blips:
                near = (math.cos(ang - bang) + 1) / 2
                c = QColor(PINK); c.setAlphaF(0.2 + 0.75 * near ** 4)
                p.setBrush(c)
                bx, by = cx + r * br * math.cos(bang), cy + r * br * math.sin(bang)
                p.drawEllipse(QPointF(bx, by), 2.0, 2.0)

    def make_table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        return table

    ID_ROLE = int(Qt.ItemDataRole.UserRole)

    class Window(QWidget):
        def __init__(self):
            super().__init__()
            self.watchlist = None   # Path of the current encrypted watchlist file
            self.secret = None      # passphrase bytes, kept in memory for this watchlist only
            self.data = None        # decrypted, validated watchlist dict
            self.report = None      # the latest scan result
            self.last_target = None # the last scanned file/folder, for Record / Export
            self.setWindowTitle("ENVY SkyWatch")
            self.resize(1200, 880)
            self.setMinimumSize(1000, 740)
            self.setStyleSheet(STYLE)
            root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
            self.header = Header(); root.addWidget(self.header)

            body = QWidget(); body.setObjectName("body")
            bl = QVBoxLayout(body); bl.setContentsMargins(22, 14, 22, 16); bl.setSpacing(10)

            intro = QLabel("Keep a watchlist of terms — keywords or file hashes — then scan a file or folder "
                           "and read every hit with its file, line and context. Every save is a new revision. Nothing is sent.")
            intro.setObjectName("status"); intro.setWordWrap(True); bl.addWidget(intro)

            controls = QHBoxLayout()
            for caption, handler, name in (("New", self.new_watchlist, "go"),
                                           ("Open", self.open_watchlist, "pick"),
                                           ("Lock", self.lock, "pick"),
                                           ("Add term", self.add_term, "go"),
                                           ("Remove", self.remove_term, "pick"),
                                           ("Scan folder", self.scan_folder, "go"),
                                           ("Scan file", self.scan_file, "go"),
                                           ("Record scan", self.record, "pick"),
                                           ("Export", self.export_report, "pick")):
                b = QPushButton(caption); b.setObjectName(name)
                b.setCursor(Qt.CursorShape.PointingHandCursor); b.clicked.connect(handler)
                controls.addWidget(b)
            controls.addStretch(1)
            bl.addLayout(controls)

            self.mon_header = QPlainTextEdit(); self.mon_header.setObjectName("mono")
            self.mon_header.setReadOnly(True); self.mon_header.setFixedHeight(84)
            self.mon_header.setPlainText("No watchlist open. Create a new watchlist or open an existing one.")
            bl.addWidget(self.mon_header)

            self.views = QTabWidget(); self.views.setObjectName("tabs")
            self.t_hits = make_table(["Severity", "Term", "Kind", "File", "Line", "Context"])
            self.t_terms = make_table(["Label", "Pattern", "Kind", "Severity", "Added"])
            self.t_history = make_table(["Scanned UTC", "Target", "Files", "Hits", "H / M / L"])
            self.views.addTab(self.t_hits, "Hits")
            self.views.addTab(self.t_terms, "Watchlist")
            self.views.addTab(self.t_history, "History")
            bl.addWidget(self.views, 1)

            self.path_label = QLabel(""); self.path_label.setObjectName("foot")
            self.path_label.setWordWrap(True); bl.addWidget(self.path_label)
            foot = QLabel("A hit is a literal, case-insensitive match — it means the term appeared, not that it "
                          "matters. Matching is not regex, fuzzy or semantic; binary and unreadable files are "
                          "skipped for keywords (still hashed). Times are assertions from your clock.")
            foot.setObjectName("foot"); foot.setWordWrap(True); bl.addWidget(foot)
            root.addWidget(body, 1)

            self.phase = 0.0
            self.timer = QTimer(self); self.timer.timeout.connect(self._animate); self.timer.start(33)
            self._set_enabled(False)

        # ----- lifecycle ----------------------------------------------------
        def _ask_passphrase(self, confirm):
            text, ok = QInputDialog.getText(self, "Passphrase",
                                            "Watchlist passphrase (at least 12 characters):", QLE.EchoMode.Password)
            if not ok:
                return None
            secret = text.encode("utf-8")
            if confirm:
                again, ok2 = QInputDialog.getText(self, "Confirm passphrase",
                                                  "Repeat the passphrase:", QLE.EchoMode.Password)
                if not ok2:
                    return None
                if again.encode("utf-8") != secret:
                    self._warn("Passphrases do not match."); return None
            try:
                return core.check_passphrase(secret)
            except SkyWatchError as exc:
                self._warn(str(exc)); return None

        def new_watchlist(self):
            title, ok = QInputDialog.getText(self, "New watchlist", "Watchlist title:")
            if not ok or not title.strip():
                return
            dest, _ = QFileDialog.getSaveFileName(self, "Save the encrypted watchlist", "watch.envywatch",
                                                  "Watchlist (*.envywatch);;All files (*)")
            if not dest:
                return
            secret = self._ask_passphrase(confirm=True)
            if secret is None:
                return
            try:
                if Path(dest).exists():
                    Path(dest).unlink()
                core.create(dest, title.strip(), secret)
                self._open_path(Path(dest), secret)
                self._warn("Watchlist created. Add a term, then scan a file or folder.",
                           icon=QMessageBox.Icon.Information, title="Watchlist created")
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc))

        def open_watchlist(self):
            path, _ = QFileDialog.getOpenFileName(self, "Open an encrypted watchlist", "",
                                                  "Watchlist (*.envywatch);;All files (*)")
            if not path:
                return
            secret = self._ask_passphrase(confirm=False)
            if secret is None:
                return
            self._open_path(Path(path), secret)

        def _open_path(self, path, secret):
            try:
                data, _ = core._load(path, secret)
            except SkyWatchError as exc:
                self._warn(str(exc)); return
            self.watchlist, self.secret, self.data = path, secret, data
            self.report, self.last_target = None, None
            self._set_enabled(True)
            self.t_hits.setRowCount(0)
            self._refresh_header()
            self._fill_terms(data["terms"])
            self._fill_history(data["journal"])

        def lock(self):
            self.watchlist = self.secret = self.data = self.report = self.last_target = None
            for t in (self.t_hits, self.t_terms, self.t_history):
                t.setRowCount(0)
            self.mon_header.setPlainText("Locked. The passphrase was cleared from memory.")
            self.path_label.setText("")
            self._set_enabled(False)

        def _reopen(self, path):
            target = self.last_target
            self._open_path(Path(path), self.secret)
            self.last_target = target

        # ----- terms --------------------------------------------------------
        def add_term(self):
            if not self.data:
                return
            label, ok = QInputDialog.getText(self, "Add term", "Label (e.g. Error lines):")
            if not ok or not label.strip():
                return
            kind, ok = QInputDialog.getItem(self, "Kind", "Match a keyword, or a file by its SHA-256?",
                                            ["keyword", "file SHA-256"], 0, False)
            if not ok:
                return
            k = "text" if kind == "keyword" else "sha256"
            prompt = "Keyword to watch for (case-insensitive):" if k == "text" else "64-character SHA-256:"
            pattern, ok = QInputDialog.getText(self, "Pattern", prompt)
            if not ok or not pattern.strip():
                return
            sev, ok = QInputDialog.getItem(self, "Severity", "Severity:", ["high", "medium", "low"], 1, False)
            if not ok:
                return
            dest = self._next_revision_path()
            try:
                core.add_term(self.watchlist, dest, self.secret, label.strip(), pattern.strip(), k, sev)
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc)); return
            self._reopen(dest)
            self.views.setCurrentIndex(1)

        def remove_term(self):
            if not self.data:
                return
            term_id, label = self._selected_term()
            if not term_id:
                self._warn("Select a term in the Watchlist tab first."); return
            if QMessageBox.question(self, "Remove term", f"Remove “{label}” from the watchlist?") \
                    != QMessageBox.StandardButton.Yes:
                return
            dest = self._next_revision_path()
            try:
                core.remove_term(self.watchlist, dest, self.secret, term_id)
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc)); return
            self._reopen(dest)

        # ----- scanning -----------------------------------------------------
        def scan_folder(self):
            target = QFileDialog.getExistingDirectory(self, "Choose a folder to scan")
            if target:
                self._run_scan(target)

        def scan_file(self):
            target, _ = QFileDialog.getOpenFileName(self, "Choose a file to scan")
            if target:
                self._run_scan(target)

        def _run_scan(self, target):
            if not self.data:
                return
            if not self.data["terms"]:
                self._warn("Add at least one term before scanning."); return
            try:
                report = core.scan(self.watchlist, self.secret, target)
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc)); return
            self.report, self.last_target = report, target
            self._fill_hits(report)
            self.views.setCurrentIndex(0)
            self._refresh_header()
            if report["clean"]:
                self._warn(f"No hits in {report['files_scanned']} file(s) scanned.",
                           icon=QMessageBox.Icon.Information, title="Scan complete")

        def record(self):
            if not self.data or not self.last_target:
                self._warn("Scan a file or folder first, then record it."); return
            dest = self._next_revision_path()
            try:
                result = core.record_scan(self.watchlist, dest, self.secret, self.last_target)
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc)); return
            self._reopen(dest)
            self.views.setCurrentIndex(2)
            self._warn(f"Recorded a scan of {result['recorded_scan']['files_scanned']} file(s) as revision "
                       f"{result['revision']}.", icon=QMessageBox.Icon.Information, title="Scan recorded")

        def export_report(self):
            if not self.data:
                return
            if not self.last_target:
                self._warn("Scan a file or folder first, then export the report."); return
            choice, ok = QInputDialog.getItem(self, "Export report", "Format:",
                                              ["HTML report", "JSON report"], 0, False)
            if not ok:
                return
            fmt = "html" if choice.startswith("HTML") else "json"
            dest, _ = QFileDialog.getSaveFileName(self, "Export scan report",
                                                  f"skywatch-report.{fmt}", f"{fmt.upper()} (*.{fmt});;All files (*)")
            if not dest:
                return
            try:
                if Path(dest).exists():
                    Path(dest).unlink()
                result = core.export(self.watchlist, dest, self.secret, fmt, self.last_target)
            except (SkyWatchError, OSError) as exc:
                self._warn(str(exc)); return
            self._warn(f"Exported a plaintext {fmt.upper()} report to {result['output']}.\n\n"
                       f"SHA-256: {result['sha256']}", icon=QMessageBox.Icon.Information, title="Report exported")

        # ----- selection ----------------------------------------------------
        def _selected_term(self):
            row = self.t_terms.currentRow()
            if row < 0:
                return None, None
            item = self.t_terms.item(row, 0)
            if item is None:
                return None, None
            return item.data(ID_ROLE), item.data(ID_ROLE + 1)

        # ----- display ------------------------------------------------------
        def _refresh_header(self):
            d, r = self.data, self.report
            if not d:
                return
            if r is None:
                verdict = "not scanned yet"
            elif r["clean"]:
                verdict = f"clean ({r['files_scanned']} files)"
            else:
                s = r["by_severity"]
                verdict = f"{r['hit_count']} hits ({s['high']} high, {s['medium']} medium, {s['low']} low)"
            self.mon_header.setPlainText(
                f"{d['title']}  ·  revision {d['revision']}  ·  {len(d['terms'])} terms  ·  {verdict}\n"
                f"watchlist: {d['watch_id']}")
            if self.watchlist:
                self.path_label.setText(str(self.watchlist) + (f"   —   last scan: {self.last_target}"
                                                               if self.last_target else ""))

        def _cell(self, text, color=None):
            item = QTableWidgetItem("" if text is None else str(text))
            if color:
                item.setForeground(QColor(color))
            return item

        def _fill_hits(self, report):
            t = self.t_hits; rows = report["hits"]; t.setRowCount(len(rows))
            for i, h in enumerate(rows):
                t.setItem(i, 0, self._cell(h["severity"], SEV_COLOR[h["severity"]]))
                t.setItem(i, 1, self._cell(h["label"], INK))
                t.setItem(i, 2, self._cell(h["kind"]))
                t.setItem(i, 3, self._cell(h["file"]))
                t.setItem(i, 4, self._cell(h["line"] if h["kind"] == "text" else "—"))
                t.setItem(i, 5, self._cell(h["context"]))
            t.resizeColumnsToContents(); t.horizontalHeader().setStretchLastSection(True)
            if not rows:
                t.setRowCount(1)
                t.setItem(0, 0, self._cell("clean", GREEN))
                t.setItem(0, 1, self._cell("No hits in the last scan."))

        def _fill_terms(self, terms):
            t = self.t_terms; t.setRowCount(len(terms))
            for i, tr in enumerate(terms):
                label_item = self._cell(tr["label"], CYAN)
                label_item.setData(ID_ROLE, tr["id"]); label_item.setData(ID_ROLE + 1, tr["label"])
                t.setItem(i, 0, label_item)
                shown = (tr["pattern"][:16] + "…") if tr["kind"] == "sha256" else tr["pattern"]
                t.setItem(i, 1, self._cell(shown))
                t.setItem(i, 2, self._cell("keyword" if tr["kind"] == "text" else "file SHA-256"))
                t.setItem(i, 3, self._cell(tr["severity"], SEV_COLOR[tr["severity"]]))
                t.setItem(i, 4, self._cell(tr["created_utc"]))
            t.resizeColumnsToContents(); t.horizontalHeader().setStretchLastSection(True)

        def _fill_history(self, journal):
            t = self.t_history; t.setRowCount(len(journal))
            for i, r in enumerate(reversed(journal)):
                s = r["scan"]
                t.setItem(i, 0, self._cell(r["recorded_utc"]))
                t.setItem(i, 1, self._cell(s["target"]))
                t.setItem(i, 2, self._cell(f"{s['files_scanned']} ({s['files_skipped']} skipped)"))
                t.setItem(i, 3, self._cell(s["hits"], PINK if s["hits"] else GREEN))
                t.setItem(i, 4, self._cell(f"{s['high']} / {s['medium']} / {s['low']}"))
            t.resizeColumnsToContents(); t.horizontalHeader().setStretchLastSection(True)

        def _next_revision_path(self):
            base = self.watchlist
            stem = base.stem
            if ".r" in stem and stem.rsplit(".r", 1)[-1].isdigit():
                stem = stem.rsplit(".r", 1)[0]
            rev = (self.data["revision"] + 1) if self.data else 1
            candidate = base.with_name(f"{stem}.r{rev}{base.suffix}")
            n = rev
            while candidate.exists():
                n += 1
                candidate = base.with_name(f"{stem}.r{n}{base.suffix}")
            return candidate

        def _set_enabled(self, on):
            self.views.setEnabled(on)

        def _warn(self, message, icon=None, title="SkyWatch"):
            box = QMessageBox(self); box.setWindowTitle(title)
            box.setIcon(icon or QMessageBox.Icon.Warning); box.setText(message); box.exec()

        def _animate(self):
            self.phase += 0.05
            self.header.tick(self.phase)

    return QApplication, Window


STYLE = f"""
#body {{ background: {BG}; }}
QWidget {{ color: {INK}; font-family: Helvetica, Arial, sans-serif; font-size: 13px; }}
#status {{ color: {MUTED}; font-size: 12px; }}
#foot {{ color: {DIM}; font-size: 11px; }}
#mono {{ background: {PANEL_HI}; border: 1px solid {LINE}; border-radius: 9px; color: {INK};
         font-family: "Courier New", monospace; font-size: 13px; padding: 8px; }}
QTableWidget {{ background: {PANEL_HI}; alternate-background-color: {PANEL}; border: 1px solid {LINE};
                border-radius: 10px; gridline-color: {LINE}; }}
QTableWidget::item {{ padding: 4px 6px; }}
QTableWidget::item:selected {{ background: {VIOLET}; color: {INK}; }}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; padding: 6px 8px; border: none;
                        border-bottom: 1px solid {LINE}; font-weight: bold; }}
QTableCornerButton::section {{ background: {PANEL}; border: none; }}
QTabWidget#tabs::pane {{ border: 1px solid {LINE}; border-radius: 12px; background: {PANEL}; }}
QTabBar::tab {{ background: {PANEL_HI}; color: {MUTED}; padding: 8px 18px; margin-right: 6px;
                border-top-left-radius: 9px; border-top-right-radius: 9px; font-weight: bold; }}
QTabBar::tab:selected {{ color: {INK}; border-bottom: 2px solid {PINK}; }}
QPushButton#go {{ background: {PINK}; color: {BG}; border: none; border-radius: 10px; font-weight: bold; padding: 9px 14px; }}
QPushButton#go:hover {{ background: {CYAN}; }}
QPushButton#pick {{ background: {PANEL_HI}; border: 1px solid {LAVENDER}; border-radius: 9px; color: {INK};
                    font-weight: bold; padding: 9px 12px; }}
QPushButton#pick:hover {{ background: #1b2150; }}
"""


def run_app() -> int:
    try:
        from PyQt6.QtWidgets import QApplication  # noqa: F401
    except Exception:
        print("PyQt6 is required for the SkyWatch window. Use 'envy-skywatch' subcommands instead.")
        return 2
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("No display found. Use 'envy-skywatch init/add/scan/record/export' in a terminal instead.")
        return 2
    try:
        QApplication, Window = _build()
        app = QApplication.instance() or QApplication(sys.argv)
        window = Window(); window.show()
        return app.exec()
    except Exception as exc:  # pragma: no cover
        print(f"Could not open the window: {exc}")
        return 2
