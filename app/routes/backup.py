from .common import *

router = APIRouter()

def backup_get_file_size(path: str) -> str:
    try:
        p = Path(path)
        if not p.exists():
            return "nicht vorhanden"
        size = p.stat().st_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    except Exception:
        return "unbekannt"

def backup_default_settings(db: Session):
    defaults = {
        "backup_enabled": "true",
        "backup_time": "02:00",
        "backup_daily_keep": "30",
        "backup_weekly_keep": "4",
        "backup_monthly_keep": "12",
        "backup_yearly_keep": "10",
        "backup_target": "local",
        "backup_path": str(BACKUP_DIR),
        "backup_include_database": "true",
        "backup_include_config": "true",
        "backup_include_uploads": "true",
        "backup_before_update": "true",
        "backup_before_restore": "true",
        "backup_log_audit": "true",
        "backup_last_status": "noch nicht ausgeführt",
        "backup_last_time": "",
        "backup_last_file": "",
        "backup_smb_server": "",
        "backup_smb_share": "",
        "backup_smb_path": "",
        "backup_smb_username": "",
        "backup_smb_password": "",
        "backup_smb_domain": "",
        "backup_smb_mountpoint": "/mnt/stempeluhr_backup",
    }
    changed = False
    for key, value in defaults.items():
        row = db.query(Setting).filter(Setting.key == key).first()
        if not row:
            db.add(Setting(key=key, value=value))
            changed = True
    if changed:
        db.commit()


def backup_smb_config_payload(settings: dict) -> dict:
    return {
        "server": settings.get("backup_smb_server", "").strip(),
        "share": settings.get("backup_smb_share", "").strip(),
        "subpath": settings.get("backup_smb_path", "").strip().strip("/"),
        "username": settings.get("backup_smb_username", "").strip(),
        "password": settings.get("backup_smb_password", ""),
        "domain": settings.get("backup_smb_domain", "").strip(),
        "mountpoint": settings.get("backup_smb_mountpoint", "/mnt/stempeluhr_backup").strip() or "/mnt/stempeluhr_backup",
    }

def backup_run_smb_helper(settings: dict, action: str = "configure") -> tuple[bool, str]:
    """Ruft das Root-Hilfsskript für SMB-Mount/fstab/Test auf."""
    import json
    import tempfile

    payload = backup_smb_config_payload(settings)
    if not payload["server"] or not payload["share"]:
        return False, "SMB Server und Freigabename müssen ausgefüllt sein."

    fd, tmp_path = tempfile.mkstemp(prefix="stempeluhr_smb_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"action": action, **payload}, f)

        os.chmod(tmp_path, 0o600)
        cmd = ["sudo", "-n", "/opt/stempeluhr/scripts/smb_backup_mount.sh", tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if result.returncode == 0:
            return True, output or "SMB-Konfiguration erfolgreich."
        return False, output or "SMB-Konfiguration fehlgeschlagen."
    except Exception as exc:
        return False, f"SMB-Konfiguration fehlgeschlagen: {exc}"
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass







def backup_redirect_with_message(message: str):
    from urllib.parse import quote
    return RedirectResponse(
        url="/system/settings/backup?message=" + quote(message),
        status_code=303,
    )

def backup_files_list():
    backup_root = BACKUP_DIR
    result = []
    try:
        for kind in ["daily", "weekly", "monthly", "yearly"]:
            folder = backup_root / kind
            folder.mkdir(parents=True, exist_ok=True)
            for f in sorted(folder.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
                result.append({
                    "kind": kind,
                    "name": f.name,
                    "path": str(f),
                    "size": backup_get_file_size(str(f)),
                    "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d.%m.%Y %H:%M:%S"),
                    "restore_available": True,
                })
    except Exception:
        return []
    return result

def safe_backup_file(kind: str, filename: str):
    if kind not in ["daily", "weekly", "monthly", "yearly"]:
        return None
    if "/" in filename or "\\" in filename or ".." in filename:
        return None
    path = BACKUP_DIR / kind / filename
    if not path.exists() or not path.is_file():
        return None
    return path

def backup_preview(path: Path):
    info = {"database": False, "config": False, "uploads": False, "docs": False, "version": False, "info": ""}
    try:
        with tarfile.open(path, "r:gz") as tar:
            names = tar.getnames()
            info["database"] = any(n.endswith("postgres.sql.gz") for n in names)
            info["config"] = any(n.endswith("/.env") or n.endswith(".env") for n in names)
            info["uploads"] = any("/uploads/" in n or n.endswith("/uploads") for n in names)
            info["docs"] = any("/docs/" in n or n.endswith("/docs") for n in names)
            info["version"] = any(n.endswith("version.txt") for n in names)
            for member in tar.getmembers():
                if member.name.endswith("backup_info.txt"):
                    extracted = tar.extractfile(member)
                    if extracted:
                        info["info"] = extracted.read().decode("utf-8", errors="ignore")[:2000]
                    break
    except Exception as exc:
        info["info"] = f"Backup-Vorschau fehlgeschlagen: {exc}"
    return info







@router.get("/system/settings/backup", response_class=HTMLResponse)
def system_backup(request: Request, db: Session = Depends(get_db)):
    page_message = request.query_params.get("message", "")
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    backup_default_settings(db)
    settings = service_settings_dict(db)
    backups = backup_files_list()

    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "backups": backups,
        "saved": False,
        "message": page_message
    })

