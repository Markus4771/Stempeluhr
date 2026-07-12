#!/usr/bin/env python3
"""Privilegierter Helfer zum atomaren Ändern des lokalen PostgreSQL-Passworts."""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
CONFIG_DIR=Path('/etc/stempeluhr'); ENV_FILE=CONFIG_DIR/'stempeluhr.env'; SECRETS_DIR=CONFIG_DIR/'secrets'; DB_SECRET_FILE=SECRETS_DIR/'database.conf'; BACKUP_DIR=CONFIG_DIR/'backup-secrets'; ALLOWED_NAME=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
def fail(message,code=1): print(message,file=sys.stderr); raise SystemExit(code)
def read_payload(path):
    st=path.stat()
    if not path.is_file() or st.st_mode & 0o077: fail('Übergabedatei muss eine geschützte reguläre Datei sein.')
    data=json.loads(path.read_text(encoding='utf-8')); return data if isinstance(data,dict) else {}
def write_atomic(path,content,mode=0o640):
    path.parent.mkdir(parents=True,exist_ok=True); fd,name=tempfile.mkstemp(prefix=path.name+'.',dir=str(path.parent)); temp=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle: handle.write(content); handle.flush(); os.fsync(handle.fileno())
        os.chmod(temp,mode); shutil.chown(temp,user='root',group='stempeluhr'); temp.replace(path)
    finally: temp.unlink(missing_ok=True)
def read_password(content):
    for line in (content or '').splitlines():
        if line.startswith('DATABASE_PASSWORD='): return line.split('=',1)[1]
    return None
def env_content(): return ENV_FILE.read_text(encoding='utf-8') if ENV_FILE.exists() else ''
def remove_password_from_env():
    lines=[raw for raw in env_content().splitlines() if not raw.strip().startswith('DATABASE_PASSWORD=')]; write_atomic(ENV_FILE,'\n'.join(lines).rstrip()+'\n')
def sql_literal(value): return "'"+value.replace("'","''")+"'"
def alter_role(user,password):
    quoted=user.replace('"','""'); sql=f"SET password_encryption='scram-sha-256';\nALTER ROLE \"{quoted}\" WITH LOGIN PASSWORD {sql_literal(password)};\n"
    fd,name=tempfile.mkstemp(prefix='stempeluhr-db-password-',suffix='.sql',dir='/run'); path=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as handle: handle.write(sql); handle.flush(); os.fsync(handle.fileno())
        os.chmod(path,0o600); shutil.chown(path,user='postgres',group='postgres')
        subprocess.run(['runuser','-u','postgres','--','psql','-v','ON_ERROR_STOP=1','postgres','-f',str(path)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=20)
    finally: path.unlink(missing_ok=True)
def test_connection(host,port,database,user,password):
    env=os.environ.copy(); env.update({'PGPASSWORD':password,'PGSSLMODE':'disable'}); subprocess.run(['psql','-h',host,'-p',port,'-U',user,'-d',database,'-tAc','SELECT 1'],env=env,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=20)
def main():
    if os.geteuid()!=0 or len(sys.argv)!=2: fail('Ungültiger Aufruf des Datenbank-Secret-Helfers.')
    payload_path=Path(sys.argv[1]).resolve(); allowed_root=Path('/var/lib/stempeluhr/tmp').resolve()
    if allowed_root not in payload_path.parents: fail('Ungültiger Übergabepfad.')
    payload=read_payload(payload_path); user=str(payload.get('user') or 'stempeluhr'); database=str(payload.get('database') or 'stempeluhr'); host=str(payload.get('host') or '127.0.0.1'); port=str(payload.get('port') or '5432'); password=str(payload.get('password') or '')
    if host not in {'127.0.0.1','localhost'}: fail('Nur lokale PostgreSQL-Datenbanken werden unterstützt.')
    if not ALLOWED_NAME.fullmatch(user) or not ALLOWED_NAME.fullmatch(database): fail('Ungültiger Datenbankname oder Benutzername.')
    if not port.isdigit() or not 1<=int(port)<=65535: fail('Ungültiger PostgreSQL-Port.')
    if len(password)<16 or len(password)>256: fail('Das Datenbankpasswort muss 16 bis 256 Zeichen lang sein.')
    SECRETS_DIR.mkdir(parents=True,exist_ok=True); os.chmod(SECRETS_DIR,0o750); shutil.chown(SECRETS_DIR,user='root',group='stempeluhr'); BACKUP_DIR.mkdir(parents=True,exist_ok=True); os.chmod(BACKUP_DIR,0o700)
    old_env=env_content(); old_secret=DB_SECRET_FILE.read_text(encoding='utf-8') if DB_SECRET_FILE.exists() else None; old_password=read_password(old_secret) or read_password(old_env)
    if ENV_FILE.exists(): shutil.copy2(ENV_FILE,BACKUP_DIR/'stempeluhr.env.before-db-password')
    if DB_SECRET_FILE.exists(): shutil.copy2(DB_SECRET_FILE,BACKUP_DIR/'database.conf.before-db-password')
    try:
        alter_role(user,password); test_connection(host,port,database,user,password); write_atomic(DB_SECRET_FILE,f'DATABASE_PASSWORD={password}\n'); remove_password_from_env()
    except Exception as exc:
        if old_password:
            try: alter_role(user,old_password)
            except Exception: pass
        if old_secret is not None: write_atomic(DB_SECRET_FILE,old_secret)
        write_atomic(ENV_FILE,old_env); fail(f'Datenbankpasswort konnte nicht sicher geändert werden: {type(exc).__name__}')
    finally: payload_path.unlink(missing_ok=True)
    unit=f'stempeluhr-db-secret-restart-{os.getpid()}-{int(time.time())}'
    subprocess.run(['systemd-run',f'--unit={unit}','--on-active=2s','/bin/systemctl','restart','stempeluhr.service'],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if __name__=='__main__': main()
