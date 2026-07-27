# EV4 QC Workbench

A local Windows-first Tkinter quality-control shell with explicit Profile isolation.

## Current production Profile

Only `CE` is registered. The Profile consumes the official CE public CLI from the exact locked `rezahh107/EV4-Constructability-Engineer-Repo` checkout. Workbench does not evaluate CE semantics or replace CE authority.

The accepted CE dependency is:

```text
branch: fix/ce-external-output-boundary
commit: ff40b2a9d801f34aad03829d0c1c24d85b5d7f08
public exporter: ev4-producer-gate-export-validator@1.1.0
entry point: validator.verified_project_gate_exporter:main
```

Branch identity alone is not accepted. Repository identity, exact commit, tracked cleanliness, public and implementation module origins, exporter ID, exporter version, and official CLI options are verified in a fresh child interpreter before CE execution.

## Windows workflow

1. Run `setup_windows.bat` once.
2. Run `launch_windows.bat`.
3. Select the exact CE checkout listed above.
4. Select a CE Review Draft, Architect Source Intake, Architect Source Bundle, and an output folder.
5. Verify the connection, then run the verified export.
6. Open the retained attempt folder.

Every original input and the selected output folder must resolve outside the selected CE checkout. A path equal to or below CE is rejected as `CE_PATH_BOUNDARY_INVALID` before attempt creation. That rejection creates no attempt, snapshot, metadata, output, settings update, or CE filesystem change.

Each operation starts a new Profile-specific Python interpreter using `sys.executable -m ev4_qc_workbench.profiles.ce.process_child`. Governed CE modules are imported only in that child after exact checkout verification. Inputs are then copied byte-for-byte into a unique Workbench attempt, and CE writes the final official artifact directly to the Workbench output path. Workbench does not construct, copy out, or reinterpret the CE artifact.

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

The validation workflow checks the exact Workbench PR Head against the named CE repair branch and exact CE commit on Linux and Windows. It also:

- preserves LF bytes for immutable Project Gate contracts on Windows and verifies their SHA-256 pins;
- proves parent `sys.modules` poisoning cannot enter the fresh CE child;
- verifies exact public and implementation module origins;
- runs authorized, blocked, invalid, and prewrite-boundary integration cases;
- compares CE Head, branch, tracked state, untracked inventory, and index before and after operations.

## Validation

```text
python -m pip install -e "[dev]"
python -m compileall -q src tests
pytest -q
git diff --check
```

The implementation and exact-pair CI do not authorize Merge. PR #1 must remain Draft until a fresh independent review is completed and the owner makes a separate merge decision.
