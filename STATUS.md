# STATUS — EV4 QC Workbench

Version: 0.1.2  
Status: ce_current_main_exact_identity_and_import_authority_repair_in_progress  
Date: 2026-07-28

```yaml
repository: rezahh107/EV4-QC-Workbench
base_branch: main
pull_request: 1
pull_request_state_observed_at_repair_preflight: open
pull_request_draft_observed_at_repair_preflight: false
production_profiles:
  - ce
ce_dependency:
  repository: rezahh107/EV4-Constructability-Engineer-Repo
  reference_branch_for_selection: main
  required_commit: bc4a901d82fcdbdb131e30058b399508262706c5
  acceptance_mode: exact_commit
  public_cli: validator.verified_project_gate_exporter:main
  public_exporter_id: ev4-producer-gate-export-validator
  public_exporter_version: 1.1.0
  read_only: true
implementation_state:
  ce_direct_external_publication: consumed_from_exact_CE_commit
  containment_preflight: before_attempt_creation
  stable_boundary_result: CE_PATH_BOUNDARY_INVALID
  boundary_rejection_attempt_path: null
  boundary_rejection_output_path: null
  child_boundary_check: preserved_defense_in_depth
  fresh_interpreter: subprocess_exec_new_python_interpreter
  isolated_mode_required: true
  inherited_PYTHONPATH: forbidden
  private_pycache_outside_CE: required
  repo_local_import_contamination: fail_closed_before_governed_import
  loaded_repo_module_bytes: verified_against_tracked_HEAD
  pre_execution_identity_recheck: required
  governed_execution_api: validator.verified_project_gate_exporter:main
  workbench_artifact_construction: false
  CE_local_temporary_output: false
  copy_out_publication: false
validation_state:
  exact_pair_workflow: validate
  static_file_records_self_current_run_ids: false
  current_evidence_authority: live_GitHub_Actions_for_exact_Workbench_head
  historical_old_pair_evidence_is_not_current_authority: true
fresh_independent_review: required_after_resulting_exact_head
owner_merge_decision: separate
merge_authorized_by_this_status: false
released: false
production_ready: false
```

## Authority boundary

The shared shell owns only Profile registration, UI lifecycle, settings, attempts, byte-copy primitives, and strict process transport. CE-specific containment remains local to `profiles/ce`. CE owns validation, evidence, Builder eligibility, Project Gate export, status, authorization, and handoff semantics.

Every original CE input and every Workbench-created output must remain outside the selected CE checkout. Boundary-invalid paths are resolved and rejected before `create_attempt`, so no attempt, input snapshot, metadata, settings write, output, or CE filesystem mutation occurs. The child repeats the boundary check independently.

The final official `ce-project-gate.json` is published directly by the exact CE public CLI to the Workbench attempt path. Workbench does not create an alternate artifact, use stdout as artifact transport, publish through a CE-local temporary file, or copy an artifact out of CE.

## Process and identity guarantees

Each Profile operation uses a separate `sys.executable` child in Python isolated mode with a private `pycache_prefix` outside CE. Caller `PYTHONPATH` is removed from the child environment. Before governed CE import, the child verifies repository root, official remote, exact required commit, tracked working-tree and staged cleanliness, and rejects untracked or ignored import-capable repository material using Python import machinery suffixes.

After governed import, every loaded executable module whose origin resolves inside CE must correspond to a tracked `HEAD` path with bytes matching the selected commit. Immediately before `validator.verified_project_gate_exporter:main` executes, exact identity and execution-relevant cleanliness are checked again. Distinct child PIDs remain supporting evidence only; PID difference alone is not isolation proof.

## Immutable-byte requirement

The exact-pair workflow preserves LF bytes before CE checkout and independently verifies the existing SHA-256 pins for both Project Gate contract files. Those files did not change between the previously accepted CE repair Head and the selected current CE `main` commit; any future byte drift must fail rather than silently repin the hashes.

## Remaining gates

This file does not assert success for a workflow that has not yet completed on its own exact Head. Live GitHub Actions is the authority for exact-pair CI. A fresh independent PR Inspector review remains required after the resulting Head is validated. Passing CI does not close findings, establish merge readiness, release the Workbench, or authorize Merge.
