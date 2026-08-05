#!/usr/bin/env python3
"""Raspberry-Terminal-Agent für entferntes RFID-/NFC-Anlernen.

Konfiguration über Umgebungsvariablen:
  STEMPELUHR_SERVER=http://server:8000
  RFID_INPUT_DEVICE=/dev/input/event0
  RASPBERRY_HOSTNAME=stempeluhr-terminal

Der Agent meldet sich regelmäßig per Heartbeat, holt einen Befehl
`rfid_scan:<employee_id>:<token>` ab und liest genau einen vollständigen
Tastatur-Wedge-Scan direkt vom Linux-Eingabegerät. Nach einem erfolgreichen
Scan wird der Anlernmodus sofort beendet und der Leser freigegeben.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import requests

SERVER = os.getenv("STEMPELUHR_SERVER", "http://127.0.0.1:8000").rstrip("/")
HOSTNAME = os.getenv("RASPBERRY_HOSTNAME", socket.gethostname())
DEVICE = os.getenv("RFID_INPUT_DEVICE", "").strip()
AGENT_VERSION = "1.0.1"
HEARTBEAT_SECONDS = int(os.getenv("HEARTBEAT_SECONDS", "5"))
SCAN_TIMEOUT = int(os.getenv("RFID_SCAN_TIMEOUT", "35"))

KEYS = {
    "KEY_0": "0", "KEY_1": "1", "KEY_2": "2", "KEY_3": "3", "KEY_4": "4",
    "KEY_5": "5", "KEY_6": "6", "KEY_7": "7", "KEY_8": "8", "KEY_9": "9",
    "KEY_A": "A", "KEY_B": "B", "KEY_C": "C", "KEY_D": "D", "KEY_E": "E", "KEY_F": "F",
    "KEY_G": "G", "KEY_H": "H", "KEY_I": "I", "KEY_J": "J", "KEY_K": "K", "KEY_L": "L",
    "KEY_M": "M", "KEY_N": "N", "KEY_O": "O", "KEY_P": "P", "KEY_Q": "Q", "KEY_R": "R",
    "KEY_S": "S", "KEY_T": "T", "KEY_U": "U", "KEY_V": "V", "KEY_W": "W", "KEY_X": "X",
    "KEY_Y": "Y", "KEY_Z": "Z", "KEY_MINUS": "-", "KEY_DOT": ".",
}


def ip_address() -> str:
    try:
        return subprocess.check_output(["hostname", "-I"], text=True).strip().split()[0]
    except Exception:
        return ""


def heartbeat() -> str | None:
    payload = {
        "hostname": HOSTNAME,
        "ip_address": ip_address(),
        "agent_version": AGENT_VERSION,
        "app_version": "5.7.0",
        "debian_version": Path("/etc/debian_version").read_text().strip() if Path("/etc/debian_version").exists() else "",
        "chromium_running": bool(subprocess.run(["pgrep", "-f", "chromium"], capture_output=True).returncode == 0),
        "last_log": f"RFID-Agent bereit; Gerät={DEVICE or 'nicht konfiguriert'}",
    }
    response = requests.post(f"{SERVER}/api/v1/raspberry/heartbeat-json", json=payload, timeout=10)
    response.raise_for_status()
    return response.json().get("command")


def send_result(command: str, result: dict) -> None:
    response = requests.post(
        f"{SERVER}/api/v1/raspberry/command-result",
        json={"hostname": HOSTNAME, "command": command, "result": json.dumps(result, ensure_ascii=False)},
        timeout=10,
    )
    response.raise_for_status()


def read_uid(timeout: int) -> str:
    if not DEVICE:
        raise RuntimeError("RFID_INPUT_DEVICE ist nicht konfiguriert")
    try:
        from evdev import InputDevice, categorize, ecodes
    except ImportError as exc:
        raise RuntimeError("python3-evdev fehlt") from exc

    device = InputDevice(DEVICE)
    try:
        buffer: list[str] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            import select
            ready, _, _ = select.select([device.fd], [], [], remaining)
            if not ready:
                continue
            for event in device.read():
                if event.type != ecodes.EV_KEY:
                    continue
                key = categorize(event)
                if key.keystate != key.key_down:
                    continue
                code = key.keycode[0] if isinstance(key.keycode, list) else key.keycode
                if code in ("KEY_ENTER", "KEY_KPENTER"):
                    value = "".join(buffer).strip()
                    if value:
                        return value
                    continue
                char = KEYS.get(code)
                if char:
                    buffer.append(char)
        raise TimeoutError("Innerhalb der Frist wurde kein RFID-/NFC-Medium gelesen")
    finally:
        # Der Leser wird nach Erfolg, Fehler oder Timeout immer sofort freigegeben.
        device.close()


def handle(command: str) -> None:
    if not command.startswith("rfid_scan:"):
        return
    parts = command.split(":", 2)
    if len(parts) != 3:
        return
    token = parts[2]
    try:
        uid = read_uid(SCAN_TIMEOUT)
        # Genau ein Medium erfassen. Das Ergebnis löscht serverseitig sofort
        # den pending_command und beendet damit den Anlernmodus.
        send_result(command, {
            "status": "complete",
            "token": token,
            "uid": uid,
            "reader": DEVICE,
            "enrollment_finished": True,
        })
        print(f"RFID-Anlernen erfolgreich beendet: UID={uid}")
    except Exception as exc:
        send_result(command, {
            "status": "error",
            "token": token,
            "message": str(exc),
            "enrollment_finished": True,
        })


def main() -> int:
    print(f"Raspberry RFID Agent {AGENT_VERSION}: Server={SERVER}, Host={HOSTNAME}, Gerät={DEVICE or 'nicht gesetzt'}")
    while True:
        try:
            command = heartbeat()
            if command:
                handle(str(command))
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"Agent-Fehler: {exc}", file=sys.stderr)
        time.sleep(HEARTBEAT_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
