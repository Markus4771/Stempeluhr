
## 5.6.39

- Arbeitszeitberechnung hat jetzt 106 weitere Tests: Tagesberechnung mit allen Buchungszustaenden, automatische Pausen, Feiertagsberechnung, Hilfsfunktionen und das Ueberstundenkonto.
- Die Tests sind gegengeprueft: Zwelf eingebaute Fehler in der Logik (Pausen, Feiertage, Konto) lassen die Suite wie erwartet fehlschlagen.
- Dokumentierte Inkonsistenz: die Monatszeile im Ueberstundenkonto nutzt das Namensformat "Vorname Nachname", die Mitarbeiterzeile nutzt "Nachname, Vorname". Beide stammen aus verschiedenen Stellen; eine Angleichung ist eine separate Aufgabe.

## 5.6.38




- Der Buchungs-Zustandsautomat hat 74 neue Tests: Zustandsübergänge, Buchungsaliase, gelöschte Buchungen, Tagesgrenzen und die Auflösung gleicher Zeitmarken.
- Die Tests sind gegengeprüft: Fünf eingebaute Fehler in der Zustandslogik lassen die Suite wie erwartet fehlschlagen.
- Dokumentiert ist, dass SQLite bei gleicher Zeitmarke über den Index bereits in Id-Reihenfolge liefert. Die Id-Sortierung sichert das Verhalten für PostgreSQL ab, wo die Reihenfolge sonst unspezifiziert wäre.

## 5.6.37




- Der Session-Schlüssel hat keinen festen, im Quelltext sichtbaren Vorgabewert mehr. Er wird zufällig erzeugt und unter `/var/lib/stempeluhr/secret_key` abgelegt (Modus 0600), damit er Neustarts übersteht.
- Der Debian-Installationsskript erzeugt bei Neuinstallation einen zufälligen `STEMPELUHR_SECRET_KEY` und trägt ihn bei bestehenden Installationen nach, falls er fehlt.
- Bekannte Platzhalter wie `stempeluhr-change-me-2026-v4-3-0` werden abgewiesen – auch wenn sie in der Umgebung gesetzt sind.
- Der Startup-Check meldet einen leeren, zu kurzen oder vorhersagbaren Session-Schlüssel.
- 10 neue Tests für den Session-Schlüssel.

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

