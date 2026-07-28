from __future__ import annotations

import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from ev4_qc_workbench.settings import profile_settings, update_profile_settings

from .launcher import run_export, verify_connection
from .models import CEConnectionResult, CEExportResult


class CETab(ttk.Frame):
    profile_id = "ce"

    def __init__(self, parent: ttk.Notebook, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.repository = tk.StringVar()
        self.review = tk.StringVar()
        self.intake = tk.StringVar()
        self.bundle = tk.StringVar()
        self.output = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.detail = tk.StringVar(value="Select the exact CE checkout and three official inputs.")
        self.last_attempt: Path | None = None
        self._action_widgets: list[ttk.Button] = []
        self.columnconfigure(1, weight=1)
        self._build()
        self._restore()

    def _button(self, *args, **kwargs) -> ttk.Button:
        button = ttk.Button(*args, **kwargs)
        self._action_widgets.append(button)
        return button

    def _path_row(self, row: int, label: str, variable: tk.StringVar, command, button_text: str, *, file: bool) -> None:
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=5)
        ttk.Entry(self, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=4, pady=5)
        self._button(self, text=button_text, command=command).grid(row=row, column=2, sticky="e", padx=4, pady=5)

    def _build(self) -> None:
        ttk.Label(self, text="Constructability Engineer Profile", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        self._path_row(1, "CE Repository", self.repository, self.select_repository, "Select CE Repository", file=False)
        self.verify_button = self._button(self, text="Verify CE Connection", command=self.verify)
        self.verify_button.grid(row=2, column=2, sticky="e", padx=4, pady=5)
        self._path_row(3, "CE Review Draft", self.review, lambda: self.select_json(self.review), "Select Review Draft", file=True)
        self._path_row(4, "Architect Source Intake", self.intake, lambda: self.select_json(self.intake), "Select Source Intake", file=True)
        self._path_row(5, "Architect Source Bundle", self.bundle, lambda: self.select_json(self.bundle), "Select Source Bundle", file=True)
        self._path_row(6, "Output Folder", self.output, self.select_output, "Select Output Folder", file=False)
        self.run_button = self._button(self, text="Run Verified CE Export", command=self.run)
        self.run_button.grid(row=7, column=0, sticky="w", padx=4, pady=12)
        self.open_button = self._button(self, text="Open Result Folder", command=self.open_result)
        self.open_button.grid(row=7, column=1, sticky="w", padx=4, pady=12)
        self.open_button.configure(state="disabled")
        ttk.Separator(self).grid(row=8, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(self, textvariable=self.status, font=("Segoe UI", 11, "bold")).grid(row=9, column=0, columnspan=3, sticky="w")
        ttk.Label(self, textvariable=self.detail, wraplength=820, justify="left").grid(row=10, column=0, columnspan=3, sticky="w", pady=(6, 0))

    def _restore(self) -> None:
        value = profile_settings(self.profile_id)
        if isinstance(value.get("repository_path"), str):
            self.repository.set(value["repository_path"])
        else:
            sibling = Path.cwd().parent / "EV4-Constructability-Engineer-Repo"
            if sibling.is_dir():
                self.repository.set(str(sibling))
        if isinstance(value.get("output_folder"), str):
            self.output.set(value["output_folder"])

    def select_repository(self) -> None:
        path = filedialog.askdirectory(parent=self)
        if path:
            self.repository.set(path)

    def select_output(self) -> None:
        path = filedialog.askdirectory(parent=self)
        if path:
            self.output.set(path)

    def select_json(self, variable: tk.StringVar) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("JSON files", "*.json")])
        if path:
            variable.set(path)

    def set_busy(self, active: bool) -> None:
        state = "disabled" if active else "normal"
        for widget in self._action_widgets:
            widget.configure(state=state)
        if not active and self.last_attempt is None:
            self.open_button.configure(state="disabled")

    def verify(self) -> None:
        self.status.set("Verifying exact CE checkout")
        self.detail.set("A fresh CE Profile child is checking repository identity and public CLI origin.")
        self.app.run_background(
            profile_id=self.profile_id,
            operation="verify_connection",
            worker=lambda: verify_connection(Path(self.repository.get())),
            callback=self._connection_complete,
        )

    def _connection_complete(self, result: CEConnectionResult | None, error: Exception | None) -> None:
        if error or result is None:
            self.status.set("CE connection failed")
            self.detail.set(str(error))
            return
        if result.ok:
            update_profile_settings(self.profile_id, repository_path=str(result.repository_path))
            self.status.set("CE connection verified")
            self.detail.set(
                f"Code: {result.code}\nObserved commit: {result.observed_commit}\nRequired commit: {result.required_commit}\n"
                f"Child PID: {result.child_pid}\nExporter: {result.exporter_id}@{result.exporter_version}\n"
                f"Public module: {result.public_module_origin}\nImplementation module: {result.implementation_module_origin}"
            )
        else:
            self.status.set("CE connection rejected")
            self.detail.set(f"{result.code}: {result.reason}\nChild PID: {result.child_pid}")

    def run(self) -> None:
        self.status.set("Running verified CE export")
        self.detail.set("Inputs are snapshotted before a fresh CE child invokes the official public CLI.")
        self.app.run_background(
            profile_id=self.profile_id,
            operation="run_export",
            worker=lambda: run_export(
                repository_path=Path(self.repository.get()),
                review_draft_path=Path(self.review.get()),
                source_intake_path=Path(self.intake.get()),
                source_bundle_path=Path(self.bundle.get()),
                output_folder=Path(self.output.get()),
            ),
            callback=self._export_complete,
        )

    def _export_complete(self, result: CEExportResult | None, error: Exception | None) -> None:
        if error or result is None:
            self.status.set("CE export failed")
            self.detail.set(str(error))
            return
        self.last_attempt = result.attempt_path
        self.open_button.configure(state="normal" if self.last_attempt else "disabled")
        if result.attempt_path is not None and self.output.get():
            update_profile_settings(self.profile_id, output_folder=str(Path(self.output.get()).expanduser().resolve()))
        self.status.set(result.classification)
        self.detail.set(
            f"Reason: {result.reason}\nNext action: {result.next_action}\nObserved commit: {result.observed_commit}\n"
            f"Child PID: {result.child_pid}\nExporter: {result.exporter_id}\nOutput: {result.output_path}\n"
            f"handoff_allowed={result.handoff_allowed}; authorization_valid={result.authorization_valid}; output_valid={result.output_valid}"
        )

    def open_result(self) -> None:
        if not self.last_attempt:
            return
        if os.name == "nt":
            os.startfile(self.last_attempt)
        else:
            subprocess.Popen(["xdg-open", str(self.last_attempt)])


def create_ce_tab(parent, app) -> CETab:
    return CETab(parent, app)
