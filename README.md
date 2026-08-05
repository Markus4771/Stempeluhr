# Stempeluhr Professional 6.0.0

Webbasierte Zeiterfassung für Debian-Server und Raspberry-Pi-Terminals.

## Betriebsarten

Version 6.0 unterstützt drei offizielle Installationsvarianten aus derselben Codebasis:

- **Server:** Weboberfläche, PostgreSQL, Verwaltung, Berichte und APIs.
- **Terminal:** schlanker Hardware-Client mit Display sowie RFID-/NFC-Agent.
- **All-in-One:** Server und Terminal gemeinsam, passend zur bisherigen Raspberry-Installation.

## Pakete bauen

```bash
cd ~/Stempeluhr
bash scripts/build_packages.sh
```

Erzeugt werden:

```text
releases/stempeluhr-server_6.0.0_all.deb
releases/stempeluhr-terminal_6.0.0_all.deb
releases/stempeluhr-all-in-one_6.0.0_all.deb
```

## All-in-One installieren

```bash
sudo apt install \
  ./releases/stempeluhr-server_6.0.0_all.deb \
  ./releases/stempeluhr-terminal_6.0.0_all.deb \
  ./releases/stempeluhr-all-in-one_6.0.0_all.deb
```

Der Server ist dabei lokal unter `http://127.0.0.1:8000` eingetragen. Die bestehende PostgreSQL-Datenbank und `/etc/stempeluhr` bleiben erhalten.

## Nur Server installieren

```bash
sudo apt install ./releases/stempeluhr-server_6.0.0_all.deb
```

## Nur Terminal installieren

```bash
sudo apt install ./releases/stempeluhr-terminal_6.0.0_all.deb
sudo nano /etc/stempeluhr/terminal.env
sudo systemctl restart stempeluhr-terminal
```

Im Terminal muss `STEMPELUHR_SERVER` auf den Debian-Server zeigen, beispielsweise:

```ini
STEMPELUHR_SERVER=http://192.168.1.20:8000
```

## Kompatibilität

Die vorhandene 5.x-Anwendung wird nicht sofort intern in mehrere Repositories zerlegt. Version 6.0 trennt zunächst Installation und Dienste. Dadurch bleibt das Upgrade sicher und die gemeinsame Codebasis kann anschließend schrittweise in Server-, Terminal-, Shared- und Plugin-Module überführt werden.
