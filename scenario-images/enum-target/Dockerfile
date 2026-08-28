# ---- Build stage: compile the custom SMTP + RPC(NFS) responders ----
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /enumd

# ---- Runtime stage: Alpine with real enumeration services ----
FROM alpine:3.20

RUN apk add --no-cache \
        samba samba-server samba-common-tools samba-client \
        net-snmp \
        openldap openldap-back-mdb \
        krb5-server \
        vsftpd \
        nginx \
        dnsmasq \
        rpcbind \
        unfs3

# ---- Kerberos: realm config + KC database baked at build time ----
COPY conf/krb5.conf /etc/krb5.conf
COPY conf/kdc.conf /etc/krb5kdc/kdc.conf
RUN mkdir -p /var/kerberos/krb5kdc && \
    echo "*/*@GLOBEX.LOCAL" > /var/kerberos/krb5kdc/kadm5.acl && \
    kdb5_util -r GLOBEX.LOCAL create -s -P 'GlobexKDC@Master2026' && \
    kadmin.local -q 'addprinc -pw Globex@2026 globex' && \
    kadmin.local -q 'addprinc -pw Operations@2026 bsmith' && \
    kadmin.local -q 'addprinc -pw Finance@2026 jtaylor' && \
    kadmin.local -q 'addprinc -pw Marketing@2026 jdoe' && \
    kadmin.local -q 'addprinc -pw Svc@P@ss2026 svc_http' && \
    kadmin.local -q 'modprinc -nopreauth svc_http' && \
    echo "=== KDC principals ===" && \
    kadmin.local -q 'listprincs' | sort

# ---- LDAP: slapd config + seed data ----
COPY conf/slapd.conf /etc/openldap/slapd.conf
COPY data/globex.ldif /tmp/globex.ldif
RUN mkdir -p /var/lib/ldap && \
    slapadd -f /etc/openldap/slapd.conf -l /tmp/globex.ldif && \
    rm -f /tmp/globex.ldif && \
    echo "=== LDAP directory loaded ==="

# ---- SNMP config ----
COPY conf/snmpd.conf /etc/snmp/snmpd.conf
RUN mkdir -p /var/lib/net-snmp && \
    echo "build-2026.1-rc3" > /etc/globex-build

# ---- Samba: users + password DB ----
COPY conf/smb.conf /etc/samba/smb.conf
RUN mkdir -p /var/lib/samba/private /var/lib/samba/locks && \
    adduser -D -H -s /sbin/nologin globex && \
    printf 'Globex@2026\nGlobex@2026\n' | smbpasswd -s -a globex && \
    echo "=== samba user 'globex' provisioned ==="

# ---- Web (nginx) ----
COPY conf/nginx.conf /etc/nginx/http.d/globex.conf
RUN rm -f /etc/nginx/http.d/default.conf

# ---- vsftpd ----
COPY conf/vsftpd.conf /etc/vsftpd/vsftpd.conf

# ---- dnsmasq ----
COPY conf/dnsmasq.conf /etc/dnsmasq.conf

# ---- NFS (unfs3 user-space NFSv3 daemon) ----
RUN mkdir -p /export/enroll
COPY data/enroll/ /export/enroll/
RUN chmod -R a+rX /export/enroll && \
    printf '/export/enroll 172.16.0.0/12(rw,insecure)\n' > /etc/exports

# ---- Share / web / ftp data ----
RUN mkdir -p /srv/smb/public /srv/smb/it /srv/smb/backup /srv/www /srv/ftp
COPY data/smb/public/  /srv/smb/public/
COPY data/smb/it/      /srv/smb/it/
COPY data/smb/backup/  /srv/smb/backup/
COPY data/web/         /srv/www/
COPY data/ftp/         /srv/ftp/
RUN chown -R nobody:nogroup /srv/smb/public /srv/smb/backup && \
    chmod -R a+r /srv/smb /srv/www /srv/ftp && \
    chmod -R a+rX /srv/smb /srv/www /srv/ftp

# ---- Custom Go responders: foreground process ----
COPY --from=build /enumd /enumd
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 21 25 53 80 88 111 139 389 445 2049

ENTRYPOINT ["/entrypoint.sh"]