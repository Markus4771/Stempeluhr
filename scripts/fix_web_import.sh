#!/bin/bash
set -e

FILE="/opt/stempeluhr/app/routes/web.py"

echo "Repariere Importfehler in $FILE ..."

if [ ! -f "$FILE" ]; then
    echo "Fehler: $FILE nicht gefunden."
    exit 1
fi

sudo sed -i 's/from pathlib import Path, timedelta/from pathlib import Path/g' "$FILE"
sudo sed -i 's/from pathlib import Path, datetime, timedelta/from pathlib import Path/g' "$FILE"
sudo sed -i 's/from pathlib import Path, datetime/from pathlib import Path/g' "$FILE"

if ! grep -q '^from datetime import datetime' "$FILE"; then
    sudo sed -i '1ifrom datetime import datetime' "$FILE"
fi

if ! grep -q '^from pathlib import Path' "$FILE"; then
    sudo sed -i '1ifrom pathlib import Path' "$FILE"
fi

sudo systemctl restart stempeluhr
sudo systemctl status stempeluhr --no-pager -l