@router.post("/system/settings/backup", response_class=HTMLResponse)
def system_backup_save(
    request: Request,
    backup_enabled: str = Form("off"),
    backup_time: str = Form("02:00"),
    backup_daily_keep: int = Form(30),
    backup_weekly_keep: int = Form(4),
    backup_monthly_keep: int = Form(12),
    backup_yearly_keep: int = Form(10),
    backup_path: str = Form(str(BACKUP_DIR)),
    backup_include_database: str = Form("off"),
    backup_include_config: str = Form("off"),
    backup_include_uploads: str = Form("off"),
    backup_before_update: str = Form("off"),
    backup_before_restore: str = Form("off"),
    backup_log_audit: str = Form("off"),
    backup_target: str = Form("local"),
    backup_smb_server: str = Form(""),
    backup_smb_share: str = Form(""),
    backup_smb_path: str = Form(""),
    backup_smb_username: str = Form(""),
    backup_smb_password: str = Form(""),
    backup_smb_domain: str = Form(""),
    backup_smb_mountpoint: str = Form("/mnt/stempeluhr_backup"),
    db: Session = Depends(get_db)
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    def set_setting(key, value):
        row = db.query(Setting).filter(Setting.key == key).first()
        if not row:
            db.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)

    if not re.match(r"^([01]\\d|2[0-3]):[0-5]\\d$", backup_time):
        backup_time = "02:00"

    backup_daily_keep = max(1, min(365, backup_daily_keep))
    backup_weekly_keep = max(1, min(52, backup_weekly_keep))
    backup_monthly_keep = max(1, min(120, backup_monthly_keep))
    backup_yearly_keep = max(1, min(30, backup_yearly_keep))

    set_setting("backup_enabled", "true" if backup_enabled == "on" else "false")
    set_setting("backup_time", backup_time)
    set_setting("backup_daily_keep", backup_daily_keep)
    set_setting("backup_weekly_keep", backup_weekly_keep)
    set_setting("backup_monthly_keep", backup_monthly_keep)
    set_setting("backup_yearly_keep", backup_yearly_keep)
    set_setting("backup_path", backup_path.strip() or str(BACKUP_DIR))
    set_setting("backup_target", backup_target if backup_target in ["local", "smb", "local_smb"] else "local")
    set_setting("backup_smb_server", backup_smb_server.strip())
    set_setting("backup_smb_share", backup_smb_share.strip())
    set_setting("backup_smb_path", backup_smb_path.strip())
    set_setting("backup_smb_username", backup_smb_username.strip())
    if backup_smb_password:
        set_setting("backup_smb_password", backup_smb_password)
    set_setting("backup_smb_domain", backup_smb_domain.strip())
    set_setting("backup_smb_mountpoint", backup_smb_mountpoint.strip() or "/mnt/stempeluhr_backup")
    set_setting("backup_include_database", "true" if backup_include_database == "on" else "false")
    set_setting("backup_include_config", "true" if backup_include_config == "on" else "false")
    set_setting("backup_include_uploads", "true" if backup_include_uploads == "on" else "false")
    set_setting("backup_before_update", "true" if backup_before_update == "on" else "false")
    set_setting("backup_before_restore", "true" if backup_before_restore == "on" else "false")
    set_setting("backup_log_audit", "true" if backup_log_audit == "on" else "false")

    db.commit()

    smb_message = ""
    if backup_target in ["smb", "local_smb"]:
        settings_now = {s.key: s.value for s in db.query(Setting).all()}
        ok, smb_result = backup_run_smb_helper(settings_now, "configure")
        smb_message = (" SMB/NAS: " + smb_result)
        set_setting("backup_smb_last_status", "erfolgreich" if ok else f"fehlgeschlagen: {smb_result}")
        db.commit()
        try:
            log_action(db, user.employee_number, "backup_smb_configured" if ok else "backup_smb_config_failed", "settings", "backup", smb_result)
        except Exception:
            pass

    # Timer-Datei anpassen
    try:
        hour, minute = backup_time.split(":")
        timer_content = f"""[Unit]
Description=Stempeluhr tägliches Backup

[Timer]
OnCalendar=*-*-* {hour}:{minute}:00
Persistent=true

[Install]
WantedBy=timers.target
"""
        Path("/etc/systemd/system/stempeluhr-backup.timer").write_text(timer_content, encoding="utf-8")
        subprocess.run(["systemctl", "daemon-reload"], check=False)
        if backup_enabled == "on":
            subprocess.run(["systemctl", "enable", "--now", "stempeluhr-backup.timer"], check=False)
            subprocess.run(["systemctl", "restart", "stempeluhr-backup.timer"], check=False)
        else:
            subprocess.run(["systemctl", "disable", "--now", "stempeluhr-backup.timer"], check=False)
    except Exception:
        pass

    log_action(db, user.employee_number, "backup_settings_updated", "settings", "backup", f"Zeit={backup_time}")

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "backups": backup_files_list(),
        "saved": True,
        "message": "Backup-Einstellungen gespeichert." + smb_message
    })


