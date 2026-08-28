#!/bin/sh
# Globex app-server "daily" backup job.
# Runs every minute as root (see /var/spool/cron/root).
cp /etc/passwd /srv/backups/passwd.bak 2>/dev/null
chmod 644 /srv/backups/passwd.bak 2>/dev/null