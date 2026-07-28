# EV4 QC Workbench

A local Windows-first Tkinter quality-control shell with explicit Profile isolation.

## Current production Profile

Only `CE` is registered. The Profile consumes the official CE public CLI from the exact locked `rezahh107/EV4-Constructability-Engineer-Repo` checkout. Workbench does not evaluate CE semantics or replace CE authority.

The accepted CE dependency is:

```text
reference branch used to select the accepted commit: main
required exact commit: bc4a901d82fcdbdb131e30058b399508262706c5
public exporter: ev4-producer-gate-export-validator@1.1.0
entry point: validator.verified_project_gate_exporter:main
```

`main` is only the reference from which the accepted commit is selected. Branch identity, exporter version, or content equivalence alone is never Runtime acceptance. Repository identity and exact commit equality remain mandatory.

## Windows workflow

1. Run `setup_windows.bat` once.
2. Run `launch_windows.bat`.
3. Select a CE checkout whose `HEAD` is the exact required commit listed above.
4. Select a CE Review Draft, Architect Source Intake, Architect Source Bundle, and an output folder.
5. Verify the connection, then run the verified export.
6. Open the retained attempt folder.

Every original input and the selected output folder must resolve outside the selected CE checkout. A path equal to or below CE is rejected as `CE_PATH_BOUNDARY_INVALID` before attempt creation. That rejection creates no attempt, snapshot, metadata, output, settings update, or CE filesystem change.

Each operation starts one new Profile-specific interpreter using `sys.executable -I -X pycache_prefix=<private-temp-path> -m ev4_qc_workbench.profiles.ce.process_child`. The child does not inherit caller `PYTHONPATH`, verifies isolated mode before governed CE import, and keeps bytecode cache outside the CE checkout. Before CE import it verifies repository identity, exact commit, tracked/index cleanliness, and rejects untracked or ignored repo-local import-capable source, bytecode, or extension material. After import it proves every executable module origin inside CE is tracked at `HEAD` with matching bytes, then rechecks execution authority immediately before the official CE `main(argv)` call.

Inputs are copied byte-for-byte into a unique Workbench attempt, and CE writes the final official artifact directly to the Workbench output path. Workbench does not construct, copy out, or reinterpret the CE artifact.

Official CLI exits remain distinct:

- `0`: authorized, valid artifact written externally;
- `2`: valid artifact written externally with handoff blocked;
- `1`: invalid input, no consumable artifact written.

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

## Exact-pair CI

The `validate` workflow selects CE from `main`, requires that selected reference to equal the exact locked commit, and tests that same Workbench/CE pair on Linux and Windows. It also:

- preserves LF bytes for immutable Project Gate contracts on Windows and verifies their SHA-256 pins;
- proves parent `sys.modules` and parent `PYTHONPATH` poisoning cannot become child execution authority;
- rejects untracked/ignored repo-local import-capable poison before governed CE import;
- verifies all loaded executable module origins inside CE against tracked `HEAD` bytes;
- runs authorized, blocked, invalid, and prewrite-boundary integration cases on both platforms;
- compares CE Head, tracked/untracked/ignored state, and index before and after operations.

## Validation

```text
python -m pip install -e ".[dev]"
python -m compileall -q src tests
pytest -q
git diff --check
```

Static repository text does not predeclare future CI conclusions. The current exact-pair result is determined from the live GitHub Actions run attached to the exact Workbench Head. Passing implementation tests or CI does not close findings, establish merge readiness, or authorize Merge. A fresh independent PR Inspector review remains a separate gate.
