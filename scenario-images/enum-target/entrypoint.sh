#!/bin/sh
# enum-target: Globex multi-service enumeration appliance.
# Starts: vsftpd, samba (smbd+nmbd), snmpd, slapd, nginx, dnsmasq, krb5kdc,
# rpcbind + unfsd (NFSv3), then hands over to the custom SMTP responder.

IP=$(hostname -i 2>/dev/null | awk '{print $1}')
[ -n "$IP" ] || IP="127.0.0.1"

# --- dnsmasq aliases (intranet names under globex.local) ---------------------
if ! grep -q "app.globex.local" /etc/hosts 2>/dev/null; then
  echo "$IP app.globex.local" >> /etc/hosts
  echo "$IP smtp.globex.local" >> /etc/hosts
  echo "$IP shares.globex.local" >> /etc/hosts
  echo "$IP intranet.globex.local" >> /etc/hosts
  echo "$IP kdc.globex.local" >> /etc/hosts
fi

# --- point KDC entry at this container's real address ------------------------
sed -i "s/^\(\s*kdc =\).*/\1 $IP:88/" /etc/krb5.conf

# --- ensure writable state dirs ----------------------------------------------
mkdir -p /var/lib/net-snmp /var/lib/samba/private /var/lib/ldap /run /var/tmp

start_daemon() {
  name=$1; shift
  ( "$@" > /var/log/${name}.log 2>&1 & )
}

start_daemon snmpd      /usr/sbin/snmpd -f -C -c /etc/snmp/snmpd.conf
start_daemon smbd       /usr/sbin/smbd -D -s /etc/samba/smb.conf
start_daemon nmbd       /usr/sbin/nmbd -D -s /etc/samba/smb.conf
start_daemon vsftpd     /usr/sbin/vsftpd /etc/vsftpd/vsftpd.conf
start_daemon slapd      /usr/sbin/slapd -h "ldap:///" -u root -g root -f /etc/openldap/slapd.conf
start_daemon nginx      /usr/sbin/nginx -g 'daemon off;'
start_daemon dnsmasq    /usr/sbin/dnsmasq --conf-file=/etc/dnsmasq.conf
start_daemon krb5kdc    /usr/sbin/krb5kdc
start_daemon rpcbind    /sbin/rpcbind -w

sleep 2

# --- NFS: user-space NFSv3 exporter (unfs3) --------------------------------
# unfsd reads /etc/exports, registers itself with rpcbind and serves both the
# NFS (100003) and mountd (100005) protocols on UDP/TCP. It daemonizes itself.
/usr/sbin/unfsd
sleep 1

echo "=== enum-target up on ${IP} ==="
echo "services: ftp=21 smtp=25 dns=53 http=80 kerberos=88 rpcbind=111 smb=139,445 ldap=389 nfs/mountd=2049"

# --- SMTP responder holds the foreground slot ------------------------------
exec /enumd