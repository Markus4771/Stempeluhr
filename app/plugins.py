"""Plugin-Erkennung für optionale Erweiterungen."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

PLUGIN_DIR = Path("/opt/stempeluhr/plugins")


@dataclass(frozen=True)
class PluginInfo:
    key: str
    path: str
    enabled: bool
    status: str
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def discover_plugins(plugin_dir: Path = PLUGIN_DIR) -> list[PluginInfo]:
    plugins: list[PluginInfo] = []
    if not plugin_dir.exists():
        return plugins
    for child in sorted(plugin_dir.iterdir()):
        if child.name.startswith("."):
            continue
        if child.is_dir():
            enabled_marker = child / "enabled"
            plugins.append(PluginInfo(
                key=child.name,
                path=str(child),
                enabled=enabled_marker.exists(),
                status="enabled" if enabled_marker.exists() else "available",
                note="Plugin-Verzeichnis erkannt",
            ))
    return plugins


def plugins_as_dicts() -> list[dict[str, object]]:
    return [plugin.as_dict() for plugin in discover_plugins()]
