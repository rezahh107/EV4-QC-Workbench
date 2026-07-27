# STATUS — EV4 QC Workbench

Version: 0.1.1  
Status: ce_profile_final_repair_exact_pair_ci_confirmed_review_pending  
Date: 2026-07-28

```yaml
repository: rezahh107/EV4-QC-Workbench
base_branch: main
pull_request: 1
pull_request_state: open_draft
reference_workbench_head: 30843d4beb3bebc557678e5778be7240ef8a5b4b
final_workbench_head: 4dfb7003ad3b1ca135c9954734ab98f2ad9322ca
production_profiles:
  - ce
ce_dependency:
  repository: rezahh107/EV4-Constructability-Engineer-Repo
  draft_pull_request: 48
  branch: fix/ce-external-output-boundary
  required_commit: ff40b2a9d801f34aad03829d0c1c24d85b5d7f08
  acceptance_mode: exact_commit
  public_cli: validator.verified_project_gate_exporter:main
  public_exporter_id: ev4-producer-gate-export-validator
  public_exporter_version: 1.1.0
  read_only: true
implementation_state:
  ce_direct_external_publication: consumed_from_exact_repaired_CE_head
  containment_preflight: before_attempt_creation
  stable_boundary_result: CE_PATH_BOUNDARY_INVALID
  boundary_rejection_attempt_path: null
  boundary_rejection_output_path: null
  child_boundary_check: preserved_defense_in_depth
  fresh_interpreter: subprocess_exec_new_python_interpreter
  governed_import_after_checkout_verification: true
  parent_runtime_state_inheritance: prohibited_and_tested
  workbench_artifact_construction: false
  CE_local_temporary_output: false
  copy_out_publication: false
validation_state:
  exact_pair_workflow: validate
  final_exact_head_run:
    run_id: 30309558857
    tested_workbench_head: 4dfb7003ad3b1ca135c9954734ab98f2ad9322ca
    CE_head: ff40b2a9d801f34aad03829d0c1c24d85b5d7f08
    CE_branch: fix/ce-external-output-boundary
    platform_independent_job:
      job_id: 90121755018
      conclusion: success
    windows_exact_head_job:
      job_id: 90121755044
      conclusion: success
  authorized_external_export: observed_success
  valid_blocked_external_export: observed_success
  invalid_external_export_without_artifact: observed_success
  CE_read_only_before_after_equality: observed_success
  immutable_contract_LF_checkout_and_hash_assertions: observed_success
  complete_workbench_regression: observed_success
conditional_validation:
  directory_symlink_to_CE:
    linux_fixture: executed_required_test
    linux_result: passed
    windows_fixture: conditional_on_environment
fresh_independent_review: required
owner_merge_decision: required_after_valid_review
merge_authorized: false
released: false
production_ready: false
```

## Authority boundary

The shared shell owns only Profile registration, UI lifecycle, settings, attempts, byte-copy primitives, and strict process transport. CE-specific containment remains local to `profiles/ce`. CE owns validation, evidence, Builder eligibility, Project Gate export, status, authorization, and handoff semantics.

Every original CE input and every Workbench-created output must remain outside the selected CE checkout. Boundary-invalid paths are resolved and rejected before `create_attempt`, so no attempt, input snapshot, metadata, settings write, output, or CE filesystem mutation occurs. The child repeats the boundary check independently.

The final official `ce-project-gate.json` is published directly by the exact CE public CLI to the Workbench attempt path. Workbench does not create an alternate artifact, use stdout as artifact transport, publish through a CE-local temporary file, or copy an artifact out of CE.

## Process and identity guarantees

Each operation uses one new interpreter through:

```text
sys.executable -m ev4_qc_workbench.profiles.ce.process_child
```

The child verifies the repository remote, exact commit, tracked cleanliness, public and implementation file origins, official option surface, exporter ID, and exporter version before importing governed CE Runtime modules. Parent `sys.modules` poisoning is tested and cannot cross the subprocess-exec boundary. Distinct child PIDs are supporting evidence, not the sole proof of isolation.

## Windows immutable-byte requirement

The exact-pair workflow disables line-ending conversion before checking out CE. It then verifies the immutable SHA-256 pins for both vendored Project Gate contracts. This prevents Windows CRLF conversion from changing authority-bearing contract bytes while leaving the CE dependency unmodified.

## Remaining gates

A fresh independent PR Inspector review and a separate owner merge decision remain required. Passing CI does not close findings, make the PR production-ready, or authorize Merge.

No Architect, Builder, Responsive, Project Gate, Decision Kernel, or PR Inspector Profile is present. Stage-QC settings are not read or migrated.
