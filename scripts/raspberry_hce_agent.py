#!/usr/bin/env python3
"""ISO-DEP/APDU Leser für Stempeluhr Android-HCE.

Dieser Prozess ist bewusst vom bestehenden keyboard-wedge RFID-Agent getrennt.
Er benötigt einen PC/SC-kompatiblen NFC-Leser und pyscard.
"""
from __future__ import annotations

import os
import time
import requests

SERVER = os.getenv("STEMPELUHR_SERVER", "http://127.0.0.1:8000").rstrip("/")
AID = bytes.fromhex(os.getenv("STEMPELUHR_HCE_AID", "F05354454D50454C01"))
POLL_SECONDS = float(os.getenv("HCE_POLL_SECONDS", "0.5"))


def select_apdu() -> list[int]:
    return list(bytes([0x00, 0xA4, 0x04, 0x00, len(AID)]) + AID + bytes([0x00]))


def read_token(connection) -> str:
    data, sw1, sw2 = connection.transmit(select_apdu())
    if (sw1, sw2) != (0x90, 0x00):
        raise RuntimeError(f"HCE-App nicht selektiert: {sw1:02X}{sw2:02X}")
    raw = bytes(data)
    if not raw.startswith(b"STEMPELUHR1:"):
        raise RuntimeError("Ungültige HCE-Antwort")
    token = raw[len(b"STEMPELUHR1:"):].decode("utf-8").strip()
    if not token:
        raise RuntimeError("Leerer Geräte-Token")
    return token


def stamp(token: str) -> dict:
    response = requests.post(
        f"{SERVER}/mobile/clock",
        data={"device_token": token, "action": "auto"},
        timeout=10,
    )
    try:
        payload = response.json()
    except Exception:
        payload = {"message": response.text[:200]}
    if not response.ok:
        raise RuntimeError(payload.get("message") or f"HTTP {response.status_code}")
    return payload


def main() -> int:
    try:
        from smartcard.System import readers
    except ImportError as exc:
        raise SystemExit("pyscard fehlt. Debian: apt install python3-pyscard pcscd") from exc

    last_token = ""
    last_seen = 0.0
    print(f"Stempeluhr HCE-Agent: Server={SERVER}, AID={AID.hex().upper()}")
    while True:
        try:
            available = readers()
            if not available:
                print("Kein PC/SC-NFC-Leser gefunden")
                time.sleep(3)
                continue
            connection = available[0].createConnection()
            connection.connect()
            token = read_token(connection)
            now = time.monotonic()
            if token != last_token or now - last_seen > 8:
                result = stamp(token)
                print(result.get("message", "Buchung erfolgreich"))
                last_token, last_seen = token, now
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            text = str(exc)
            if "Card is not connected" not in text and "No card" not in text:
                print(f"HCE: {text}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