@router.post("/system/settings/backup/smb-test", response_class=HTMLResponse)
def system_backup_smb_test(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    backup_default_settings(db)
    settings = service_settings_dict(db)
    ok, message = backup_run_smb_helper(settings, "test")

    row = db.query(Setting).filter(Setting.key == "backup_smb_last_status").first()
    if not row:
        db.add(Setting(key="backup_smb_last_status", value="erfolgreich" if ok else f"fehlgeschlagen: {message}"))
    else:
        row.value = "erfolgreich" if ok else f"fehlgeschlagen: {message}"
    db.commit()

    try:
        log_action(db, user.employee_number, "backup_smb_test_ok" if ok else "backup_smb_test_failed", "settings", "backup", message)
    except Exception:
        pass

    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": {s.key: s.value for s in db.query(Setting).all()},
        "backups": backup_files_list(),
        "saved": ok,
        "message": ("SMB-Test erfolgreich: " if ok else "SMB-Test fehlgeschlagen: ") + message,
        "restore_preview": None,
        "restore_backup": None,
    })


@router.post("/system/settings/backup/run", response_class=HTMLResponse)
def system_backup_run(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    message = "Backup wurde gestartet."
    try:
        cmd = ["sudo", "-n", "/opt/stempeluhr/scripts/backup_root.sh", "daily"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0 and ("password" in (result.stderr or "").lower() or "sudo" in (result.stderr or "").lower()):
            result = subprocess.run(
                ["/opt/stempeluhr/scripts/backup.sh", "daily"],
                capture_output=True,
                text=True,
                timeout=300
            )
        if result.returncode == 0:
            message = "Backup erfolgreich erstellt."
            log_action(db, user.employee_number, "backup_created", "backup", "manual", result.stdout[-500:])
        else:
            message = "Backup fehlgeschlagen."
            log_action(db, user.employee_number, "backup_failed", "backup", "manual", result.stderr[-500:])
    except Exception as exc:
        message = f"Backup fehlgeschlagen: {exc}"
        log_action(db, user.employee_number, "backup_failed", "backup", "manual", str(exc))

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "backups": backup_files_list(),
        "saved": False,
        "message": message
    })

