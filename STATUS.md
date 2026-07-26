# STATUS — EV4 QC Workbench

Version: 0.1.0  
Status: ce_profile_mvp_implemented_pending_exact_head_ci_and_review  
Date: 2026-07-27

```yaml
repository: rezahh107/EV4-QC-Workbench
base_branch: main
starting_head: ac246e9b72bd4d72035f2fd035c80ea0ff4b6b01
production_profiles:
  - ce
ce_dependency:
  repository: rezahh107/EV4-Constructability-Engineer-Repo
  required_commit: 0e7d8756c8452113d42e8f50fc9489b240a01bfe
  acceptance_mode: exact_commit
  public_cli: validator.verified_project_gate_exporter:main
implementation_state: implemented_on_feature_branch
local_validation:
  compileall: passed
  pytest: 18_passed_7_skipped_environment_specific
exact_head_windows_ci: pending
fresh_independent_review: pending
merge_authorized: false
released: false
production_ready: false
```

The shared shell owns only Profile registration, UI lifecycle, settings, attempts, byte-copy primitives, and strict process transport. CE owns all CE-specific semantics inside `profiles/ce` and the official CE repository remains the sole execution authority.

No Architect, Builder, Responsive, Project Gate, Decision Kernel, or PR Inspector Profile is present. Stage-QC settings are not read or migrated.
