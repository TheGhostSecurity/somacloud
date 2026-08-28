Globex Onboarding NFS Share
===========================

This directory keeps the HR "enrollment" export that the intranet
provisioning playbooks reference. Files here are regenerated nightly by
the `enroll-sync` cron on kdc.globex.local.

Everything under /export/enroll is world-readable so new hire onboarding
scripts can pull the latest roster without needing a Kerberos ticket.

NOTE: usernames in roster.csv are the canonical corporate logins; they
map 1:1 to the mail system, the Samba domain, and the Kerberos realm
(GLOBEX.LOCAL). service accounts (svc_*) are used by application
integration, NOT by humans.