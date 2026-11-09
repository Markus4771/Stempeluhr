# Sicherheitskorrekturen: Mitarbeiter-API und Netzwerkfilter

`GET /api/employees` verwendet jetzt dieselbe Zugriffskontrolle wie die
versionierte API: Die API muss aktiviert sein und der Aufruf benötigt einen
gültigen API-Schlüssel als `X-API-Key` oder `Authorization: Bearer …`.
Deaktivierte, abgelaufene oder für die Client-IP gesperrte Schlüssel werden
abgewiesen. Bestehende Clients dieses Endpunkts müssen einen Schlüssel senden.

Der Netzwerkfilter liest die Client-IP ausschließlich aus dem ASGI-Scope.
Ungeprüfte `X-Forwarded-For`- und `X-Real-IP`-Header werden nicht ausgewertet.
Eine fehlende Client-IP führt bei aktiviertem Filter zur Ablehnung.

Bei Reverse Proxys muss Uvicorn die tatsächlichen Proxy-Adressen über
`--forwarded-allow-ips` beziehungsweise `FORWARDED_ALLOW_IPS` kennen.
Uvicorn vertraut standardmäßig `127.0.0.1`, was einen lokalen Nginx abdeckt.
Keine Wildcard `*` verwenden, wenn der Anwendungsport direkt erreichbar ist.
Der Proxy muss die Weiterleitung der tatsächlichen Client-IP sicherstellen.

Regressionstests: `tests/test_security_regressions.py`.
