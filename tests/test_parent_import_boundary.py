import ast
import importlib
import sys
from pathlib import Path

import ev4_qc_workbench
import ev4_qc_workbench.profiles.ce.process_child as process_child

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


def test_child_source_orders_checkout_and_contamination_gates_before_runtime_import():
    source = Path(process_child.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_verify_and_import"
    )
    imports = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "importlib"
        and node.func.attr == "import_module"
    ]
    checkout_guards = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_verify_checkout_identity"
    ]
    pre_import_guards = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"_no_ce_modules_loaded", "_no_repo_modules_loaded", "_require_isolated_interpreter"}
    ]
    assert imports and checkout_guards and pre_import_guards
    assert min(checkout_guards) < min(imports)
    assert max(line for line in pre_import_guards if line < min(imports)) < min(imports)


def test_export_rechecks_execution_authority_immediately_before_public_main():
    source = Path(process_child.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_run_export"
    )
    rechecks = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_recheck_before_execution"
    ]
    public_main_calls = [
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "public"
        and node.func.attr == "main"
    ]
    assert rechecks and public_main_calls
    assert max(rechecks) < min(public_main_calls)
