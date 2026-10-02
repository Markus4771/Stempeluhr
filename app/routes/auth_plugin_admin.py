from __future__ import annotations

from html import escape

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth_plugins.registry import list_plugins, set_plugin_enabled
from app.database import get_db
from .common import require_system_admin_response

router = APIRouter()


def _capabilities(items: list[str]) -> str:
    if not items:
        return "Keine besondere Terminalfähigkeit erforderlich"
    return ", ".join(escape(item) for item in items)


def _page(plugins: list[dict], message: str = "") -> str:
    cards = []
    for plugin in plugins:
        installed = bool(plugin.get("installed"))
        enabled = bool(plugin.get("enabled"))
        planned = bool(plugin.get("planned"))
        status_class = "enabled" if enabled else ("planned" if planned else "disabled")
        status_text = "Aktiv" if enabled else ("Geplant" if planned else "Deaktiviert")
        controls = ""
        if installed:
            controls = (
                f"<form method='post' action='/system/auth-plugins/{escape(plugin['key'])}/toggle'>"
                f"<input type='hidden' name='enabled' value='{'0' if enabled else '1'}'>"
                f"<button class='{'secondary' if enabled else ''}' type='submit'>"
                f"{'Deaktivieren' if enabled else 'Aktivieren'}</button></form>"
            )
        elif planned:
            controls = "<button type='button' disabled>Noch nicht installiert</button>"
        error = f"<div class='error'>{escape(str(plugin['last_error']))}</div>" if plugin.get("last_error") else ""
        cards.append(f"""
        <article class='plugin-card'>
          <div class='plugin-head'><div><h2>{escape(str(plugin.get('name') or plugin['key']))}</h2>
          <code>{escape(str(plugin['key']))}</code></div><span class='badge {status_class}'>{status_text}</span></div>
          <p>{escape(str(plugin.get('description') or ''))}</p>
          <dl>
            <div><dt>Version</dt><dd>{escape(str(plugin.get('version') or '—'))}</dd></div>
            <div><dt>Terminal-Fähigkeiten</dt><dd>{_capabilities(plugin.get('required_capabilities') or [])}</dd></div>
            <div><dt>Anlernen</dt><dd>{'Ja' if plugin.get('supports_enrollment') else 'Nein'}</dd></div>
            <div><dt>Diagnose</dt><dd>{'Ja' if plugin.get('supports_diagnostics') else 'Nein'}</dd></div>
          </dl>
          {error}<div class='actions'>{controls}</div>
        </article>""")

    return f"""<!doctype html><html lang='de'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Anmelde-Plugins</title><style>
:root{{--bg:#f4f7fb;--card:#fff;--line:#dbe3ee;--text:#172033;--muted:#667085;--blue:#1769e0;--green:#18794e;--amber:#9a6700;--red:#b42318}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}}
main{{max-width:1200px;margin:auto;padding:28px}}a{{color:var(--blue)}}h1{{margin-bottom:5px}}.intro{{color:var(--muted);max-width:850px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px;margin-top:22px}}.plugin-card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 5px 20px rgba(23,32,51,.05)}}
.plugin-head{{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}}h2{{margin:0 0 5px}}code{{color:var(--muted)}}.badge{{padding:5px 10px;border-radius:999px;font-weight:700;font-size:.85rem}}.badge.enabled{{background:#e7f6ec;color:var(--green)}}.badge.disabled{{background:#eef1f5;color:#596273}}.badge.planned{{background:#fff4d6;color:var(--amber)}}
dl{{margin:18px 0}}dl div{{display:grid;grid-template-columns:145px 1fr;border-top:1px solid var(--line);padding:9px 0}}dt{{font-weight:700}}dd{{margin:0;color:var(--muted)}}button{{border:0;border-radius:8px;padding:10px 15px;background:var(--blue);color:#fff;font-weight:700;cursor:pointer}}button.secondary{{background:#fff;color:var(--red);border:1px solid #e2a09b}}button:disabled{{background:#c7ced8;cursor:not-allowed}}.error{{background:#fff1f0;color:var(--red);padding:10px;border-radius:8px}}.msg{{background:#e8f4ff;border:1px solid #afd4ff;padding:12px;border-radius:9px;margin-top:15px}}
</style></head><body><main><a href='/system/terminals'>← Zurück zur Terminalverwaltung</a><h1>Anmelde-Plugins</h1>
<p class='intro'>Anmeldeverfahren werden unabhängig vom Stempeluhr-Kern verwaltet. Nur aktive, installierte Plugins dürfen Anmeldedaten verarbeiten.</p>
{f"<div class='msg'>{escape(message)}</div>" if message else ''}<section class='grid'>{''.join(cards)}</section></main></body></html>"""


@router.get('/system/auth-plugins', response_class=HTMLResponse)
def plugin_manager(request: Request, message: str = '', db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    return HTMLResponse(_page(list_plugins(db), message))


@router.post('/system/auth-plugins/{plugin_key}/toggle')
def toggle_plugin(plugin_key: str, request: Request, enabled: int = Form(0), db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    try:
        state = set_plugin_enabled(db, plugin_key, bool(enabled))
        message = f"Plugin {plugin_key} wurde {'aktiviert' if state.enabled else 'deaktiviert'}."
    except ValueError as exc:
        message = str(exc)
    from urllib.parse import quote
    return RedirectResponse(f'/system/auth-plugins?message={quote(message)}', status_code=303)
