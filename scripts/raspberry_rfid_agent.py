#!/usr/bin/env python3
"""Raspberry-Terminal-Agent für entferntes RFID-/NFC-Anlernen."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

SERVER = os.getenv("STEMPELUHR_SERVER", "http://127.0.0.1:8000").rstrip("/")
HOSTNAME = os.getenv("RASPBERRY_HOSTNAME", socket.gethostname())
DEVICE = os.getenv("RFID_INPUT_DEVICE", "").strip()
AGENT_VERSION = "1.1.0"
HEARTBEAT_SECONDS = int(os.getenv("HEARTBEAT_SECONDS", "5"))
SCAN_TIMEOUT = int(os.getenv("RFID_SCAN_TIMEOUT", "35"))
DISPLAY_ENABLED = os.getenv("RFID_DISPLAY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DISPLAY_USER = os.getenv("RFID_DISPLAY_USER", "pi").strip() or "pi"
DISPLAY = os.getenv("RFID_DISPLAY", ":0").strip() or ":0"
WAYLAND_DISPLAY = os.getenv("RFID_WAYLAND_DISPLAY", "wayland-0").strip()
XDG_RUNTIME_DIR = os.getenv("RFID_XDG_RUNTIME_DIR", "").strip()
SUCCESS_SECONDS = int(os.getenv("RFID_SUCCESS_SECONDS", "3"))

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
        "chromium_running": subprocess.run(["pgrep", "-f", "chromium"], capture_output=True).returncode == 0,
        "last_log": f"RFID-Agent aktiv; Gerät={DEVICE or 'nicht konfiguriert'}; Display={'aktiv' if DISPLAY_ENABLED else 'aus'}",
    }
    response = requests.post(f"{SERVER}/api/v1/raspberry/heartbeat-json", json=payload, timeout=10)
    response.raise_for_status()
    return response.json().get("command")


def send_result(command: str, result: dict) -> None:
    requests.post(
        f"{SERVER}/api/v1/raspberry/command-result",
        json={"hostname": HOSTNAME, "command": command, "result": json.dumps(result, ensure_ascii=False)},
        timeout=10,
    ).raise_for_status()


def chromium_binary() -> str | None:
    for name in ("chromium", "chromium-browser"):
        path = subprocess.run(["sh", "-lc", f"command -v {name}"], capture_output=True, text=True).stdout.strip()
        if path:
            return path
    return None


def display_command(url: str) -> list[str] | None:
    browser = chromium_binary()
    if not DISPLAY_ENABLED or not browser:
        return None
    env_parts = [f"DISPLAY={DISPLAY}"]
    if WAYLAND_DISPLAY:
        env_parts.append(f"WAYLAND_DISPLAY={WAYLAND_DISPLAY}")
    if XDG_RUNTIME_DIR:
        env_parts.append(f"XDG_RUNTIME_DIR={XDG_RUNTIME_DIR}")
    return [
        "runuser", "-u", DISPLAY_USER, "--", "env", *env_parts,
        browser,
        "--kiosk", "--no-first-run", "--disable-session-crashed-bubble",
        "--disable-infobars", "--noerrdialogs", "--disable-translate",
        "--user-data-dir=/tmp/stempeluhr-rfid-display", url,
    ]


def open_display(employee_id: int, uid: str = "") -> subprocess.Popen | None:
    url = f"{SERVER}/terminal/rfid-enrollment/{employee_id}?seconds={SCAN_TIMEOUT}"
    if uid:
        url += f"&uid={quote(uid)}"
    command = display_command(url)
    if not command:
        return None
    try:
        return subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as exc:
        print(f"Display konnte nicht geöffnet werden: {exc}", file=sys.stderr)
        return None


def close_display(process: subprocess.Popen | None) -> None:
    if not process or process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except Exception:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except Exception:
            pass


def read_uid(timeout: int) -> str:
    if not DEVICE:
        raise RuntimeError("RFID_INPUT_DEVICE ist nicht konfiguriert")
    try:
        from evdev import InputDevice, categorize, ecodes
    except ImportError as exc:
        raise RuntimeError("python3-evdev fehlt; bitte Stempeluhr-Paket neu installieren") from exc

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
        device.close()


def handle(command: str) -> None:
    if not command.startswith("rfid_scan:"):
        return
    parts = command.split(":", 2)
    if len(parts) != 3:
        return
    try:
        employee_id = int(parts[1])
    except ValueError:
        return
    token = parts[2]
    waiting_display = open_display(employee_id)
    try:
        uid = read_uid(SCAN_TIMEOUT)
        send_result(command, {"status": "complete", "token": token, "uid": uid, "reader": DEVICE})
        close_display(waiting_display)
        success_display = open_display(employee_id, uid)
        print(f"RFID-Anlernen erfolgreich beendet: UID={uid}")
        time.sleep(max(1, SUCCESS_SECONDS))
        close_display(success_display)
    except Exception as exc:
        send_result(command, {"status": "error", "token": token, "message": str(exc)})
        close_display(waiting_display)
        print(f"RFID-Anlernen beendet: {exc}", file=sys.stderr)


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