@router.post("/system/settings/backup/restore/preview/{kind}/{filename}", response_class=HTMLResponse)
def system_backup_restore_preview(kind: str, filename: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    path = safe_backup_file(kind, filename)
    message = None
    restore_preview = None
    restore_backup = None

    if not path:
        message = "Backup-Datei wurde nicht gefunden."
    else:
        restore_preview = backup_preview(path)
        restore_backup = {"kind": kind, "name": filename}
        log_action(db, user.employee_number, "backup_restore_preview", "backup", kind, filename)

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "backups": backup_files_list(),
        "saved": False,
        "message": message,
        "restore_preview": restore_preview,
        "restore_backup": restore_backup,
    })

@router.post("/system/settings/backup/restore/run/{kind}/{filename:path}", response_class=HTMLResponse)
def system_backup_restore_run(
    kind: str,
    filename: str,
    request: Request,
    confirm_restore: str = Form(""),
    restore_database: str = Form("off"),
    restore_config: str = Form("off"),
    restore_uploads: str = Form("off"),
    restore_docs: str = Form("off"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    path = safe_backup_file(kind, filename)
    message = None

    if not path:
        message = "Backup-Datei wurde nicht gefunden."
    elif confirm_restore != "WIEDERHERSTELLEN":
        message = "Restore wurde nicht ausgeführt: Bestätigung fehlt."
    elif all(v != "on" for v in [restore_database, restore_config, restore_uploads, restore_docs]):
        message = "Restore wurde nicht ausgeführt: Es wurde kein Bereich ausgewählt."
    else:
        try:
            settings = service_settings_dict(db)
            if settings.get("backup_before_restore", "true") == "true":
                subprocess.run(["sudo", "-n", "/opt/stempeluhr/scripts/backup_root.sh", "daily"], capture_output=True, text=True, timeout=300)

            cmd = [
                "sudo", "-n", "/opt/stempeluhr/scripts/restore_root.sh", str(path),
                "--database" if restore_database == "on" else "--no-database",
                "--config" if restore_config == "on" else "--no-config",
                "--uploads" if restore_uploads == "on" else "--no-uploads",
                "--docs" if restore_docs == "on" else "--no-docs",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                message = "Restore erfolgreich ausgeführt. Bitte Dienst neu starten, falls Konfiguration oder Datenbank wiederhergestellt wurde."
                log_action(db, user.employee_number, "backup_restored", "backup", kind, filename)
            else:
                message = "Restore fehlgeschlagen: " + ((result.stderr or result.stdout or "unbekannter Fehler")[-1000:])
                log_action(db, user.employee_number, "backup_restore_failed", "backup", kind, message)
        except Exception as exc:
            message = f"Restore fehlgeschlagen: {exc}"
            log_action(db, user.employee_number, "backup_restore_failed", "backup", kind, str(exc))

    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_backup.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "backups": backup_files_list(),
        "saved": False,
        "message": message,
        "restore_preview": None,
        "restore_backup": None,
    })

@router.get("/system/settings/backup/download/{kind}/{filename}")
def system_backup_download(kind: str, filename: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    path = safe_backup_file(kind, filename)
    if not path:
        return RedirectResponse("/system/settings/backup", status_code=303)

    log_action(db, user.employee_number, "backup_downloaded", "backup", kind, filename)
    return FileResponse(path, filename=filename, media_type="application/gzip")

@router.post("/system/settings/backup/delete/{kind}/{filename}")
def system_backup_delete(kind: str, filename: str, request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect

    path = safe_backup_file(kind, filename)
    if path:
        path.unlink()
        log_action(db, user.employee_number, "backup_deleted", "backup", kind, filename)

    return RedirectResponse("/system/settings/backup", status_code=303)

