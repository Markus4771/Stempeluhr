#!/usr/bin/env python3
"""Restore-Werkzeug für Stempeluhr-Backups inklusive Secret-Verzeichnis."""
import argparse, gzip, grp, os, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
from dotenv import load_dotenv

APP_DIR=Path('/opt/stempeluhr'); CONFIG_DIR=Path('/etc/stempeluhr'); ENV_PATH=CONFIG_DIR/'stempeluhr.env'; SECRET_PATH=CONFIG_DIR/'secrets/database.conf'
if ENV_PATH.exists(): load_dotenv(ENV_PATH,override=False)
if SECRET_PATH.exists(): load_dotenv(SECRET_PATH,override=True)
DB_HOST=os.getenv('DATABASE_HOST','127.0.0.1'); DB_PORT=os.getenv('DATABASE_PORT','5432'); DB_NAME=os.getenv('DATABASE_NAME','stempeluhr'); DB_USER=os.getenv('DATABASE_USER','stempeluhr'); DB_PASSWORD=os.getenv('DATABASE_PASSWORD','')

def safe_extract(tar,target):
    root=target.resolve()
    for member in tar.getmembers():
        path=(target/member.name).resolve()
        if not str(path).startswith(str(root)): raise RuntimeError(f'Unsicherer Pfad im Backup: {member.name}')
    tar.extractall(target)
def find_first(root,name): return next(root.rglob(name),None)
def find_dir(root,name): return next((p for p in root.rglob(name) if p.is_dir() and p.name==name),None)
def restore_database(root):
    sql_gz=find_first(root,'postgres.sql.gz')
    if not sql_gz: raise RuntimeError('Im Backup wurde keine postgres.sql.gz gefunden.')
    env=os.environ.copy(); env['PGPASSWORD']=DB_PASSWORD; env['PGSSLMODE']='disable' if DB_HOST in {'127.0.0.1','localhost'} else env.get('PGSSLMODE','prefer')
    terminate="SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid();"
    subprocess.run(['psql','-h',DB_HOST,'-p',DB_PORT,'-U',DB_USER,'-d',DB_NAME,'-c',terminate],env=env,check=True)
    subprocess.run(['psql','-h',DB_HOST,'-p',DB_PORT,'-U',DB_USER,'-d',DB_NAME,'-c','DROP SCHEMA public CASCADE; CREATE SCHEMA public;'],env=env,check=True)
    proc=subprocess.Popen(['psql','-h',DB_HOST,'-p',DB_PORT,'-U',DB_USER,'-d',DB_NAME],env=env,stdin=subprocess.PIPE)
    with gzip.open(sql_gz,'rb') as src: shutil.copyfileobj(src,proc.stdin)
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError('psql Restore ist fehlgeschlagen.')
def copy_replace(src,dst):
    if not src.exists(): raise RuntimeError(f'Quelle fehlt: {src}')
    if dst.exists():
        backup=dst.with_name(dst.name+'.before_restore')
        if backup.exists(): shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
        shutil.move(str(dst),str(backup))
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(src,dst) if src.is_dir() else shutil.copy2(src,dst)
def restore_config(root):
    config=find_dir(root,'config')
    if config:
        env_file=config/'stempeluhr.env'; secrets=config/'secrets'
        if env_file.exists(): copy_replace(env_file,CONFIG_DIR/'stempeluhr.env')
        if secrets.exists(): copy_replace(secrets,CONFIG_DIR/'secrets')
    else:
        legacy=find_first(root,'.env')
        if not legacy: raise RuntimeError('Keine Konfiguration im Backup gefunden.')
        copy_replace(legacy,CONFIG_DIR/'stempeluhr.env')
    gid=grp.getgrnam('stempeluhr').gr_gid
    env_target=CONFIG_DIR/'stempeluhr.env'; os.chown(env_target,0,gid); os.chmod(env_target,0o640)
    secrets=CONFIG_DIR/'secrets'
    if secrets.exists():
        os.chown(secrets,0,gid); os.chmod(secrets,0o750)
        for path in secrets.glob('*.conf'): os.chown(path,0,gid); os.chmod(path,0o640)
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('backup_file')
    for option in ['database','config','uploads','docs']:
        parser.add_argument('--'+option,action='store_true'); parser.add_argument('--no-'+option,action='store_true')
    args=parser.parse_args(); backup=Path(args.backup_file); allowed=Path('/opt/stempeluhr/backups').resolve()
    if not backup.exists() or not backup.is_file() or not str(backup.resolve()).startswith(str(allowed)): print('Ungültige Backup-Datei.',file=sys.stderr); return 2
    with tempfile.TemporaryDirectory(prefix='stempeluhr_restore_') as tmp:
        root=Path(tmp)
        with tarfile.open(backup,'r:gz') as tar: safe_extract(tar,root)
        if args.config: restore_config(root); print('Konfiguration und Secrets wiederhergestellt.')
        if args.database: restore_database(root); print('Datenbank wiederhergestellt.')
        if args.uploads:
            src=find_dir(root,'uploads')
            if not src: raise RuntimeError('Kein uploads-Ordner im Backup gefunden.')
            copy_replace(src,APP_DIR/'app/static/uploads')
        if args.docs:
            src=find_dir(root,'docs')
            if not src: raise RuntimeError('Kein docs-Ordner im Backup gefunden.')
            copy_replace(src,APP_DIR/'docs')
    return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except Exception as exc: print(f'Restore fehlgeschlagen: {exc}',file=sys.stderr); raise SystemExit(1)
