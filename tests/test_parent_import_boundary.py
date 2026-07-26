import ast
import importlib
import sys
from pathlib import Path

import ev4_qc_workbench

FORBIDDEN = ("validator", "EV4-Constructability-Engineer-Repo")


def test_parent_source_has_no_governed_ce_import_or_private_call():
    root = Path(ev4_qc_workbench.__file__).resolve().parent
    parent_files = [root / "app.py", root / "process_launcher.py", root / "profile_registry.py"]
    for path in parent_files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert "_verified_project_gate_exporter_impl" not in source
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("validator") for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("validator")


def test_importing_parent_keeps_ce_modules_absent():
    importlib.import_module("ev4_qc_workbench.app")
    importlib.import_module("ev4_qc_workbench.process_launcher")
    assert not any(name == "validator" or name.startswith("validator.") for name in sys.modules)
