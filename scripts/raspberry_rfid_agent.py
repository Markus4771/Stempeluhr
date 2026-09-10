#!/usr/bin/env python3
"""Stempeluhr-Terminal-Agent mit Protokoll 1.0 und pluginbasiertem Anlernmodus."""
from __future__ import annotations

import json
import os
import pwd
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

SERVER = os.getenv("STEMPELUHR_SERVER", "http://127.0.0.1:8000").rstrip("/")
HOSTNAME = os.getenv("TERMINAL_CODE", os.getenv("RASPBERRY_HOSTNAME", socket.gethostname())).strip()
TERMINAL_NAME = os.getenv("TERMINAL_NAME", HOSTNAME).strip()
DEVICE = os.getenv("RFID_INPUT_DEVICE", "").strip()
AGENT_VERSION = "2.1.0"
PROTOCOL_VERSION = "1.0"
HEARTBEAT_SECONDS = int(os.getenv("HEARTBEAT_SECONDS", "5"))
SCAN_TIMEOUT = int(os.getenv("RFID_SCAN_TIMEOUT", "35"))
DISPLAY_ENABLED = os.getenv("RFID_DISPLAY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DISPLAY_USER = os.getenv("RFID_DISPLAY_USER", "pi").strip() or "pi"
DISPLAY = os.getenv("RFID_DISPLAY", ":0").strip() or ":0"
WAYLAND_DISPLAY = os.getenv("RFID_WAYLAND_DISPLAY", "wayland-0").strip()
XDG_RUNTIME_DIR = os.getenv("RFID_XDG_RUNTIME_DIR", "").strip()
SUCCESS_SECONDS = int(os.getenv("RFID_SUCCESS_SECONDS", "3"))
STATE_FILE = Path(os.getenv("TERMINAL_STATE_FILE", "/var/lib/stempeluhr/terminal-state.json"))
LEGACY_STATE_FILE = Path("/etc/stempeluhr/terminal-state.json")

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


def chromium_binary() -> str | None:
    for name in ("chromium", "chromium-browser"):
        path = subprocess.run(["sh", "-lc", f"command -v {name}"], capture_output=True, text=True).stdout.strip()
        if path:
            return path
    return None


def detect_capabilities() -> list:
    capabilities: list = []
    browser = chromium_binary()
    if DISPLAY_ENABLED and browser:
        capabilities.append({"name": "display", "details": {"browser": Path(browser).name}})
    if DEVICE and Path(DEVICE).exists():
        capabilities.extend([
            {"name": "rfid", "details": {"input_device": DEVICE, "mode": "keyboard-wedge"}},
            {"name": "nfc", "details": {"input_device": DEVICE, "mode": "keyboard-wedge", "limited": True}},
        ])
    if Path("/dev/video0").exists():
        capabilities.append({"name": "camera", "details": {"device": "/dev/video0"}})
    if subprocess.run(["sh", "-lc", "command -v bluetoothctl"], capture_output=True).returncode == 0:
        capabilities.append("bluetooth")
    capabilities.append("offline_buffer")
    return capabilities


def load_state() -> dict:
    for path in (STATE_FILE, LEGACY_STATE_FILE):
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_FILE)


def register_v2() -> dict:
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "terminal_code": HOSTNAME,
        "hostname": socket.gethostname(),
        "name": TERMINAL_NAME,
        "ip_address": ip_address(),
        "agent_version": AGENT_VERSION,
        "capabilities": detect_capabilities(),
    }
    response = requests.post(f"{SERVER}/api/v2/terminals/register", json=payload, timeout=10)
    response.raise_for_status()
    data = response.json()
    state = load_state()
    state.update({
        "terminal_id": data.get("terminal_id"),
        "terminal_code": HOSTNAME,
        "api_key": data.get("api_key") or state.get("api_key"),
        "protocol_version": data.get("protocol_version", PROTOCOL_VERSION),
        "registered_at": int(time.time()),
    })
    save_state(state)
    return state


def heartbeat_v2(state: dict) -> dict:
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "terminal_code": HOSTNAME,
        "api_key": state.get("api_key", ""),
        "ip_address": ip_address(),
        "agent_version": AGENT_VERSION,
    }
    response = requests.post(f"{SERVER}/api/v2/terminals/heartbeat", json=payload, timeout=10)
    if response.status_code in (403, 409):
        print(f"Terminal-Schlüssel ungültig oder Registrierung erforderlich (HTTP {response.status_code}); registriere neu.")
        return register_v2()
    response.raise_for_status()
    return state


