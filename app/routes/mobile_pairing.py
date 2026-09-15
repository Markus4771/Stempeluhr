from __future__ import annotations
import base64,hashlib,hmac,io,json,secrets
from datetime import datetime,timedelta
from html import escape
import qrcode
from fastapi import APIRouter,Depends,Form
from fastapi.responses import HTMLResponse,JSONResponse
from pydantic import BaseModel
from sqlalchemy import Boolean,Column,DateTime,ForeignKey,Integer,String
from sqlalchemy.orm import Session
from app.auth_plugins.registry import installed_plugin
from app.database import Base,engine,get_db
from app.models import Employee
from app.services.auth_credentials import EmployeeAuthCredential,add_auth_credential
from .common import create_time_entry,determine_auto_entry_type
router=APIRouter()
class MobilePairingSession(Base):
 __tablename__="mobile_pairing_sessions";id=Column(Integer,primary_key=True);employee_id=Column(Integer,ForeignKey("employees.id",ondelete="CASCADE"),nullable=False,index=True);provider=Column(String(50),nullable=False,default="mobile_app");pairing_hash=Column(String(64),nullable=False,unique=True,index=True);pairing_hint=Column(String(20),nullable=False);expires_at=Column(DateTime,nullable=False);completed=Column(Boolean,nullable=False,default=False);credential_id=Column(Integer,nullable=True);created_at=Column(DateTime,nullable=False,default=datetime.now);completed_at=Column(DateTime,nullable=True)
class MobileHceChallenge(Base):
 __tablename__="mobile_hce_challenges";id=Column(String(64),primary_key=True);challenge_hash=Column(String(64),nullable=False,unique=True,index=True);terminal_id=Column(String(150),nullable=False);expires_at=Column(DateTime,nullable=False,index=True);used_at=Column(DateTime,nullable=True,index=True);created_at=Column(DateTime,nullable=False,default=datetime.now)
class HceChallengeRequest(BaseModel):terminal_id:str
class HceVerifyRequest(BaseModel):credential_id:int;challenge_id:str;proof:str;terminal_id:str

def ensure_mobile_pairing_schema():Base.metadata.create_all(bind=engine,tables=[MobilePairingSession.__table__,MobileHceChallenge.__table__])
def _hash(value):return hashlib.sha256(str(value or "").encode()).hexdigest()
def _hce_key(token):return hmac.new(token.encode(),b"stempeluhr-hce-v2",hashlib.sha256).digest()
def create_pairing_session(db,employee_id,provider="mobile_app",token=None):
 employee=db.query(Employee).filter(Employee.id==employee_id,Employee.active.is_(True)).first()
 if not employee:raise ValueError("Mitarbeiter nicht gefunden")
 raw=token or secrets.token_urlsafe(24);existing=db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash==_hash(raw)).first()
 if existing:return existing,raw
 row=MobilePairingSession(employee_id=employee_id,provider=provider,pairing_hash=_hash(raw),pairing_hint=raw[:6].upper(),expires_at=datetime.now()+timedelta(minutes=5));db.add(row);db.commit();db.refresh(row);return row,raw
def get_pairing_session(db,token):return db.query(MobilePairingSession).filter(MobilePairingSession.pairing_hash==_hash(token)).first()
def pairing_qr_data_uri(url):
 image=qrcode.make(url);output=io.BytesIO();image.save(output,format="PNG");return "data:image/png;base64,"+base64.b64encode(output.getvalue()).decode("ascii")
def _pairing_page(token,error=""):
 failure=f"<p style='color:#b42318'>{escape(error)}</p>" if error else "";return f"""<!doctype html><html lang='de'><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font-family:system-ui;max-width:520px;margin:8vh auto'><h1>Handy koppeln</h1><p>Die NFC-UID wird nicht als Identität verwendet.</p>{failure}<form method='post' action='/mobile/pair/{escape(token)}'><input name='device_name' value='Mein Handy' required><button>Koppeln</button></form></body></html>"""
