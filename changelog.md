
## 5.6.36




- Admin-Mitarbeiterliste ermittelt den letzten Buchungsstatus aller Mitarbeiter in einer Abfrage statt in einer je Mitarbeiter (50 statt 1 Abfragen)
- Bei gleicher Zeitmarke entscheidet die höhere Buchungs-Id, wie es bisher die Einzelabfrage getan hat
- Sicherheitsprüfung liest ihre Einstellungen nur noch einmal je Anfrage statt bis zu sechsmal (1 statt 6 Abfragen)
- Verhalten unverändert, geprüft mit 180 Kombinationen aus Pfad, Protokoll und Filterkonfiguration
- CI-Check erkennt doppelt registrierte Routen; neue Duplikate lassen den Build scheitern
- Ursache der doppelten Routen ermittelt: verschiedene Module bedienen denselben Pfad (12 Konflikte)
- CI-Check erkennt zusätzlich Duplikate, die FastAPI wegen abweichender Funktionsnamen nicht meldet

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

