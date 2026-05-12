"""PatchSmith application entry (PySide6 GUI)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication

        from patcher.gui.main_window import MainWindow
    except ImportError as e:
        print("PySide6 is required. Install with: pip install -r requirements.txt", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
