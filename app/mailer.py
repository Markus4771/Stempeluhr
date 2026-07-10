import smtplib
from email.message import EmailMessage
from sqlalchemy.orm import Session
from app.models import Setting

def get_email_settings(db: Session) -> dict:
    return {s.key: s.value for s in db.query(Setting).all()}

def send_email_from_settings(db: Session, to_address: str, subject: str, body: str):
    settings = get_email_settings(db)

    if settings.get("email_enabled") != "true":
        raise RuntimeError("E-Mail-Versand ist deaktiviert.")

    host = settings.get("email_smtp_host", "").strip()
    port = int(settings.get("email_smtp_port", "587") or "587")
    user = settings.get("email_smtp_user", "").strip()
    password = settings.get("email_smtp_password", "")
    from_address = settings.get("email_from_address", "").strip() or user
    from_name = settings.get("email_from_name", "Stempeluhr").strip() or "Stempeluhr"
    use_tls = settings.get("email_use_tls", "true") == "true"
    use_ssl = settings.get("email_use_ssl", "false") == "true"

    if not host:
        raise RuntimeError("SMTP-Server fehlt.")
    if not from_address:
        raise RuntimeError("Absenderadresse fehlt.")
    if not to_address:
        raise RuntimeError("Empfängeradresse fehlt.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_address}>"
    msg["To"] = to_address
    msg.set_content(body)

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)

    try:
        server.ehlo()
        if use_tls and not use_ssl:
            server.starttls()
            server.ehlo()
        if user:
            server.login(user, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass


def send_email_with_attachments_from_settings(db: Session, to_address: str, subject: str, body: str, attachments=None):
    """E-Mail mit optionalen Anhängen über die Systemeinstellungen senden.

    attachments: Liste aus Tupeln (filename, content_bytes, mime_type).
    """
    settings = get_email_settings(db)

    if settings.get("email_enabled") != "true":
        raise RuntimeError("E-Mail-Versand ist deaktiviert.")

    host = settings.get("email_smtp_host", "").strip()
    port = int(settings.get("email_smtp_port", "587") or "587")
    user = settings.get("email_smtp_user", "").strip()
    password = settings.get("email_smtp_password", "")
    from_address = settings.get("email_from_address", "").strip() or user
    from_name = settings.get("email_from_name", "Stempeluhr").strip() or "Stempeluhr"
    use_tls = settings.get("email_use_tls", "true") == "true"
    use_ssl = settings.get("email_use_ssl", "false") == "true"

    if not host:
        raise RuntimeError("SMTP-Server fehlt.")
    if not from_address:
        raise RuntimeError("Absenderadresse fehlt.")
    if not to_address:
        raise RuntimeError("Empfängeradresse fehlt.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_address}>"
    msg["To"] = to_address
    msg.set_content(body)

    for filename, content, mime_type in (attachments or []):
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)

    try:
        server.ehlo()
        if use_tls and not use_ssl:
            server.starttls()
            server.ehlo()
        if user:
            server.login(user, password)
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