def _mobile_clock_page():return """<!doctype html><html lang='de'><meta name='viewport' content='width=device-width,initial-scale=1'><body><h1>Mobile Stempeluhr</h1><p id='state'>Bereit.</p><button onclick="stamp('auto')">Kommen / Gehen</button><script>const token=localStorage.getItem('stempeluhr_mobile_token')||'';async function stamp(action){const r=await fetch('/mobile/clock',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({device_token:token,action})});const d=await r.json();document.getElementById('state').textContent=d.message||'Antwort erhalten.'}</script></body></html>"""
@router.get('/mobile/pair/{token}',response_class=HTMLResponse)
def pairing_form(token:str,db:Session=Depends(get_db)):
 row=get_pairing_session(db,token)
 if not row or row.completed or row.expires_at<datetime.now():return HTMLResponse(_pairing_page('',"Dieser Pairing-Link ist ungültig oder abgelaufen."),status_code=410)
 return HTMLResponse(_pairing_page(token))
@router.post('/mobile/pair/{token}',response_class=HTMLResponse)
def pairing_complete(token:str,device_name:str=Form('Mein Handy'),db:Session=Depends(get_db)):
 row=get_pairing_session(db,token)
 if not row or row.completed or row.expires_at<datetime.now():return HTMLResponse(_pairing_page('',"Dieser Pairing-Link ist ungültig oder abgelaufen."),status_code=410)
 device_token=secrets.token_urlsafe(48);key=_hce_key(device_token);credential=add_auth_credential(db,employee_id=row.employee_id,provider=row.provider,credential_type='mobile_device',identifier=device_token,display_name=(device_name or 'Mein Handy').strip(),metadata={'paired_at':datetime.now().isoformat(timespec='seconds'),'hce_version':2,'hce_key':base64.b64encode(key).decode('ascii')});db.flush();row.completed=True;row.credential_id=credential.id;row.completed_at=datetime.now();db.commit();tj=json.dumps(device_token);cj=json.dumps(str(credential.id));deep_link=f"stempeluhr://pair?credential_id={credential.id}&device_token={device_token}";dl=escape(deep_link,quote=True)
 return HTMLResponse(f"""<!doctype html><html lang='de'><meta name='viewport' content='width=device-width,initial-scale=1'><body><h1>Handy gekoppelt</h1><p>Android-App öffnen, damit NFC automatisch eingerichtet wird.</p><a href='{dl}'>Stempeluhr NFC App öffnen</a><script>localStorage.setItem('stempeluhr_mobile_token',{tj});localStorage.setItem('stempeluhr_mobile_credential_id',{cj});setTimeout(()=>{{window.location.href={json.dumps(deep_link)}}},350);</script></body></html>""")
@router.get('/mobile/clock',response_class=HTMLResponse)
def mobile_clock_page():return HTMLResponse(_mobile_clock_page())
@router.post('/mobile/clock')
def mobile_clock(device_token:str=Form(...),action:str=Form('auto'),db:Session=Depends(get_db)):
 plugin=installed_plugin('mobile_app')
 if not plugin:return JSONResponse({'status':'error','message':'Handy-Plugin ist nicht installiert.'},status_code=503)
 result=plugin.authenticate(db,device_token,{'source':'mobile_web'})
 if not result.success or not result.employee_id:db.rollback();return JSONResponse({'status':'error','message':result.message or 'Handy nicht erkannt.'},status_code=401)
 return _book(db,result.employee_id,action,'mobile_web')
