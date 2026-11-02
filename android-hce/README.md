# Stempeluhr Android HCE

Android-Komponente für die Smartphone-Anmeldung am Raspberry-Terminal.

## Protokoll

AID: `F05354454D50454C01`

Der Terminal-Leser selektiert die Stempeluhr-Anwendung per ISO-DEP/APDU. Danach liefert die Android-HCE-App einen Anwendungsnachweis. Eine wechselnde NFC-UID des Smartphones wird nicht als Identität verwendet.

Die erste Implementierungsstufe verwendet den beim Pairing erzeugten `mobile_app`-Geräte-Token. Für den produktiven Betrieb ist als nächster Sicherheitsschritt Challenge/Response vorgesehen, damit ein mitgeschnittener APDU-Datensatz nicht wiederverwendet werden kann.

## Hardware-Hinweis

Der derzeitige Raspberry-Agent erkennt den vorhandenen Leser als `keyboard-wedge`. Ein solcher Leser liefert nur eine UID/Tastatureingabe und kann keine ISO-DEP/APDU-Kommunikation mit Android HCE durchführen. Für HCE muss am Terminal ein PC/SC- oder PN532-kompatibler Leser verwendet werden. Der bestehende RFID-Keyboard-Wedge-Pfad bleibt parallel erhalten.
