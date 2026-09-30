#!/usr/bin/env bash
# Encrypt a set of SomaCloud backups into a single file safe to store in git.
#
# Usage:
#   ./scripts/backup_encrypt.sh                      # encrypt latest backups/
#   ./scripts/backup_encrypt.sh db-2026...gz m-...tar.gz   # encrypt specific files
#
# The passphrase is read from $SOMACLOUD_BACKUP_PASSPHRASE_FILE
# (default: ~/somacloud-backup-passphrase.txt) or prompted for.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="$APP_DIR/backups"
PASS_FILE="${SOMACLOUD_BACKUP_PASSPHRASE_FILE:-$HOME/somacloud-backup-passphrase.txt}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [ ! -f "$BACKUP_DIR" ]; then
    echo "ERROR: no backups/ directory. Run ./scripts/backup.sh first." >&2
    exit 1
fi

if [ $# -gt 0 ]; then
    INPUTS=("$@")
else
    # Default: newest db snapshot + newest media archive.
    mapfile -t INPUTS < <(
        cd "$BACKUP_DIR" && ls -t db-*.sqlite3.gz 2>/dev/null | head -1
        cd "$BACKUP_DIR" && ls -t media-*.tar.gz 2>/dev/null | head -1
    )
fi

if [ ${#INPUTS[@]} -eq 0 ]; then
    echo "ERROR: nothing to encrypt in $BACKUP_DIR" >&2
    exit 1
fi

if [ ! -f "$PASS_FILE" ]; then
    echo "ERROR: passphrase file not found at $PASS_FILE" >&2
    echo "Create one with:" >&2
    echo "  umask 077 && openssl rand -base64 24 > $PASS_FILE" >&2
    exit 1
fi

OUT="$BACKUP_DIR/somacloud-backup-$STAMP.tar.gz.enc"
TARBALL="$(mktemp -t somacloud-enc-XXXXXX.tar.gz)"

tar -czf "$TARBALL" -C "$BACKUP_DIR" "${INPUTS[@]}"

openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt \
    -in "$TARBALL" -out "$OUT" -pass "file:$PASS_FILE"

rm -f "$TARBALL"
chmod 600 "$OUT"

echo "Encrypted backup: $OUT"
echo "Contents: ${INPUTS[*]}"
echo
echo "Restore with:"
echo "  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \\"
echo "    -in $OUT -out backups.tar.gz -pass file:$PASS_FILE"
echo "  tar -xzf backups.tar.gz -C backups/"
echo "  ./scripts/restore.sh backups/<db-snapshot>.sqlite3.gz backups/<media>.tar.gz"