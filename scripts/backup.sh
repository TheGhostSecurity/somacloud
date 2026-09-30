#!/usr/bin/env bash
# SomaCloud database backup.
# Creates a consistent snapshot of db.sqlite3 (safe to run while the app is live)
# plus a Django fixture dump you can inspect/merge by hand.
#
# Usage:  ./scripts/backup.sh [output_dir]
# Default output dir: ./backups

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:-$APP_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DB="$APP_DIR/db.sqlite3"

if [ ! -f "$DB" ]; then
    echo "ERROR: database not found at $DB" >&2
    exit 1
fi

mkdir -p "$OUT_DIR"

# Consistent snapshot using sqlite3's online backup API via Python.
# This is safe while the web app is running, unlike a plain file copy.
SNAPSHOT="$OUT_DIR/db-$STAMP.sqlite3"
python3 - "$DB" "$SNAPSHOT" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
d = sqlite3.connect(dst)
s.backup(d)
d.close()
s.close()
PY

gzip -f "$SNAPSHOT"

echo "Backup written: $SNAPSHOT.gz"

# Optional human-readable fixture dump (large, but handy for diffing/inspecting).
FIXTURE="$OUT_DIR/fixture-$STAMP.json"
if [ -f "$APP_DIR/venv/bin/python" ]; then
    PY="$APP_DIR/venv/bin/python"
elif [ -f "$APP_DIR/.venv/bin/python" ]; then
    PY="$APP_DIR/.venv/bin/python"
else
    PY="python3"
fi

( cd "$APP_DIR" && "$PY" manage.py dumpdata \
    --exclude contenttypes \
    --exclude auth.permission \
    --indent 2 > "$FIXTURE" )

gzip -f "$FIXTURE"
echo "Fixture dump:  $FIXTURE.gz"

# media/ holds the Docker node SSH private keys as real files.
# The database only stores SSHKey rows, so this must be archived separately
# or a restored server cannot register/manage its Docker nodes.
MEDIA="$OUT_DIR/media-$STAMP.tar.gz"
if [ -d "$APP_DIR/media" ]; then
    tar -czf "$MEDIA" -C "$APP_DIR" media
    echo "Media archive: $MEDIA"
fi

echo
echo "To restore on a new server, see scripts/restore.sh"