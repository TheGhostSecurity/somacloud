#!/usr/bin/env bash
# Restore a SomaCloud database backup produced by scripts/backup.sh
#
# Usage:  ./scripts/restore.sh backups/db-20260930-161500.sqlite3.gz
#
# Stop the service BEFORE restoring, otherwise running containers/sessions
# keep writing to the old database file.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP="${1:-}"

if [ -z "$BACKUP" ]; then
    echo "ERROR: pass the path to a backup file, e.g." >&2
    echo "  ./scripts/restore.sh backups/db-20260930-161500.sqlite3.gz" >&2
    exit 1
fi

if [ ! -f "$BACKUP" ]; then
    echo "ERROR: backup not found: $BACKUP" >&2
    exit 1
fi

case "$BACKUP" in
    *.gz) SRC="$(mktemp -t somacloud-restore-XXXXXX.sqlite3)" ;;
    *)    SRC="$BACKUP" ;;
esac

echo "==> Stopping somacloud service (if present)"
sudo systemctl stop somacloud 2>/dev/null || echo "    (no systemd service found, continuing)"

echo "==> Unpacking backup to temporary file"
if [ "$SRC" != "$BACKUP" ]; then
    gunzip -c "$BACKUP" > "$SRC"
fi

echo "==> Backing up current database (safety net)"
if [ -f "$APP_DIR/db.sqlite3" ]; then
    cp "$APP_DIR/db.sqlite3" "$APP_DIR/db.sqlite3.bak-$(date +%Y%m%d-%H%M%S)"
    echo "    saved as db.sqlite3.bak-$(date +%Y%m%d-%H%M%S)"
fi

echo "==> Installing backup as db.sqlite3"
cp "$SRC" "$APP_DIR/db.sqlite3"

# Restore media/ (Docker node SSH keys) if a matching archive was provided.
# Pass it as the 2nd argument: ./scripts/restore.sh db.sqlite3.gz media.tar.gz
MEDIA_ARCHIVE="${2:-}"
if [ -n "$MEDIA_ARCHIVE" ] && [ -f "$MEDIA_ARCHIVE" ]; then
    echo "==> Restoring media/ (Docker node SSH keys)"
    tar -xzf "$MEDIA_ARCHIVE" -C "$APP_DIR"
else
    echo "NOTE: no media archive supplied. If media/keys/ is empty, upload the node"
    echo "      SSH key again via the admin UI, otherwise node setup will fail."
fi

if [ -f "$APP_DIR/venv/bin/python" ]; then
    PY="$APP_DIR/venv/bin/python"
elif [ -f "$APP_DIR/.venv/bin/python" ]; then
    PY="$APP_DIR/.venv/bin/python"
else
    PY="python3"
fi

echo "==> Applying migrations"
( cd "$APP_DIR" && "$PY" manage.py migrate --noinput )

echo "==> Verifying integrity"
( cd "$APP_DIR" && "$PY" -c "
import sqlite3
c = sqlite3.connect('db.sqlite3')
print('   integrity:', c.execute('PRAGMA integrity_check').fetchone()[0])
c.close()
" )

echo "==> Starting somacloud service"
sudo systemctl start somacloud 2>/dev/null || echo "    (start manually if not a systemd service)"

echo
echo "Restore complete. Check the service with:  systemctl status somacloud"