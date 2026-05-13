"""PySide6 main window: Create Patch / Apply Patch."""

from __future__ import annotations

import sys
from pathlib import Path

from dataclasses import replace

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from patcher.core.apply_patch import ApplyPatchOptions, apply_patch
from patcher.core.create_patch import CreatePatchOptions, UserCancelledError, create_patch
from patcher.core.paths import portable_apply_bundle_name
from patcher.engines.detect import Engine, detect_engine, ignore_overrides_for_engine
from patcher.platform_check import tool_warning_messages
from patcher.version import __version__


class _CreateWorker(QThread):
    log_line = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    need_confirm = Signal(str)

    def __init__(self, opts: CreatePatchOptions) -> None:
        super().__init__()
        self._opts = opts
        self._confirm_reply = False

    def set_confirm_reply(self, ok: bool) -> None:
        self._confirm_reply = ok

    def _ask_confirm_large_xdelta(self, msg: str) -> bool:
        self.need_confirm.emit(msg)
        return self._confirm_reply

    def run(self) -> None:
        def log(s: str) -> None:
            self.log_line.emit(s)

        try:
            opts = self._opts
            if opts.large_xdelta_warn_mb > 0:
                opts = replace(opts, confirm_large_xdelta=self._ask_confirm_large_xdelta)
            archive = create_patch(opts, log=log)
            self.finished_ok.emit(archive)
        except UserCancelledError:
            self.cancelled.emit()
        except Exception as e:
            self.failed.emit(str(e))


