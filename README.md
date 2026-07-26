# EV4 QC Workbench

A local Windows-first Tkinter quality-control shell with explicit Profile isolation.

## Current production Profile

Only `CE` is registered. The Profile consumes the official CE public CLI from the exact locked `rezahh107/EV4-Constructability-Engineer-Repo` checkout. Workbench does not evaluate CE semantics or replace CE authority.

## Windows workflow

1. Run `setup_windows.bat` once.
2. Run `launch_windows.bat`.
3. Select the exact CE checkout at commit `0e7d8756c8452113d42e8f50fc9489b240a01bfe`.
4. Select a CE Review Draft, Architect Source Intake, Architect Source Bundle, and an output folder.
5. Verify the connection, then run the verified export.
6. Open the retained attempt folder.

Each operation starts a fresh Profile-specific Python interpreter. Inputs are copied byte-for-byte into a unique attempt before the official CLI runs. Exit `0`, `2`, and `1` remain distinct as authorized, valid-blocked, and invalid outcomes.

## Attempt output

```text
<output-folder>/ev4-qc-results/attempt-####/
├── input-snapshot/
├── generated-artifacts/ce-project-gate.json
├── generated-artifacts/ce-cli-result.json
├── diagnostics.json
├── attempt-metadata.json
└── execution-summary.txt
```

## Validation

```text
python -m pip install -e ".[dev]"
python -m compileall -q src tests
pytest -q
git diff --check
```

The Workbench is not Merge-ready or operationally validated until exact-head Windows CI and fresh review are complete.
