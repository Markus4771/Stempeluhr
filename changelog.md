## 5.6.29

- Dashboard rollenabhängig reduziert
- Mitarbeiter sehen nur persönliche Kennzahlen und persönliche Buchungsfunktionen
- Teamleiter sehen Anwesenheit und offene Vorgänge ihres Bereichs
- Personal und Administratoren sehen übergreifende Vorgänge
- Backup- und Systeminformationen werden nur Administratoren angezeigt
- letzte Buchungen, Namensliste der Anwesenden und letzte Aktivitäten aus der normalen Mitarbeiteransicht entfernt
- optionale Eigenbuchung für angemeldete Benutzer ergänzt
- Eigenbuchung akzeptiert nur Kommen und Gehen für das eigene Konto
- Konfiguration unter Allgemeine Einstellungen ergänzt
- Zustandsprüfung, Doppelbuchungsschutz und Audit-Protokoll bleiben aktiv

## 5.6.28

- Dashboard verwendet für Anwesenheit und aktive Mitarbeiter dieselbe Datenbasis
- widersprüchliche Verhältnis- und Unterzeilenanzeige entfernt
- doppelte Kachel `Heute nicht anwesend` entfernt
- Systemstatus nennt den konkreten Hauptgrund statt pauschal `Handlungsbedarf`
- Backup-Alter wird verständlich in Stunden oder Tagen angezeigt
- E-Mail- und GitHub-Hinweise beeinflussen den roten Gesamtstatus nicht mehr
- Kacheltexte wurden gekürzt und übersichtlicher gestaltet

## 5.6.27

- Dashboard zeigt Anwesenheit als Verhältnis aus anwesenden und aktiven Mitarbeitern
- Buchungen des Tages werden nach Kommen, Gehen und Pause aufgeschlüsselt
- Plausibilitätsmeldungen und Backup-Alter erhalten Warnstufen
- Überstunden werden rollenbezogen dargestellt
- Systemstatus prüft zusätzlich Speicherplatz, E-Mail-Konfiguration und GitHub-Token

## 5.6.26

- frühere Raspberry-Kiosk-Oberfläche mit RFID-Feld und vier großen Buchungstasten wiederhergestellt
- automatische Buchung nach Wartezeit bleibt erhalten
- optionale Stempelgründe kompakt in das alte Kiosk-Layout integriert
- RFID-Lernmodus und Kiosk-Links bleiben erhalten

## 5.6.25

- Hauptmenüpunkt `Zusatz-Programme` wird bei leerer oder nicht sichtbarer Programmliste vollständig aus dem DOM entfernt
- Fehler der Sichtbarkeitsprüfung blenden den Menüpunkt sicher aus
- Rollen- und Aktivitätsfilter bleiben unverändert aktiv

## 5.6.24

- Hauptmenüpunkt `Zusatz-Programme` wird ohne hinterlegte Programme ausgeblendet
- Stempelgründe unterstützen reine Personenstatus ohne Arbeitszeitbuchung
- Personenstatus kann über einen eigenen Grund zurückgesetzt werden
- Statusänderungen werden getrennt von Kommen-, Gehen- und Pausenbuchungen gespeichert

## 5.6.23

- Zusatz-Programme erhalten konfigurierbare Rollenfreigaben
- Report-Webansicht, CSV, PDF und E-Mail-Anhang filtern zukünftige und unvollständige Tage einheitlich

## 5.6.22

- GitHub-Updater kann bei fehlendem Release auf den aktuellen Branch `main` zurückgreifen

## 5.6.21

- Kommen- und Gehen-Uhrzeiten werden direkt in `Auswertung & Reporting` angezeigt

## 5.6.20

- Plausibilitätsmeldungen können zurückgesetzt werden
- Überstundenverwaltung mit Mitarbeiterfreigabe per E-Mail ergänzt
