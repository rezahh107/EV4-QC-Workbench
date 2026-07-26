# AGENTS.md

## Repository role

`EV4-QC-Workbench` is a local Windows-first Tkinter shell that hosts explicit repository-specific Profiles. It is a consumer and orchestrator, never a replacement authority.

## Current production scope

The production registry contains exactly one Profile: `ce`.

CE validation, evidence, Builder eligibility, Project Gate export, status, authorization, and handoff semantics remain solely owned by `rezahh107/EV4-Constructability-Engineer-Repo`. The only production CE execution surface is `validator.verified_project_gate_exporter:main` from the exact checkout declared by `src/ev4_qc_workbench/profiles/ce/ce-profile.lock.json`.

## Hard boundaries

- Do not add shared evaluators, shared Runtime authority, generic status semantics, or dynamic plugin discovery.
- Do not copy or reinterpret CE validator logic.
- Do not call CE private implementation functions.
- Do not import governed CE modules in the Tkinter parent, shared shell, or shared transport.
- Every CE operation must use `sys.executable -m ev4_qc_workbench.profiles.ce.process_child`, execute one operation, and exit.
- Verify exact CE repository identity, exact commit, tracked working-tree cleanliness, public CLI identity, and module origins before CE import.
- Untracked CE metadata is not an automatic connection rejection.
- Workbench inputs and outputs must remain outside the CE repository.
- No second production Profile or placeholder tab is authorized in this work unit.

## Change and validation rules

Use focused branches. Do not modify the CE dependency. Avoid unrelated refactoring, dependency upgrades, release work, installers, telemetry, authentication, signing, databases, or web services.

Run:

```text
python -m pip install -e ".[dev]"
python -m compileall -q src tests
pytest -q
git diff --check
```

Report only executed evidence. Local tests do not prove exact-head CI. Exact-head CI does not prove independent review or authorize Merge.