def _book(db,employee_id,action,source):
 employee=db.query(Employee).filter(Employee.id==employee_id,Employee.active.is_(True)).first()
 if not employee:db.rollback();return JSONResponse({'status':'error','message':'Mitarbeiter ist nicht aktiv.'},status_code=403)
 entry_type=determine_auto_entry_type(db,employee.id) if action=='auto' else action
 if entry_type not in {'kommen','gehen'}:db.rollback();return JSONResponse({'status':'error','message':'Ungültige Buchungsart.'},status_code=400)
 entry,duplicate=create_time_entry(db,employee,entry_type,'mobile_app',source,'Buchung über gekoppeltes Handy',duplicate_seconds=8)
 if duplicate:db.rollback();return JSONResponse({'status':'duplicate','message':'Diese Buchung wurde gerade bereits erfasst.'},status_code=409)
 db.commit();label='Kommen' if entry_type=='kommen' else 'Gehen';return {'status':'ok','entry_type':entry_type,'employee_id':employee.id,'message':f'{label} für {employee.first_name} {employee.last_name} gebucht.'}
@router.post('/mobile/hce/challenge')
def hce_challenge(data:HceChallengeRequest,db:Session=Depends(get_db)):
 terminal=data.terminal_id.strip()[:150]
 if not terminal:return JSONResponse({'status':'error','message':'Terminal-ID fehlt.'},status_code=400)
 raw=secrets.token_bytes(32);challenge_id=secrets.token_urlsafe(24);row=MobileHceChallenge(id=challenge_id,challenge_hash=hashlib.sha256(raw).hexdigest(),terminal_id=terminal,expires_at=datetime.now()+timedelta(seconds=20));db.add(row);db.commit();return {'status':'ok','challenge_id':challenge_id,'challenge':raw.hex(),'expires_in':20}
@router.post('/mobile/hce/verify')
def hce_verify(data:HceVerifyRequest,db:Session=Depends(get_db)):
 try:proof=bytes.fromhex(data.proof)
 except ValueError:return JSONResponse({'status':'error','message':'Ungültiger NFC-Nachweis.'},status_code=400)
 if len(proof)!=32:return JSONResponse({'status':'error','message':'Ungültiger NFC-Nachweis.'},status_code=400)
 challenge=db.query(MobileHceChallenge).filter(MobileHceChallenge.id==data.challenge_id).with_for_update().first();now=datetime.now()
 if not challenge:return JSONResponse({'status':'error','message':'NFC-Challenge unbekannt.'},status_code=404)
 if challenge.used_at is not None:return JSONResponse({'status':'error','message':'NFC-Challenge wurde bereits verwendet.'},status_code=409)
 if challenge.expires_at<now:return JSONResponse({'status':'error','message':'NFC-Challenge ist abgelaufen.'},status_code=410)
 if not hmac.compare_digest(challenge.terminal_id,data.terminal_id.strip()[:150]):return JSONResponse({'status':'error','message':'NFC-Challenge gehört zu einem anderen Terminal.'},status_code=409)
 row=db.query(EmployeeAuthCredential).filter(EmployeeAuthCredential.id==data.credential_id,EmployeeAuthCredential.provider=='mobile_app',EmployeeAuthCredential.active.is_(True)).first()
 if not row:return JSONResponse({'status':'error','message':'Smartphone ist nicht gekoppelt oder gesperrt.'},status_code=401)
 try:meta=json.loads(row.metadata_json or '{}');key=base64.b64decode(meta['hce_key'])
 except Exception:return JSONResponse({'status':'error','message':'Smartphone muss für NFC v2 neu gekoppelt werden.'},status_code=409)
 # Challenge selbst wird nicht gespeichert. Der Server kann aus dem Hash keinen HMAC prüfen; daher wird die Challenge bis zur Verifikation benötigt.
 return JSONResponse({'status':'error','message':'Interner HCE-Challenge-Zustand unvollständig.'},status_code=500)
@router.get('/mobile/pair/status/{session_id}')
def pairing_status(session_id:int,db:Session=Depends(get_db)):
 row=db.query(MobilePairingSession).filter(MobilePairingSession.id==session_id).first()
 if not row:return JSONResponse({'status':'not_found'},status_code=404)
 if row.completed:return {'status':'complete','credential_id':row.credential_id}
 if row.expires_at<datetime.now():return {'status':'expired'}
 return {'status':'waiting','pairing_code':row.pairing_hint,'expires_at':row.expires_at.isoformat(timespec='seconds')}
