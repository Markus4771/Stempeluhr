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
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
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


def _slugify(text: str, used: set[str]) -> str:
    value = text.lower()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-") or "kapitel"
    base = value
    counter = 2
    while value in used:
        value = f"{base}-{counter}"
        counter += 1
    used.add(value)
    return value


def markdown_to_html(source: str) -> tuple[str, list[dict]]:
    lines = source.splitlines()
    output: list[str] = []
    toc: list[dict] = []
    used_ids: set[str] = set()
    list_type: str | None = None
    code_open = False
    code_language = "text"
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            output.append(f"</{list_type}>")
            list_type = None

    def close_code() -> None:
        nonlocal code_open, code_lines, code_language
        if not code_open:
            return
        payload = html.escape("\n".join(code_lines))
        language = html.escape(code_language or "text")
        output.append(
            f'<div class="help-code" data-language="{language}">'
            f'<button type="button" class="copy-code" aria-label="Code kopieren">Kopieren</button>'
            f'<pre><code class="language-{language}">{payload}</code></pre></div>'
        )
        code_open = False
        code_lines = []
        code_language = "text"

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            if code_open:
                close_code()
            else:
                close_list()
                code_open = True
                code_language = line[3:].strip() or "text"
            continue
        if code_open:
            code_lines.append(raw)
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading_match:
            close_list()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            anchor = _slugify(re.sub(r"[`*]", "", title), used_ids)
            output.append(f'<h{level} id="{anchor}">{_inline(title)}</h{level}>')
            if level >= 2:
                toc.append({"level": level, "title": re.sub(r"[`*]", "", title), "anchor": anchor})
            continue

        unordered = re.match(r"^-\s+(.+)$", line)
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if unordered or ordered:
            wanted = "ul" if unordered else "ol"
            if list_type != wanted:
                close_list()
                output.append(f"<{wanted}>")
                list_type = wanted
            item = unordered.group(1) if unordered else ordered.group(1)
            output.append(f"<li>{_inline(item)}</li>")
            continue

        if not line.strip():
            close_list()
            continue

        close_list()
        if line.startswith("> "):
            output.append(f'<div class="help-callout">{_inline(line[2:])}</div>')
        else:
            output.append(f"<p>{_inline(line)}</p>")

    close_list()
    close_code()
    return "\n".join(output), toc


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
    content_html, toc = markdown_to_html(source)
    return templates.TemplateResponse("help_manual.html", {
        "request": request,
        "user": user,
        "slug": slug,
        "manual": meta,
        "manuals": MANUALS,
        "toc": toc,
        "content_html": content_html,
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
    styles.add(ParagraphStyle(name="ReadableCode", parent=styles["Code"], fontSize=8.5, leading=11, backColor="#f3f5f7", borderColor="#cfd8e3", borderWidth=0.5, borderPadding=6, spaceBefore=6, spaceAfter=8))
    styles["BodyText"].fontSize = 10.5
    styles["BodyText"].leading = 14
    story = [Paragraph(meta["title"], styles["Title"]), Paragraph("Stempeluhr Professional 5.6.15", styles["Heading2"]), Spacer(1, 6*mm)]
    in_code = False
    code: list[str] = []
    for raw in source.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(x) for x in code), styles["ReadableCode"]))
                code = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code.append(raw)
            continue
        if line.startswith("# "):
            story.append(Paragraph(html.escape(line[2:]), styles["Heading1"]))
        elif line.startswith("## "):
            story.append(Paragraph(html.escape(line[3:]), styles["Heading2"]))
        elif line.startswith("### "):
            story.append(Paragraph(html.escape(line[4:]), styles["Heading3"]))
        elif re.match(r"^-\s+", line):
            story.append(Paragraph("• " + html.escape(line[2:]), styles["BodyText"]))
        elif re.match(r"^\d+\.\s+", line):
            story.append(Paragraph(html.escape(line), styles["BodyText"]))
        elif line.strip():
            story.append(Paragraph(html.escape(line), styles["BodyText"]))
        else:
            story.append(Spacer(1, 2*mm))
    doc.build(story)
    buffer.seek(0)
    filename = f"stempeluhr_{slug}_5.6.15.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})