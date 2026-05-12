"""Entry point for the portable apply-only tool (PySide6; Windows .exe / Linux ELF)."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import stat

        from PySide6.QtWidgets import QApplication

        from patcher.core.paths import bin_dir
        from patcher.gui.portable_apply_window import PortableApplyWindow
    except ImportError as e:
        print("PySide6 is required.", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1

    if getattr(sys, "frozen", False):
        b = bin_dir()
        if b.is_dir():
            for p in b.iterdir():
                if p.is_file():
                    try:
                        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    except OSError:
                        pass

    app = QApplication(sys.argv)
    win = PortableApplyWindow()
    win.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
