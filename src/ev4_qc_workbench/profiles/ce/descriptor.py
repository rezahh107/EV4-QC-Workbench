from __future__ import annotations

from ev4_qc_workbench.profile_registry import ProfileDescriptor

from .launcher import CHILD_MODULE
from .tab import create_ce_tab

CE_PROFILE = ProfileDescriptor(
    profile_id="ce",
    display_name="CE",
    child_module=CHILD_MODULE,
    tab_factory=create_ce_tab,
)
