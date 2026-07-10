from .common import *

router = APIRouter()


def _bool_setting_value(value: str) -> str:
    return "1" if str(value or "").lower() in ["1", "true", "on", "ja", "yes"] else "0"

def _clamp_int(value, default: int, min_value: int, max_value: int) -> int:
    try:
        ivalue = int(value)
    except Exception:
        ivalue = default
    return max(min_value, min(ivalue, max_value))

def ensure_https_settings(db: Session):
    defaults = {
        "https_enabled": "0",
        "https_certificate_type": "self_signed",
        "https_hostname": "stempeluhr.local",
        "https_alt_names": "10.0.0.48, stempeluhr.local",
        "https_valid_days": "3650",
        "https_organization": "Stempeluhr",
        "https_redirect_http": "1",
        "https_last_cert": "",
        "https_last_status": "Noch nicht geprüft",
        "https_cert_path": "/opt/stempeluhr/certs/stempeluhr.crt",
        "https_key_path": "/opt/stempeluhr/certs/stempeluhr.key",
    }
    changed = False
    for key, value in defaults.items():
        if service_get_setting(db, key, None) is None:
            service_set_setting(db, key, value)
            changed = True
    if changed:
        db.commit()


def _https_cert_dir() -> Path:
    return Path("/opt/stempeluhr/certs")


def _https_nginx_dir() -> Path:
    return Path("/opt/stempeluhr/nginx")


def _https_status(db: Session) -> dict:
    cert_path = Path(service_get_setting(db, "https_cert_path", "/opt/stempeluhr/certs/stempeluhr.crt"))
    key_path = Path(service_get_setting(db, "https_key_path", "/opt/stempeluhr/certs/stempeluhr.key"))
    nginx_path = _https_nginx_dir() / "stempeluhr_https.conf"
    return {
        "cert_exists": cert_path.exists(),
        "key_exists": key_path.exists(),
        "cert_path": str(cert_path),
        "key_path": str(key_path),
        "nginx_config_exists": nginx_path.exists(),
        "nginx_config_path": str(nginx_path),
    }


def _split_alt_names(value: str) -> list[str]:
    names = []
    for part in re.split(r"[,;\s]+", value or ""):
        part = part.strip()
        if part and part not in names:
            names.append(part)
    return names


def _build_openssl_config(common_name: str, alt_names: list[str], organization: str) -> str:
    dns_lines = []
    ip_lines = []
    dns_idx = 1
    ip_idx = 1
    for name in alt_names:
        try:
            ipaddress.ip_address(name)
            ip_lines.append(f"IP.{ip_idx} = {name}")
            ip_idx += 1
        except Exception:
            dns_lines.append(f"DNS.{dns_idx} = {name}")
            dns_idx += 1
    if common_name and common_name not in alt_names:
        try:
            ipaddress.ip_address(common_name)
            ip_lines.append(f"IP.{ip_idx} = {common_name}")
        except Exception:
            dns_lines.append(f"DNS.{dns_idx} = {common_name}")
    org = (organization or "Stempeluhr").replace("\n", " ").replace("/", "-")
    cn = (common_name or "stempeluhr.local").replace("\n", " ").replace("/", "-")
    return """[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
C = DE
O = {org}
CN = {cn}

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
{alt}
""".format(org=org, cn=cn, alt="\n".join(dns_lines + ip_lines) or "DNS.1 = stempeluhr.local")


