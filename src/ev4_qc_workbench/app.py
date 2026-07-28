from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from .profile_registry import production_registry


class Application:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.registry = production_registry()
        self.active = False
        self._queue: queue.Queue[tuple[str, Callable[[Any, Exception | None], None], Any, Exception | None]] = queue.Queue()
        self.tabs: dict[str, Any] = {}
        root.title("EV4 QC Workbench")
        root.minsize(900, 650)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(root)
        notebook.grid(row=0, column=0, sticky="nsew")
        for descriptor in self.registry.ordered():
            tab = descriptor.tab_factory(notebook, self)
            self.tabs[descriptor.profile_id] = tab
            notebook.add(tab, text=descriptor.display_name)
        root.protocol("WM_DELETE_WINDOW", self._close)
        root.after(100, self._poll)

    def run_background(
        self,
        *,
        profile_id: str,
        operation: str,
        worker: Callable[[], Any],
        callback: Callable[[Any, Exception | None], None],
    ) -> bool:
        if self.active:
            return False
        self.registry.get(profile_id)
        self.active = True
        for tab in self.tabs.values():
            tab.set_busy(True)
        threading.Thread(
            target=self._worker,
            args=(operation, worker, callback),
            daemon=True,
        ).start()
        return True

    def _worker(self, operation: str, worker: Callable[[], Any], callback: Callable[[Any, Exception | None], None]) -> None:
        try:
            result = worker()
            error = None
        except Exception as exc:  # GUI boundary: convert unexpected failures to visible status.
            result = None
            error = exc
        self._queue.put((operation, callback, result, error))

    def _poll(self) -> None:
        try:
            _, callback, result, error = self._queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.active = False
            for tab in self.tabs.values():
                tab.set_busy(False)
            callback(result, error)
        self.root.after(100, self._poll)

    def _close(self) -> None:
        if self.active:
            messagebox.showinfo(
                "Operation active",
                "The active Profile operation must finish before closing.",
                parent=self.root,
            )
            return
        self.root.destroy()
