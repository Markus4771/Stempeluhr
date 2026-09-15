#!/usr/bin/env python3
"""ISO-DEP/APDU Agent für sichere Stempeluhr Android-HCE-Anmeldung."""
from __future__ import annotations
import os, time
import requests

SERVER=os.getenv("STEMPELUHR_SERVER","http://127.0.0.1:8000").rstrip("/")
AID=bytes.fromhex(os.getenv("STEMPELUHR_HCE_AID","F05354454D50454C01"))
POLL_SECONDS=float(os.getenv("HCE_POLL_SECONDS","0.5"))
TERMINAL_ID=os.getenv("STEMPELUHR_TERMINAL_ID",os.uname().nodename)

def select_apdu(): return list(bytes([0,0xA4,4,0,len(AID)])+AID+bytes([0]))
def challenge_apdu(challenge:bytes): return list(bytes([0x80,0x10,0,0,len(challenge)])+challenge+bytes([0]))
def transmit_ok(connection,apdu):
    data,sw1,sw2=connection.transmit(apdu)
    if (sw1,sw2)!=(0x90,0): raise RuntimeError(f"HCE APDU fehlgeschlagen: {sw1:02X}{sw2:02X}")
    return bytes(data)
def new_challenge():
    r=requests.post(f"{SERVER}/mobile/hce/challenge",json={"terminal_id":TERMINAL_ID},timeout=10); data=r.json()
    if not r.ok: raise RuntimeError(data.get("message") or f"Challenge HTTP {r.status_code}")
    return data["challenge_id"],bytes.fromhex(data["challenge"])
def read_proof(connection):
    hello=transmit_ok(connection,select_apdu())
    if hello!=b"STEMPELUHR2": raise RuntimeError("HCE v2 wird vom Smartphone nicht unterstützt")
    challenge_id,challenge=new_challenge()
    raw=transmit_ok(connection,challenge_apdu(challenge)).decode("ascii"); parts=raw.split(":",2)
    if len(parts)!=3 or parts[0]!="PROOF": raise RuntimeError("Ungültiger HCE-Nachweis")
    return int(parts[1]),challenge_id,parts[2]
def stamp(credential_id:int,challenge_id:str,proof:str):
    r=requests.post(f"{SERVER}/mobile/hce/verify",json={"credential_id":credential_id,"challenge_id":challenge_id,"proof":proof,"terminal_id":TERMINAL_ID},timeout=10)
    try:data=r.json()
    except Exception:data={"message":r.text[:200]}
    if not r.ok:raise RuntimeError(data.get("message") or f"HTTP {r.status_code}")
    return data
def main():
    try:from smartcard.System import readers
    except ImportError as exc:raise SystemExit("pyscard fehlt. Debian: apt install python3-pyscard pcscd") from exc
    last_id=0;last_seen=0.0
    print(f"Stempeluhr HCE-Agent v2: Server={SERVER}, Terminal={TERMINAL_ID}, AID={AID.hex().upper()}")
    while True:
        try:
            available=readers()
            if not available:time.sleep(3);continue
            c=available[0].createConnection();c.connect();credential_id,challenge_id,proof=read_proof(c);now=time.monotonic()
            if credential_id!=last_id or now-last_seen>8:
                result=stamp(credential_id,challenge_id,proof);print(result.get("message","Buchung erfolgreich"));last_id,last_seen=credential_id,now
        except KeyboardInterrupt:return 0
        except Exception as exc:
            text=str(exc)
            if "Card is not connected" not in text and "No card" not in text:print(f"HCE: {text}")
        time.sleep(POLL_SECONDS)
if __name__=="__main__":raise SystemExit(main())
