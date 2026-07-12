from __future__ import annotations

import html
import re
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy.orm import Session

from app.auth import current_user
from app.database import get_db
from app.routes.common import templates

router = APIRouter()
DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "manuals"

MANUALS = {
    "administrator": {
        "title": "Administratorhandbuch",
        "description": "Einrichtung, Benutzer, Rollen, Sicherheit, Backup, Updates und Wartung.",
        "file": "administrator.md",
    },
    "benutzer": {
        "title": "Benutzerhandbuch",
        "description": "Anmeldung, Zeiterfassung, Abwesenheiten, Korrekturen und persönliche Auswertungen.",
        "file": "benutzer.md",
    },
    "installation": {
        "title": "Installations- und Einrichterhandbuch",
        "description": "Debian, PostgreSQL, Installation, Erstkonfiguration, Update und Wiederherstellung.",
        "file": "installation.md",
    },
    "api": {
        "title": "API-Handbuch",
        "description": "Authentifizierung, Endpunkte, Datenformate, Fehlercodes und Beispiele.",
        "file": "api.md",
    },
}


def _require_user(request: Request, db: Session):
    user = current_user(request, db)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    return user, None


def _read_manual(slug: str) -> tuple[dict, str] | tuple[None, None]:
    meta = MANUALS.get(slug)
    if not meta:
        return None, None
    path = DOCS_ROOT / meta["file"]
    try:
        return meta, path.read_text(encoding="utf-8")
    except OSError:
        return meta, "# Dokument nicht verfügbar\n\nDie Handbuchdatei wurde nicht gefunden."


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def markdown_to_html(source: str) -> str:
    lines = source.splitlines()
    output: list[str] = []
    list_open = False
    code_open = False
    code_lines: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if code_open:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = []
                code_open = False
            else:
                if list_open:
                    output.append("</ul>")
                    list_open = False
                code_open = True
            continue
        if code_open:
            code_lines.append(raw)
            continue
        if line.startswith("# "):
            if list_open:
                output.append("</ul>"); list_open = False
            output.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            if list_open:
                output.append("</ul>"); list_open = False
            output.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            if list_open:
                output.append("</ul>"); list_open = False
            output.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("- "):
            if not list_open:
                output.append("<ul>"); list_open = True
            output.append(f"<li>{_inline(line[2:])}</li>")
        elif not line.strip():
            if list_open:
                output.append("</ul>"); list_open = False
        else:
            if list_open:
                output.append("</ul>"); list_open = False
            output.append(f"<p>{_inline(line)}</p>")
    if list_open:
        output.append("</ul>")
    if code_open:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


def _search_results(query: str) -> list[dict]:
    query = (query or "").strip().lower()
    if len(query) < 2:
        return []
    results = []
    for slug, meta in MANUALS.items():
        _, text = _read_manual(slug)
        if not text:
            continue
        lower = text.lower()
        pos = lower.find(query)
        if pos < 0:
            continue
        start = max(0, pos - 100)
        end = min(len(text), pos + len(query) + 180)
        snippet = re.sub(r"[#*`]", "", text[start:end]).replace("\n", " ").strip()
        results.append({"slug": slug, "title": meta["title"], "snippet": snippet})
    return results


@router.get("/help", response_class=HTMLResponse)
def help_index(request: Request, q: str = Query(""), db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    return templates.TemplateResponse("help_index.html", {
        "request": request,
        "user": user,
        "manuals": MANUALS,
        "query": q,
        "results": _search_results(q),
    })


@router.get("/help/{slug}", response_class=HTMLResponse)
def help_manual(slug: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    meta, source = _read_manual(slug)
    if not meta:
        return RedirectResponse("/help", status_code=303)
    return templates.TemplateResponse("help_manual.html", {
        "request": request,
        "user": user,
        "slug": slug,
        "manual": meta,
        "content_html": markdown_to_html(source),
    })


@router.get("/help/{slug}/pdf")
def help_manual_pdf(slug: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = _require_user(request, db)
    if redirect:
        return redirect
    meta, source = _read_manual(slug)
    if not meta:
        return RedirectResponse("/help", status_code=303)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallCode", parent=styles["Code"], fontSize=7.5, leading=9))
    story = [Paragraph(meta["title"], styles["Title"]), Paragraph("Stempeluhr Professional", styles["Heading2"]), Spacer(1, 6*mm)]
    in_code = False
    code: list[str] = []
    for raw in source.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(x) for x in code), styles["SmallCode"]))
                story.append(Spacer(1, 2*mm)); code = []; in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code.append(raw); continue
        if line.startswith("# "):
            story.append(Paragraph(html.escape(line[2:]), styles["Heading1"]))
        elif line.startswith("## "):
            story.append(Paragraph(html.escape(line[3:]), styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(html.escape(line[4:]), styles["Heading3"]))
        elif line.startswith("- "):
            story.append(Paragraph("• " + html.escape(line[2:]), styles["BodyText"]))
        elif line.strip():
            story.append(Paragraph(html.escape(line), styles["BodyText"]))
        else:
            story.append(Spacer(1, 2*mm))
    doc.build(story)
    buffer.seek(0)
    filename = f"stempeluhr_{slug}_5.6.15.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