def heartbeat_legacy() -> str | None:
    payload = {
        "hostname": HOSTNAME,
        "ip_address": ip_address(),
        "agent_version": AGENT_VERSION,
        "app_version": "6.0.0",
        "debian_version": Path("/etc/debian_version").read_text().strip() if Path("/etc/debian_version").exists() else "",
        "chromium_running": subprocess.run(["pgrep", "-f", "chromium"], capture_output=True).returncode == 0,
        "last_log": f"Terminal-Agent aktiv; Protokoll={PROTOCOL_VERSION}; Gerät={DEVICE or 'nicht konfiguriert'}",
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


def _desktop_runtime_dir() -> str:
    if XDG_RUNTIME_DIR:
        return XDG_RUNTIME_DIR
    try:
        uid = pwd.getpwnam(DISPLAY_USER).pw_uid
        candidate = Path(f"/run/user/{uid}")
        if candidate.exists():
            return str(candidate)
    except Exception:
        pass
    return ""


def display_command(url: str) -> list[str] | None:
    browser = chromium_binary()
    if not DISPLAY_ENABLED or not browser:
        return None
    env_parts = [f"DISPLAY={DISPLAY}"]
    runtime_dir = _desktop_runtime_dir()
    if runtime_dir:
        env_parts.append(f"XDG_RUNTIME_DIR={runtime_dir}")
        bus = Path(runtime_dir) / "bus"
        if bus.exists():
            env_parts.append(f"DBUS_SESSION_BUS_ADDRESS=unix:path={bus}")
    if WAYLAND_DISPLAY:
        env_parts.append(f"WAYLAND_DISPLAY={WAYLAND_DISPLAY}")
    return [
        "runuser", "-u", DISPLAY_USER, "--", "env", *env_parts,
        browser, "--kiosk", "--no-first-run", "--disable-session-crashed-bubble",
        "--disable-infobars", "--noerrdialogs", "--disable-translate",
        "--user-data-dir=/tmp/stempeluhr-auth-enrollment", url,
    ]


def open_display(plugin_key: str, employee_id: int, identifier: str = "", message: str = "") -> subprocess.Popen | None:
    url = f"{SERVER}/terminal/auth-enrollment/{quote(plugin_key)}/{employee_id}?seconds={SCAN_TIMEOUT}"
    if identifier:
        url += f"&identifier={quote(identifier)}"
    if message:
        url += f"&message={quote(message)}"
    command = display_command(url)
    if not command:
        print("Terminal-Anzeige nicht verfügbar (Chromium/Display-Konfiguration prüfen)", file=sys.stderr)
        return None
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print(f"Anlern-GUI geöffnet: Plugin={plugin_key}, PID={process.pid}")
        return process
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
        raise RuntimeError("python3-evdev fehlt; bitte Terminal-Paket neu installieren") from exc

    device = InputDevice(DEVICE)
    try:
        buffer: list[str] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            import select
            ready, _, _ = select.select([device.fd], [], [], max(0.1, deadline - time.monotonic()))
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


def _parse_enrollment_command(command: str) -> tuple[str, int, str] | None:
    if command.startswith("auth_enroll:"):
        parts = command.split(":", 3)
        if len(parts) != 4:
            return None
        try:
            return parts[1], int(parts[2]), parts[3]
        except ValueError:
            return None
    if command.startswith("rfid_scan:"):
        parts = command.split(":", 2)
        if len(parts) != 3:
            return None
        try:
            return "rfid", int(parts[1]), parts[2]
        except ValueError:
            return None
    return None


def handle(command: str) -> None:
    parsed = _parse_enrollment_command(command)
    if not parsed:
        return
    plugin_key, employee_id, token = parsed

    if plugin_key != "rfid":
        message = (
            "Dieses Gerät verwendet ein sicheres Pairing. Eine zufällige NFC-UID wird nicht gespeichert."
        )
        process = open_display(plugin_key, employee_id, message=message)
        try:
            send_result(command, {
                "status": "pairing_required",
                "token": token,
                "provider": plugin_key,
                "message": message,
            })
            time.sleep(max(1, min(SUCCESS_SECONDS + 2, 8)))
        finally:
            close_display(process)
        return

    waiting_display = open_display("rfid", employee_id)
    try:
        uid = read_uid(SCAN_TIMEOUT)
        send_result(command, {
            "status": "complete",
            "token": token,
            "provider": "rfid",
            "uid": uid,
            "reader": DEVICE,
        })
        close_display(waiting_display)
        success_display = open_display("rfid", employee_id, uid)
        print(f"Anlernen erfolgreich beendet: UID={uid}")
        time.sleep(max(1, SUCCESS_SECONDS))
        close_display(success_display)
    except Exception as exc:
        try:
            send_result(command, {"status": "error", "token": token, "provider": "rfid", "message": str(exc)})
        except Exception as result_exc:
            print(f"Fehler konnte nicht an Server gemeldet werden: {result_exc}", file=sys.stderr)
        close_display(waiting_display)
        print(f"Anlernen beendet: {exc}", file=sys.stderr)


def main() -> int:
    print(f"Stempeluhr Terminal Agent {AGENT_VERSION}: Server={SERVER}, Terminal={HOSTNAME}, State={STATE_FILE}")
    state: dict = load_state()
    while True:
        try:
            if not state or not state.get("api_key"):
                state = register_v2()
                print(f"Terminal registriert: ID={state.get('terminal_id')}, Protokoll={state.get('protocol_version')}")
            state = heartbeat_v2(state)
            command = heartbeat_legacy()
            if command:
                handle(str(command))
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            print(f"Agent-Fehler: {exc}", file=sys.stderr)
            state = load_state()
        time.sleep(HEARTBEAT_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
