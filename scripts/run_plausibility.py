#!/usr/bin/env python3
from datetime import date, datetime, timedelta
import argparse

from app.database import SessionLocal
from app.services.plausibility import scan_day, teamlead_summary

parser = argparse.ArgumentParser(description='Stempeluhr Plausibilitätsprüfung')
parser.add_argument('--date', default='', help='Datum YYYY-MM-DD, Standard heute')
parser.add_argument('--yesterday', action='store_true', help='gestern prüfen')
parser.add_argument('--teamlead-summary', action='store_true', help='Teamleiter-Zusammenfassung senden')
args = parser.parse_args()

if args.yesterday:
    day = date.today() - timedelta(days=1)
elif args.date:
    day = datetime.strptime(args.date, '%Y-%m-%d').date()
else:
    day = date.today()

db = SessionLocal()
try:
    issues = scan_day(db, day, send_employee_mail=True)
    print(f'Plausibilitätsprüfung {day}: {len(issues)} Auffälligkeiten')
    if args.teamlead_summary:
        sent = teamlead_summary(db, day)
        print(f'Teamleiter-Zusammenfassung: {sent} E-Mail(s)')
finally:
    db.close()
