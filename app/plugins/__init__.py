"""Plugin-Registry fuer Stempeluhr Professional."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PLUGIN_DIRS = [Path('/opt/stempeluhr/plugins')]


def _read_plugin_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return {
            'id': data.get('id') or data.get('name') or path.parent.name,
            'name': data.get('name') or path.parent.name,
            'version': data.get('version') or '',
            'description': data.get('description') or '',
            'enabled': bool(data.get('enabled', True)),
            'path': str(path.parent),
        }
    except Exception as exc:
        return {
            'id': path.parent.name,
            'name': path.parent.name,
            'version': '',
            'description': '',
            'enabled': False,
            'path': str(path.parent),
            'error': str(exc),
        }


def plugins_as_dicts() -> list[dict[str, Any]]:
    """Liefert installierte Plugins als Liste fuer Entwickler-/Monitoringseiten.

    Die Funktion ist absichtlich fehlertolerant, damit ein defektes oder
    unvollstaendiges Plugin den Start der Stempeluhr nicht verhindert.
    """
    plugins: list[dict[str, Any]] = []
    seen: set[str] = set()
    for base in PLUGIN_DIRS:
        try:
            if not base.exists():
                continue
            for manifest in sorted(base.glob('*/plugin.json')):
                item = _read_plugin_json(manifest)
                if not item:
                    continue
                key = str(item.get('id') or manifest.parent.name)
                if key in seen:
                    continue
                seen.add(key)
                plugins.append(item)
        except Exception:
            continue
    return plugins


def get_plugins_as_dicts() -> list[dict[str, Any]]:
    return plugins_as_dicts()
