FROM alpine:3.20 AS builder
RUN apk add --no-cache build-base
COPY flagd.c /tmp/flagd.c
RUN gcc -static -O2 -o /tmp/flagd /tmp/flagd.c

FROM alpine:3.20
RUN apk add --no-cache openssh sudo vim util-linux \
 && adduser -D -s /bin/ash globex \
 && echo 'globex:Globex@2026' | chpasswd \
 && echo 'root:Root@2026' | chpasswd \
 && ssh-keygen -A \
 && mkdir -p /srv/backups /usr/local/cron /home/globex/.ssh \
 && chown globex:globex /home/globex/.ssh \
 && chmod 700 /home/globex/.ssh \
 && echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config \
 && echo 'globex ALL=(root) NOPASSWD: /usr/bin/vim' > /etc/sudoers.d/globex \
 && chmod 440 /etc/sudoers.d/globex \
 && printf 'FLAG{suid_escalation_root}\n' > /root/flag-suid.txt \
 && printf 'FLAG{gtfobins_root_shell}\n' > /root/flag-sudo.txt \
 && printf 'FLAG{cron_job_takeover}\n' > /root/flag-cron.txt \
 && printf 'FLAG{ssh_key_persistence}\n' > /root/flag-persist.txt \
 && chmod 600 /root/flag-*.txt \
 && printf 'FLAG{beachhead_secured}\n' > /home/globex/user.txt \
 && chown globex:globex /home/globex/user.txt \
 && chmod 644 /home/globex/user.txt

COPY --from=builder /tmp/flagd /usr/local/bin/flagd
COPY backup.sh /usr/local/cron/backup.sh
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chown root:root /usr/local/bin/flagd \
 && chmod 4755 /usr/local/bin/flagd \
 && chown root:root /usr/local/cron/backup.sh \
 && chmod 0777 /usr/local/cron/backup.sh \
 && chmod +x /docker-entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/docker-entrypoint.sh"]