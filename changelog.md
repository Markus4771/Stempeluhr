## 5.7.0

- modernes responsives Design für die RFID-/NFC-Medienverwaltung ergänzt
- Raspberry-Terminal kann direkt in der Medienverwaltung ausgewählt und geprüft werden
- Anlernauftrag wird vom Server an den ausgewählten Raspberry Pi übertragen
- Browser fragt den Scanstatus automatisch ab und übernimmt die gelesene UID
- Zeitüberschreitung und verständliche Fehleranzeigen für Offline-Terminals ergänzt
- eigenständiger Raspberry-RFID-Agent mit Heartbeat und Linux-evdev-Unterstützung ergänzt
- Installationsskript und systemd-Dienst für den RFID-Agent ergänzt
- letzte Verwendung eines RFID-/NFC-Mediums wird in der Übersicht angezeigt

## 5.6.34

- Backup-Erstellung mit Manifest, SHA256-Prüfsumme und Integritätsprüfung repariert
- leere oder unvollständige PostgreSQL-Dumps werden als Fehler erkannt
- Backups werden atomar über eine temporäre Datei erstellt
- Prüfsummen werden bei SMB-/NAS-Zielen mitkopiert und bei der Rotation berücksichtigt
- mehrere RFID-/NFC-Medien pro Mitarbeiter ergänzt
- bestehende RFID-Zuordnungen werden automatisch in das neue Medienmodell übernommen
- UID-Normalisierung für Karten, Smartphones, Smartwatches und NFC-Ringe ergänzt
- neue Verwaltungsseite für RFID-/NFC-Medien pro Mitarbeiter ergänzt
- letzte Verwendung eines Mediums wird protokolliert

## 5.6.33

- Urlaubsberechnung verbindlich auf eine 5-Tage-Woche umgestellt
- Samstage und Sonntage werden nicht mehr als Urlaubstage abgezogen
- volle Feiertage werden übersprungen, halbe Feiertage mit 0,5 Tagen berücksichtigt
- Berechnung wird bei jedem Speichern eines Antrags serverseitig erzwungen
- Modelle für feste 5-Tage-Woche, feste Teilzeit, unregelmäßige Jahresarbeitstage und manuellen Anspruch ergänzt
- Eintritt und Austritt können automatisch nach vollen Beschäftigungsmonaten berücksichtigt werden
- Arbeitszeitwechsel im laufenden Jahr werden über Zeitabschnitte berechnet
- getrennte Konten für Jahresurlaub, Resturlaub, Zusatzurlaub und Sonderurlaub ergänzt
- revisionssicheres Urlaubskonten-Journal ergänzt
- Krankheit während genehmigten Urlaubs kann mit Rückbuchung umgewandelt werden
- Betriebsferien können für Firma oder Abteilung hinterlegt werden
- neue Administrationsseite unter `/vacation/management`

## 5.6.32

- Dashboard-Zeiterfassung um Pausen ergänzt
- aktive Stempelgründe im Dashboard ergänzt
- personenbezogene Freigabe bleibt erhalten

## 5.6.31

- Dashboard-Buchung für bestehende Mitarbeiter standardmäßig verfügbar
- Freigabe je Mitarbeiter verwaltbar
- Überstunden aus Arbeitszeitdaten berechnet
- CSV und PDF verwenden Kommen- und Gehen-Zeiten
