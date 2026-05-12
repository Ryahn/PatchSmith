"""Minimal GUI to apply a patch from the folder containing this tool."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from patcher.core.apply_patch import ApplyPatchOptions, apply_patch
from patcher.core.paths import portable_apply_patch_root
from patcher.version import __version__


class _PortableApplyWorker(QThread):
    log_line = Signal(str)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, opts: ApplyPatchOptions) -> None:
        super().__init__()
        self._opts = opts

    def run(self) -> None:
        def log(s: str) -> None:
            self.log_line.emit(s)

        try:
            apply_patch(self._opts, log=log)
            self.finished_ok.emit()
        except Exception as e:
            self.failed.emit(str(e))


class PortableApplyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._patch_root = portable_apply_patch_root()
        self._worker: _PortableApplyWorker | None = None

        self.setWindowTitle(f"Apply patch {__version__}")
        self.resize(640, 480)

        central = QWidget()
        layout = QVBoxLayout(central)

        manifest = self._patch_root / "patch_manifest.json"
        if not manifest.is_file():
            layout.addWidget(
                QLabel(
                    "patch_manifest.json was not found next to this program.\n"
                    "Keep this apply tool in the patch folder (same folder as the manifest).\n"
                    f"Looked in:\n{self._patch_root}"
                )
            )
            self._manifest_ok = False
        else:
            layout.addWidget(
                QLabel(
                    f"Patch folder:\n{self._patch_root}\n\n"
                    "Select the game folder to update, then click Apply patch."
                )
            )
            self._manifest_ok = True

        form = QFormLayout()
        self._game = QLineEdit()
        g_row = QHBoxLayout()
        g_row.addWidget(self._game)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._browse_game)
        g_row.addWidget(btn_browse)
        form.addRow("Game folder", g_row)

        self._backup = QCheckBox("Create backup before patching")
        self._backup.setChecked(True)
        form.addRow(self._backup)

        self._backup_dir = QLineEdit()
        self._backup_dir.setPlaceholderText("Optional: defaults to parent of game folder")
        bd_row = QHBoxLayout()
        bd_row.addWidget(self._backup_dir)
        bbd = QPushButton("Browse…")
        bbd.clicked.connect(self._browse_backup_dir)
        bd_row.addWidget(bbd)
        form.addRow("Backup directory (optional)", bd_row)

        layout.addLayout(form)

        self._apply_btn = QPushButton("Apply patch")
        self._apply_btn.clicked.connect(self._on_apply)
        self._apply_btn.setEnabled(self._manifest_ok)
        layout.addWidget(self._apply_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        layout.addWidget(self._progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Log…")
        layout.addWidget(self._log, stretch=1)

        if os.environ.get("PATCHSMITH_DEBUG"):
            self._log.appendPlainText(f"DEBUG patch_root={self._patch_root}")

        self.setCentralWidget(central)

    def _browse_game(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self,
            "Select game folder",
            self._game.text() or str(Path.home()),
        )
        if d:
            self._game.setText(d)

    def _browse_backup_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self,
            "Select backup directory",
            self._backup_dir.text() or str(Path.home()),
        )
        if d:
            self._backup_dir.setText(d)

    def _append_log(self, text: str) -> None:
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertPlainText(text + "\n")

    def _on_apply(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        game = self._game.text().strip()
        if not game:
            QMessageBox.warning(self, "Apply patch", "Please select the game folder.")
            return
        backup_dir = self._backup_dir.text().strip()
        opts = ApplyPatchOptions(
            game_root=Path(game),
            patch_path=self._patch_root,
            backup=self._backup.isChecked(),
            backup_dir=Path(backup_dir) if backup_dir else None,
        )
        self._log.clear()
        self._apply_btn.setEnabled(False)
        self._worker = _PortableApplyWorker(opts)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_fail)
        self._worker.start()

    def _on_done(self) -> None:
        self._apply_btn.setEnabled(True)
        QMessageBox.information(self, "Apply patch", "Patch applied successfully.")

    def _on_fail(self, msg: str) -> None:
        self._apply_btn.setEnabled(True)
        self._append_log(f"ERROR: {msg}")
        QMessageBox.critical(self, "Apply patch", msg)
