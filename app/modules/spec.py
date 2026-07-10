"""Modul-Spezifikation für Stempeluhr Professional.

Dieses Modul definiert die gemeinsame Beschreibung eines Stempeluhr-Moduls.
Ab 5.2.07 wird diese Spezifikation von Registry, Entwicklerkonsole und
später dem automatischen Modul-Lader verwendet.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable


@dataclass(frozen=True)
class NavigationEntry:
    label: str
    href: str
    required_roles: tuple[str, ...] = ("admin",)
    order: int = 100

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StempeluhrModule:
    key: str
    title: str
    version: str = "1.0"
    status: str = "prepared"
    legacy_path: str = ""
    module_path: str = ""
    router_path: str | None = None
    navigation: tuple[NavigationEntry, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["navigation"] = [nav.as_dict() for nav in self.navigation]
        return data
