import pytest

from ev4_qc_workbench.profile_registry import ProfileDescriptor, ProfileRegistry, ProfileRegistryError, production_registry
from ev4_qc_workbench.profiles.ce.tab import create_ce_tab


def test_production_registry_contains_only_ce():
    registry = production_registry()
    assert [item.profile_id for item in registry.ordered()] == ["ce"]
    assert registry.get("ce").display_name == "CE"


def test_registry_rejects_duplicate_unknown_and_arbitrary_module():
    valid = production_registry().get("ce")
    with pytest.raises(ProfileRegistryError):
        ProfileRegistry((valid, valid))
    with pytest.raises(ProfileRegistryError):
        production_registry().get("architect")
    with pytest.raises(ProfileRegistryError):
        ProfileRegistry((ProfileDescriptor("ce", "CE", "attacker.child", create_ce_tab),))
