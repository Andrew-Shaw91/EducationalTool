#!/usr/bin/env bash
# Makes a consistent copy of the CodeSense SQLite database and keeps the last 14.
# Safe to run while the site is live (uses SQLite's own backup command).
#
# Needs the sqlite3 program:  sudo apt install -y sqlite3
# Run by hand (as the codesense user):
#   sudo -u codesense /srv/codesense/app/deploy/backup_db.sh
# Run every night at 02:30 (see DEPLOYMENT.md, "Backups").

set -euo pipefail

DB="${DATABASE_PATH:-/srv/codesense/data/db.sqlite3}"
DEST="${BACKUP_DIR:-/srv/codesense/data/backups}"
KEEP=14

mkdir -p "$DEST"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$DEST/db-$STAMP.sqlite3"

sqlite3 "$DB" ".backup '$OUT'"
gzip "$OUT"

# Delete all but the newest $KEEP backups.
ls -1t "$DEST"/db-*.sqlite3.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm --

echo "Backup written to $OUT.gz"
