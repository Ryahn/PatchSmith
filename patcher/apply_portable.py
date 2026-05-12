"""Entry point for the portable Windows apply-only tool (PySide6)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication

        from patcher.gui.portable_apply_window import PortableApplyWindow
    except ImportError as e:
        print("PySide6 is required.", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    win = PortableApplyWindow()
    win.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
