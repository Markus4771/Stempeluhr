"""GitHub-Release-Quelle für die bestehende Updateverwaltung."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPOSITORY = os.environ.get("STEMPELUHR_GITHUB_REPOSITORY", "Markus4771/Stempeluhr")
API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
USER_AGENT = "Stempeluhr-Professional-Updater"
TOKEN_FILE = Path(os.environ.get("STEMPELUHR_GITHUB_TOKEN_FILE", "/etc/stempeluhr/secrets/github_token"))


def _github_token() -> str:
    token = (os.environ.get("STEMPELUHR_GITHUB_TOKEN") or "").strip()
    if token:
        return token
    try:
        if TOKEN_FILE.is_file():
            return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _request(url: str, timeout: int = 20) -> bytes:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def latest_release() -> dict[str, Any]:
    try:
        payload = json.loads(_request(API_URL).decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            token_hint = (
                " Das Repository ist möglicherweise privat; dann muss ein GitHub-Token mit Leserechten "
                "in /etc/stempeluhr/secrets/github_token hinterlegt werden."
            )
            return {
                "ok": False,
                "error": (
                    "GitHub antwortet mit HTTP 404. Es wurde kein veröffentlichtes Release gefunden oder "
                    f"der Zugriff auf {REPOSITORY} ist nicht berechtigt.{token_hint}"
                ),
            }
        return {"ok": False, "error": f"GitHub antwortet mit HTTP {exc.code}."}
    except Exception as exc:
        return {"ok": False, "error": f"GitHub-Release konnte nicht gelesen werden: {exc}"}

    tag = str(payload.get("tag_name") or "").strip()
    version = tag[1:] if tag.startswith("v") else tag
    assets = []
    for asset in payload.get("assets") or []:
        assets.append({
            "name": str(asset.get("name") or ""),
            "url": str(asset.get("browser_download_url") or ""),
            "size": int(asset.get("size") or 0),
        })

    deb_name = f"stempeluhr_{version}_all.deb"
    sha_name = deb_name + ".sha256"
    deb = next((item for item in assets if item["name"] == deb_name), None)
    checksum = next((item for item in assets if item["name"] == sha_name), None)

    return {
        "ok": True,
        "tag": tag,
        "version": version,
        "name": str(payload.get("name") or tag),
        "body": str(payload.get("body") or ""),
        "published_at": str(payload.get("published_at") or ""),
        "html_url": str(payload.get("html_url") or ""),
        "deb": deb,
        "checksum": checksum,
        "assets_complete": bool(deb and checksum),
        "authenticated": bool(_github_token()),
    }


def download_release_assets(release: dict[str, Any], target_dir: Path) -> tuple[Path, str]:
    if not release.get("ok") or not release.get("assets_complete"):
        raise RuntimeError("Das GitHub Release enthält nicht alle benötigten Update-Dateien.")

    target_dir.mkdir(parents=True, exist_ok=True)
    deb_info = release["deb"]
    checksum_info = release["checksum"]
    deb_path = target_dir / Path(deb_info["name"]).name
    checksum_path = target_dir / Path(checksum_info["name"]).name

    deb_tmp = deb_path.with_suffix(deb_path.suffix + ".download")
    sha_tmp = checksum_path.with_suffix(checksum_path.suffix + ".download")
    deb_tmp.write_bytes(_request(deb_info["url"], timeout=120))
    sha_tmp.write_bytes(_request(checksum_info["url"], timeout=30))
    deb_tmp.replace(deb_path)
    sha_tmp.replace(checksum_path)
    os.chmod(deb_path, 0o644)
    os.chmod(checksum_path, 0o644)

    expected = checksum_path.read_text(encoding="utf-8", errors="ignore").strip().split()[0].lower()
    actual = hashlib.sha256(deb_path.read_bytes()).hexdigest().lower()
    if not expected or expected != actual:
        deb_path.unlink(missing_ok=True)
        raise RuntimeError("SHA256-Prüfung des GitHub-Pakets fehlgeschlagen.")

    return deb_path, actual