class _ApplyWorker(QThread):
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"PatchSmith {__version__}")
        self.resize(920, 640)

        self._create_worker: _CreateWorker | None = None
        self._apply_worker: _ApplyWorker | None = None

        tabs = QTabWidget()
        tabs.addTab(self._build_create_tab(), "Create Patch")
        tabs.addTab(self._build_apply_tab(), "Apply Patch")
        self.setCentralWidget(tabs)

        self._maybe_warn_tools()

    def _append_log(self, text: str) -> None:
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertPlainText(text + "\n")

    def _maybe_warn_tools(self) -> None:
        msgs = tool_warning_messages()
        if msgs:
            QMessageBox.warning(
                self,
                "External tools",
                "\n\n".join(msgs),
            )

    def _browse_dir(self, target: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select folder", target.text() or str(Path.home()))
        if d:
            target.setText(d)

    def _browse_patch_folder(self, target: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select patch folder", target.text() or str(Path.home()))
        if d:
            target.setText(d)

    def _browse_patch_archive(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select patch archive",
            target.text() or str(Path.home()),
            "Archives (*.7z *.zip);;All files (*.*)",
        )
        if path:
            target.setText(path)

    def _build_create_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        form = QFormLayout()
        self._c_old = QLineEdit()
        self._c_new = QLineEdit()
        self._c_out = QLineEdit()
        old_row = QHBoxLayout()
        old_row.addWidget(self._c_old)
        b_old = QPushButton("Browse…")
        b_old.clicked.connect(lambda: self._browse_dir(self._c_old))
        old_row.addWidget(b_old)
        new_row = QHBoxLayout()
        new_row.addWidget(self._c_new)
        b_new = QPushButton("Browse…")
        b_new.clicked.connect(lambda: self._browse_dir(self._c_new))
        new_row.addWidget(b_new)
        out_row = QHBoxLayout()
        out_row.addWidget(self._c_out)
        b_out = QPushButton("Browse…")
        b_out.clicked.connect(lambda: self._browse_dir(self._c_out))
        out_row.addWidget(b_out)
        form.addRow("Old game folder", old_row)
        form.addRow("New game folder", new_row)
        form.addRow("Output patch folder", out_row)

        self._c_name = QLineEdit("Game update")
        self._c_from = QLineEdit("1.0")
        self._c_to = QLineEdit("1.1")
        form.addRow("Patch name", self._c_name)
        form.addRow("From version", self._c_from)
        form.addRow("To version", self._c_to)

        self._c_threshold = QDoubleSpinBox()
        self._c_threshold.setRange(0.0, 10_000.0)
        self._c_threshold.setValue(50.0)
        self._c_threshold.setSuffix(" MB")
        form.addRow("xdelta threshold (changed files ≥ this use xdelta)", self._c_threshold)

        self._c_xdelta_level = QSpinBox()
        self._c_xdelta_level.setRange(1, 9)
        self._c_xdelta_level.setValue(6)
        self._c_xdelta_level.setToolTip(
            "xdelta3 secondary compression: 1 = faster encode, larger .xdelta files; "
            "9 = slowest, smallest. Large games (multi‑GB) differ a lot in wall time."
        )
        form.addRow("xdelta compression (1–9)", self._c_xdelta_level)

        self._c_xdelta_warn_mb = QSpinBox()
        self._c_xdelta_warn_mb.setRange(0, 500_000)
        self._c_xdelta_warn_mb.setValue(500)
        self._c_xdelta_warn_mb.setSuffix(" MiB")
        self._c_xdelta_warn_mb.setSpecialValueText("off")
        self._c_xdelta_warn_mb.setToolTip(
            "Before encoding, warn if any file that will use xdelta is at least this large. "
            "Set to 0 MiB to disable the prompt."
        )
        form.addRow("Warn before xdelta if file ≥", self._c_xdelta_warn_mb)

        self._c_preset = QComboBox()
        self._c_preset.addItem("Generic", "generic")
        self._c_preset.addItem("Auto-detect (from old folder)", "auto")
        form.addRow("Preset", self._c_preset)

        self._c_track_del = QCheckBox("Track deleted files")
        self._c_track_del.setChecked(True)
        form.addRow(self._c_track_del)

        self._c_archive = QCheckBox("Create archive after patch (7-Zip)")
        self._c_archive.setChecked(False)
        form.addRow(self._c_archive)

        arch_row = QHBoxLayout()
        self._c_fmt = QComboBox()
        self._c_fmt.addItem("7z", "7z")
        self._c_fmt.addItem("zip", "zip")
        self._c_level = QSpinBox()
        self._c_level.setRange(0, 9)
        self._c_level.setValue(6)
        arch_row.addWidget(QLabel("Format"))
        arch_row.addWidget(self._c_fmt)
        arch_row.addWidget(QLabel("Level"))
        arch_row.addWidget(self._c_level)
        form.addRow("Archive options", arch_row)

        self._c_tools = QCheckBox("Copy xdelta / 7za into patch tools/ (portable)")
        self._c_tools.setChecked(False)
        form.addRow(self._c_tools)

        self._c_portable_apply = QCheckBox(
            f"Include portable apply tool ({portable_apply_bundle_name()}) for end users"
        )
        self._c_portable_apply.setToolTip(
            "When checked, copies the pre-built portable apply binary from repo bin/ "
            "next to patch_manifest.json. Build with PyInstaller (see README and CI workflows)."
        )
        self._c_portable_apply.setChecked(False)
        self._c_portable_apply.setEnabled(sys.platform in ("win32", "linux"))
        form.addRow(self._c_portable_apply)

        self._c_overwrite = QCheckBox("Overwrite output folder if it exists")
        self._c_overwrite.setChecked(False)
        form.addRow(self._c_overwrite)

        layout.addLayout(form)

        self._c_start = QPushButton("Start")
        self._c_start.clicked.connect(self._on_create_start)
        layout.addWidget(self._c_start)

        self._c_progress = QProgressBar()
        self._c_progress.setRange(0, 0)
        layout.addWidget(self._c_progress)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setPlaceholderText("Log output…")
        layout.addWidget(self._log, stretch=1)

        return w

    def _build_apply_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        form = QFormLayout()
        self._a_game = QLineEdit()
        g_row = QHBoxLayout()
        g_row.addWidget(self._a_game)
        bg = QPushButton("Browse…")
        bg.clicked.connect(lambda: self._browse_dir(self._a_game))
        g_row.addWidget(bg)
        form.addRow("Game folder", g_row)

        self._a_patch = QLineEdit()
        p_row = QHBoxLayout()
        p_row.addWidget(self._a_patch)
        btn_folder = QPushButton("Folder…")
        btn_folder.clicked.connect(lambda: self._browse_patch_folder(self._a_patch))
        btn_arc = QPushButton("Archive…")
        btn_arc.clicked.connect(lambda: self._browse_patch_archive(self._a_patch))
        p_row.addWidget(btn_folder)
        p_row.addWidget(btn_arc)
        form.addRow("Patch folder or archive", p_row)

        self._a_backup = QCheckBox("Create backup before patching")
        self._a_backup.setChecked(True)
        form.addRow(self._a_backup)

        self._a_backup_dir = QLineEdit()
        self._a_backup_dir.setPlaceholderText("Optional: defaults to parent of game folder")
        bd_row = QHBoxLayout()
        bd_row.addWidget(self._a_backup_dir)
        bbd = QPushButton("Browse…")
        bbd.clicked.connect(lambda: self._browse_dir(self._a_backup_dir))
        bd_row.addWidget(bbd)
        form.addRow("Backup directory (optional)", bd_row)

        layout.addLayout(form)

        self._a_start = QPushButton("Apply patch")
        self._a_start.clicked.connect(self._on_apply_start)
        layout.addWidget(self._a_start)

        self._a_progress = QProgressBar()
        self._a_progress.setRange(0, 0)
        layout.addWidget(self._a_progress)

        self._apply_log = QPlainTextEdit()
        self._apply_log.setReadOnly(True)
        layout.addWidget(self._apply_log, stretch=1)

        return w

    def _engine_for_create(self) -> Engine:
        mode = self._c_preset.currentData()
        if mode == "auto":
            old = Path(self._c_old.text().strip())
            if old.is_dir():
                return detect_engine(old)
            return Engine.GENERIC
        return Engine.GENERIC

    def _on_create_start(self) -> None:
        if self._create_worker and self._create_worker.isRunning():
            return
        old = self._c_old.text().strip()
        new = self._c_new.text().strip()
        out = self._c_out.text().strip()
        if not old or not new or not out:
            QMessageBox.warning(self, "PatchSmith", "Please set old folder, new folder, and output patch folder.")
            return
        engine = self._engine_for_create()
        ign_names, ign_prefixes = ignore_overrides_for_engine(engine)

        warn_mb = float(self._c_xdelta_warn_mb.value())
        opts = CreatePatchOptions(
            old_root=Path(old),
            new_root=Path(new),
            out_patch_dir=Path(out),
            patch_name=self._c_name.text().strip() or "Patch",
            from_version=self._c_from.text().strip(),
            to_version=self._c_to.text().strip(),
            xdelta_threshold_mb=float(self._c_threshold.value()),
            xdelta_compression_level=int(self._c_xdelta_level.value()),
            large_xdelta_warn_mb=warn_mb,
            track_deletes=self._c_track_del.isChecked(),
            bundle_archive=self._c_archive.isChecked(),
            archive_format=self._c_fmt.currentData(),
            archive_compression_level=int(self._c_level.value()),
            bundle_tools=self._c_tools.isChecked(),
            bundle_portable_apply=self._c_portable_apply.isChecked(),
            overwrite=self._c_overwrite.isChecked(),
            extra_ignore_names=ign_names or None,
            extra_ignore_path_prefixes=ign_prefixes or None,
        )
        self._log.clear()
        self._append_log(f"Preset: {engine.value}")
        self._c_start.setEnabled(False)
        self._create_worker = _CreateWorker(opts)
        self._create_worker.log_line.connect(self._append_log)
        self._create_worker.finished_ok.connect(self._on_create_done)
        self._create_worker.failed.connect(self._on_create_fail)
        self._create_worker.cancelled.connect(self._on_create_cancelled)
        self._create_worker.need_confirm.connect(
            self._on_create_need_confirm,
            Qt.ConnectionType.BlockingQueuedConnection,
        )
        self._create_worker.start()

    def _on_create_done(self, archive: object) -> None:
        self._c_start.setEnabled(True)
        if archive:
            self._append_log(f"Done. Archive: {archive}")
            QMessageBox.information(self, "PatchSmith", f"Patch created.\nArchive:\n{archive}")
        else:
            self._append_log("Done.")
            QMessageBox.information(self, "PatchSmith", "Patch folder created.")

    def _on_create_fail(self, msg: str) -> None:
        self._c_start.setEnabled(True)
        self._append_log(f"ERROR: {msg}")
        QMessageBox.critical(self, "PatchSmith", msg)

    def _on_create_cancelled(self) -> None:
        self._c_start.setEnabled(True)
        self._append_log("Cancelled.")

    def _on_create_need_confirm(self, msg: str) -> None:
        if not self._create_worker:
            return
        ok = (
            QMessageBox.question(
                self,
                "PatchSmith — large xdelta jobs",
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )
        self._create_worker.set_confirm_reply(ok)

    def _on_apply_start(self) -> None:
        if self._apply_worker and self._apply_worker.isRunning():
            return
        game = self._a_game.text().strip()
        patch = self._a_patch.text().strip()
        if not game or not patch:
            QMessageBox.warning(self, "PatchSmith", "Please set game folder and patch path.")
            return
        backup_dir = self._a_backup_dir.text().strip()
        opts = ApplyPatchOptions(
            game_root=Path(game),
            patch_path=Path(patch),
            backup=self._a_backup.isChecked(),
            backup_dir=Path(backup_dir) if backup_dir else None,
        )
        self._apply_log.clear()
        self._a_start.setEnabled(False)
        self._apply_worker = _ApplyWorker(opts)
        self._apply_worker.log_line.connect(lambda s: self._apply_log.appendPlainText(s))
        self._apply_worker.finished_ok.connect(self._on_apply_done)
        self._apply_worker.failed.connect(self._on_apply_fail)
        self._apply_worker.start()

    def _on_apply_done(self) -> None:
        self._a_start.setEnabled(True)
        QMessageBox.information(self, "PatchSmith", "Patch applied successfully.")

    def _on_apply_fail(self, msg: str) -> None:
        self._a_start.setEnabled(True)
        self._apply_log.appendPlainText(f"ERROR: {msg}")
        QMessageBox.critical(self, "PatchSmith", msg)