def _build_nginx_config(db: Session) -> str:
    settings = service_settings_dict(db)
    cert_path = settings.get("https_cert_path", "/opt/stempeluhr/certs/stempeluhr.crt")
    key_path = settings.get("https_key_path", "/opt/stempeluhr/certs/stempeluhr.key")
    server_name = settings.get("https_hostname", "stempeluhr.local") or "stempeluhr.local"
    redirect = settings.get("https_redirect_http", "1") in ["1", "true", "on", "ja"]
    http_block = f"""server {{
    listen 80;
    server_name {server_name};
    return 301 https://$host$request_uri;
}}
""" if redirect else f"""server {{
    listen 80;
    server_name {server_name};
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    return http_block + f"""
server {{
    listen 443 ssl http2;
    server_name {server_name};

    ssl_certificate {cert_path};
    ssl_certificate_key {key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }}
}}
"""


@router.get("/system/settings/https", response_class=HTMLResponse)
def system_settings_https(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_https_settings(db)
    settings = service_settings_dict(db)
    return templates.TemplateResponse("system_settings_https.html", {
        "request": request,
        "user": user,
        "settings": settings,
        "status": _https_status(db),
        "message": request.query_params.get("message", ""),
    })


@router.post("/system/settings/https/save", response_class=HTMLResponse)
def system_settings_https_save(
    request: Request,
    https_enabled: str = Form("0"),
    https_hostname: str = Form("stempeluhr.local"),
    https_alt_names: str = Form(""),
    https_valid_days: int = Form(3650),
    https_organization: str = Form("Stempeluhr"),
    https_redirect_http: str = Form("0"),
    db: Session = Depends(get_db),
):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_https_settings(db)
    hostname = (https_hostname or "stempeluhr.local").strip() or "stempeluhr.local"
    service_set_setting(db, "https_enabled", _bool_setting_value(https_enabled))
    service_set_setting(db, "https_certificate_type", "self_signed")
    service_set_setting(db, "https_hostname", hostname)
    service_set_setting(db, "https_alt_names", (https_alt_names or hostname).strip() or hostname)
    service_set_setting(db, "https_valid_days", str(_clamp_int(https_valid_days, 3650, 1, 36500)))
    service_set_setting(db, "https_organization", (https_organization or "Stempeluhr").strip() or "Stempeluhr")
    service_set_setting(db, "https_redirect_http", _bool_setting_value(https_redirect_http))
    db.commit()
    log_action(db, user.employee_number, "https_settings_saved", "settings", "https", f"Hostname: {hostname}")
    return RedirectResponse("/system/settings/https?message=HTTPS-Einstellungen%20gespeichert.", status_code=303)


@router.post("/system/settings/https/generate", response_class=HTMLResponse)
def system_settings_https_generate(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_https_settings(db)
    settings = service_settings_dict(db)
    cert_dir = _https_cert_dir()
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "stempeluhr.crt"
    key_path = cert_dir / "stempeluhr.key"
    cn = settings.get("https_hostname", "stempeluhr.local")
    alt_names = _split_alt_names(settings.get("https_alt_names", cn))
    days = _clamp_int(settings.get("https_valid_days", "3650"), 3650, 1, 36500)
    org = settings.get("https_organization", "Stempeluhr")
    cfg_path = cert_dir / "openssl_stempeluhr.cnf"
    cfg_path.write_text(_build_openssl_config(cn, alt_names, org), encoding="utf-8")
    try:
        result = subprocess.run([
            "openssl", "req", "-x509", "-nodes", "-newkey", "rsa:2048",
            "-days", str(days), "-keyout", str(key_path), "-out", str(cert_path),
            "-config", str(cfg_path)
        ], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "openssl fehlgeschlagen").strip()[:500])
        try:
            key_path.chmod(0o600)
            cert_path.chmod(0o644)
        except Exception:
            pass
        service_set_setting(db, "https_cert_path", str(cert_path))
        service_set_setting(db, "https_key_path", str(key_path))
        service_set_setting(db, "https_last_cert", datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        service_set_setting(db, "https_last_status", "Selbstsigniertes Zertifikat erzeugt")
        db.commit()
        log_action(db, user.employee_number, "https_selfsigned_generated", "settings", "https", f"CN={cn}, SAN={', '.join(alt_names)}, Tage={days}")
        message = "Selbstsigniertes Zertifikat wurde erzeugt."
    except Exception as exc:
        message = f"Zertifikat konnte nicht erzeugt werden: {exc}"
        service_set_setting(db, "https_last_status", message)
        db.commit()
    return RedirectResponse("/system/settings/https?message=" + quote(message), status_code=303)


@router.post("/system/settings/https/nginx", response_class=HTMLResponse)
def system_settings_https_nginx(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_https_settings(db)
    nginx_dir = _https_nginx_dir()
    nginx_dir.mkdir(parents=True, exist_ok=True)
    config_path = nginx_dir / "stempeluhr_https.conf"
    config_path.write_text(_build_nginx_config(db), encoding="utf-8")
    service_set_setting(db, "https_last_status", f"Nginx-Konfiguration erzeugt: {config_path}")
    db.commit()
    log_action(db, user.employee_number, "https_nginx_config_generated", "settings", "https", str(config_path))
    message = "Nginx-Konfiguration wurde erzeugt. Für Aktivierung nach /etc/nginx/sites-available kopieren und Nginx neu laden."
    return RedirectResponse("/system/settings/https?message=" + quote(message), status_code=303)


@router.post("/system/settings/https/test", response_class=HTMLResponse)
def system_settings_https_test(request: Request, db: Session = Depends(get_db)):
    user, redirect = require_system_admin_response(request, db)
    if redirect:
        return redirect
    ensure_https_settings(db)
    status = _https_status(db)
    if status["cert_exists"] and status["key_exists"]:
        message = "HTTPS-Dateien vorhanden. Zertifikat und Schlüssel wurden gefunden."
    else:
        message = "HTTPS-Dateien fehlen noch. Bitte zuerst Zertifikat erzeugen."
    service_set_setting(db, "https_last_status", message)
    db.commit()
    return RedirectResponse("/system/settings/https?message=" + quote(message), status_code=303)


@router.get("/system/settings/https/certificate")
def system_settings_https_certificate(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    ensure_https_settings(db)
    cert_path = Path(service_get_setting(db, "https_cert_path", "/opt/stempeluhr/certs/stempeluhr.crt"))
    if not cert_path.exists():
        return PlainTextResponse("Zertifikat nicht vorhanden", status_code=404)
    return FileResponse(str(cert_path), filename="stempeluhr.crt", media_type="application/x-x509-ca-cert")


@router.get("/system/settings/https/nginx-config")
def system_settings_https_nginx_config(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not is_system_admin(user):
        return RedirectResponse("/login", status_code=303)
    path = _https_nginx_dir() / "stempeluhr_https.conf"
    if not path.exists():
        return PlainTextResponse("Nginx-Konfiguration nicht vorhanden", status_code=404)
    return FileResponse(str(path), filename="stempeluhr_https.conf", media_type="text/plain")



