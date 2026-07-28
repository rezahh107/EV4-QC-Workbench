from __future__ import annotations

import tkinter as tk

from .app import Application


def main() -> int:
    root = tk.Tk()
    Application(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
