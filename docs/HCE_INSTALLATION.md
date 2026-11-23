# Smartphone-NFC/HCE installieren

## Voraussetzungen am Terminal

Der bestehende Keyboard-Wedge-RFID-Leser bleibt für Karten und Tags erhalten. Android HCE benötigt zusätzlich einen PC/SC-kompatiblen NFC-Leser, der ISO-DEP/APDU unterstützt.

## Installation

```bash
cd /opt/stempeluhr
sudo sh packaging/install-hce-agent.sh
```

Prüfen:

```bash
systemctl status pcscd --no-pager
systemctl status stempeluhr-hce-agent --no-pager
pcsc_scan
journalctl -u stempeluhr-hce-agent -f
```

## Android APK

Der Workflow `.github/workflows/android-hce.yml` baut bei Änderungen unter `android-hce/` automatisch eine Debug-APK. Das Workflow-Artefakt heißt `stempeluhr-hce-debug-apk`.

## Pairing

Im Adminbereich beim Mitarbeiter ein Smartphone-Pairing starten. Nach dem Pairing müssen Credential-ID und Geräte-Token in die Android-App übernommen werden. Die HCE-v2-Kommunikation sendet den Geräte-Token nicht über NFC. Das Terminal erzeugt eine zufällige Challenge; das Smartphone antwortet mit Credential-ID und HMAC-SHA256-Nachweis.

## Sicherheit

- Smartphone-NFC-UID wird nicht als Identität verwendet.
- Geräte-Token wird serverseitig nur gehasht gespeichert.
- HCE v2 nutzt Challenge/Response.
- Wiederverwendung einer Challenge wird serverseitig abgewiesen.
- Gesperrte Geräte-Credentials werden nicht akzeptiert.
