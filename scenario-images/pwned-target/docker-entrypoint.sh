#!/bin/sh
set -e
(
  while [ 1 ]; do
    sleep 30
    sh /usr/local/cron/backup.sh
  done
) &
exec /usr/sbin/sshd -D