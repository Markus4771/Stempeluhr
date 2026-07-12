# API-Handbuch

Version 5.6.15 – Stempeluhr Professional

## Überblick

Die Stempeluhr stellt REST-Endpunkte für ausgewählte Integrationen und Raspberry-Terminals bereit. Aktive Endpunkte können über die Entwicklerkonsole oder die OpenAPI-Beschreibung der laufenden Installation geprüft werden.

## Basisadresse

Beispiel:

```text
http://10.0.0.130:8000
```

Produktiv sollte HTTPS verwendet werden.

## Authentifizierung

API-Schlüssel werden unter **Systemeinstellungen → Integrationen → API** verwaltet. Schlüssel nur an berechtigte Systeme weitergeben, regelmäßig erneuern und niemals in öffentliches Quellcode-Repository übernehmen.

Je nach Endpunkt wird der Schlüssel als Header erwartet. Die konkrete Header-Bezeichnung der installierten Version ist in der API-Konfiguration und OpenAPI-Beschreibung zu prüfen.

## Systemendpunkte

### Healthcheck

```http
GET /health
```

Beispielantwort:

```json
{
  "status": "ok",
  "version": "5.6.15",
  "database": "postgresql"
}
```

### Versionsinformation

```http
GET /version
```

Die Antwort enthält Produktname, Version und den Abgleich mit `version.txt`.

## Datenformate

- Zeichencodierung: UTF-8
- Zeitstempel: ISO-8601, sofern der Endpunkt nichts anderes vorgibt
- Inhaltstyp: `application/json`
- Datumswerte: `YYYY-MM-DD`

## Fehlercodes

- `200` Anfrage erfolgreich
- `201` Datensatz erstellt
- `303` Weiterleitung bei Webformularen
- `400` ungültige Eingabe
- `401` nicht authentifiziert
- `403` Zugriff nicht erlaubt
- `404` Endpunkt oder Datensatz nicht gefunden
- `409` Konflikt oder Doppelbuchung
- `422` Validierungsfehler
- `500` interner Fehler

## Beispiel mit curl

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/version
```

Beispiel mit JSON und API-Key:

```bash
curl -sS \
  -H "Content-Type: application/json" \
  -H "X-API-Key: API_KEY_HIER_EINSETZEN" \
  http://STEMPELUHR:8000/api/v1/ENDPUNKT
```

## Raspberry-Terminals

Terminals verwenden eigene Kennungen beziehungsweise Schlüssel. Heartbeats melden Erreichbarkeit und Versionsinformationen. Terminalschlüssel getrennt von normalen Benutzerpasswörtern verwalten.

## Sicherheitsregeln

- Nur HTTPS über unsichere Netze verwenden.
- API-Schlüssel mit minimalen Berechtigungen ausstellen.
- Erlaubte IP-Adressen einschränken, wenn möglich.
- Schlüssel nicht in URLs übertragen.
- Antworten und Logs dürfen keine Passwörter oder Secrets enthalten.
- Fehlgeschlagene Zugriffe im Audit beziehungsweise Serverlog prüfen.

## Versionskompatibilität

Integrationen müssen vor einem Update auf der Test-VM geprüft werden. Nicht dokumentierte interne Endpunkte gelten nicht als stabile Schnittstelle. Für produktive Integrationen nur freigegebene API-Routen verwenden.

## Fehlersuche

1. `/health` prüfen.
2. API-Schlüssel und Aktivstatus prüfen.
3. Netzwerk und Firewall prüfen.
4. Statuscode und Antworttext auswerten.
5. Serverlog ohne Secret-Werte prüfen.
6. Aktive Routen in der Entwicklerkonsole vergleichen.
