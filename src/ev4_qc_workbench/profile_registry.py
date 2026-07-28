from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ProfileDescriptor:
    profile_id: str
    display_name: str
    child_module: str
    tab_factory: Callable[[Any, Any], Any]


class ProfileRegistryError(ValueError):
    pass


class ProfileRegistry:
    def __init__(self, descriptors: tuple[ProfileDescriptor, ...]):
        if not descriptors:
            raise ProfileRegistryError("At least one code-owned Profile is required")
        items: dict[str, ProfileDescriptor] = {}
        for descriptor in descriptors:
            profile_id = descriptor.profile_id
            expected_prefix = f"ev4_qc_workbench.profiles.{profile_id}."
            if (
                not profile_id
                or profile_id in items
                or not descriptor.display_name
                or not descriptor.child_module.startswith(expected_prefix)
                or not callable(descriptor.tab_factory)
                or not descriptor.tab_factory.__module__.startswith(expected_prefix)
            ):
                raise ProfileRegistryError("PROFILE_REGISTRY_INVALID")
            items[profile_id] = descriptor
        self._items = items
        self._order = tuple(item.profile_id for item in descriptors)

    def get(self, profile_id: str) -> ProfileDescriptor:
        try:
            return self._items[profile_id]
        except KeyError as exc:
            raise ProfileRegistryError("UNKNOWN_PROFILE") from exc

    def ordered(self) -> tuple[ProfileDescriptor, ...]:
        return tuple(self._items[item] for item in self._order)


def production_registry() -> ProfileRegistry:
    from .profiles.ce.descriptor import CE_PROFILE

    return ProfileRegistry((CE_PROFILE,))
