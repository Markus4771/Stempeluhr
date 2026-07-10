# Modul: auth

Dieses Modul wurde in Version 5.2.03 vorbereitet.

Aktueller Stand:
- Bestehende produktive Routen bleiben zunächst in `app/routes/`.
- Die Migration in dieses Modul erfolgt schrittweise in späteren 5.2.x-Versionen.
- Ziel ist eine klare Trennung von Routen, Services, Templates und Tests.

Geplante Struktur:

```
app/modules/auth/
├── __init__.py
├── routes.py
├── services.py
├── schemas.py
└── README.md
```
