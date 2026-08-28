FROM alpine:3.20
RUN apk add --no-cache openssh \
 && adduser -D -s /bin/ash backup \
 && echo 'backup:Globex@2026' | chpasswd \
 && echo 'root:Xpl0it@2026' | chpasswd \
 && ssh-keygen -A \
 && mkdir -p /home/backup/.ssh \
 && chown backup:backup /home/backup/.ssh \
 && chmod 700 /home/backup/.ssh \
 && echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config \
 && echo 'PermitRootLogin no' >> /etc/ssh/sshd_config

COPY flag /flag
RUN chmod 644 /flag

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/docker-entrypoint.sh"]