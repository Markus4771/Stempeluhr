# Smartphone-NFC – Architektur und nächster Entwicklungsschritt

## Ausgangslage

Die klassische RFID-/NFC-Anmeldung der Stempeluhr 6.x arbeitet mit festen UIDs in `employee_rfid_media`. Das ist für RFID-Karten, NFC-Tags und NFC-Ringe geeignet.

Bei Smartphones ist eine beim NFC-Kontakt gelesene Kennung jedoch nicht als dauerhaft stabile Geräteidentität vorauszusetzen. Eine beim Enrollment gelesene Kennung kann sich beim nächsten Kontakt unterscheiden. Deshalb darf Smartphone-NFC nicht als normale UID-basierte Karte behandelt werden.

## Zielarchitektur

### Feste Medien

- RFID-Karten
- NFC-Tags
- NFC-Ringe

Diese bleiben unverändert in `employee_rfid_media` und werden über die bestehende zentrale RFID-/NFC-Auflösung verarbeitet.

### Smartphone

Smartphones erhalten einen eigenen Authentifizierungsweg. Die Identität wird nicht aus der NFC-UID des Telefons abgeleitet.

Geplant ist:

1. Enrollment eines Smartphones für einen Mitarbeiter.
2. Ausstellung eines zufälligen, dauerhaften Smartphone-Credentials durch die Stempeluhr.
3. Sichere Speicherung des Credentials auf dem Smartphone.
4. Übertragung eines Authentifizierungsnachweises über NFC/HCE an das Terminal.
5. Prüfung durch einen eigenen `mobile_app`-/Smartphone-Provider.
6. Zuordnung zum Mitarbeiter über `employee_auth_credentials`.
7. Möglichkeit, einzelne Smartphones unabhängig zu sperren oder neu anzulernen.

Tokens bzw. Geheimnisse werden serverseitig nicht im Klartext gespeichert. Die vorhandene generische Credential-Infrastruktur verwendet dafür gehashte Identifier.

## Trennung der Medien

```text
Mitarbeiter
  |-- RFID-Karte --------> employee_rfid_media
  |-- NFC-Tag/Ring ------> employee_rfid_media
  |-- Smartphone --------> employee_auth_credentials / mobile_app
  `-- weitere Medien ----> jeweiliger Auth-Provider
```

Damit können mehrere Anmeldemedien gleichzeitig einem Mitarbeiter gehören, ohne dass ein Smartphone die funktionierende RFID-Kartenanmeldung beeinflusst.

## Smartphone-NFC

Für die eigentliche Kommunikation zwischen Smartphone und Raspberry-Terminal ist eine Smartphone-Komponente erforderlich. Für Android ist dafür NFC Host Card Emulation (HCE) vorgesehen. Das Telefon emuliert dabei nicht einfach eine UID-Karte, sondern stellt dem Terminal einen Anwendungsdienst für die Stempeluhr-Authentifizierung bereit.

Der Raspberry-Agent benötigt entsprechend einen Smartphone-NFC-Pfad, der den Anwendungsnachweis an den Server weitergibt. Dieser Pfad muss getrennt vom bestehenden RFID-UID-Scan bleiben.

## Sicherheitsziel

Eine spätere Ausbaustufe soll statt eines statisch übertragenen Tokens ein Challenge/Response-Verfahren verwenden. Dadurch kann ein abgefangener NFC-Datensatz nicht einfach erneut zum Stempeln verwendet werden.

## Umsetzungsreihenfolge

1. Smartphone-/`mobile_app`-Provider serverseitig ergänzen.
2. Enrollment- und Widerrufs-API ergänzen.
3. Challenge/Response-Protokoll definieren.
4. Android-HCE-Komponente erstellen.
5. Raspberry-NFC-Agent um HCE/APDU-Kommunikation erweitern.
6. Terminalanzeige und Fehlerbehandlung ergänzen.
7. Integrationstest mit realem Android-Smartphone.

Die vorhandenen RFID- und festen NFC-Medien bleiben während dieser Erweiterung unverändert funktionsfähig.
