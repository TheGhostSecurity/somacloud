# SomaCloud Backups

Your database backups live here as **AES-256-CBC encrypted** files (`*.tar.gz.enc`).

## What's inside

Each `.enc` file contains:
- `db-<stamp>.sqlite3.gz` — full database snapshot (users, labs, sessions, nodes, resource profiles)
- `media-<stamp>.tar.gz` — `media/`, including `keys/somacloud.pem` (your Docker node SSH private key)

## Passphrase

The passphrase is **not** in the repository. It's stored locally at:

```
~/somacloud-backup-passphrase.txt
```

If you lose that file, the backups cannot be opened. Keep a copy somewhere safe
(password manager, offline USB, etc.).

## Creating a new backup

```bash
# 1. snapshot the database + media (app can stay running)
./scripts/backup.sh

# 2. encrypt the newest artifacts
./scripts/backup_encrypt.sh

# 3. commit the new .enc file
git add -f backups/*.tar.gz.enc && git commit -m "backup: $(date +%Y%m%d-%H%M)" && git push
```

## Restoring on a new server

```bash
git clone https://github.com/TheGhostSecurity/somacloud.git && cd somacloud
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt

openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in backups/somacloud-backup-<stamp>.tar.gz.enc \
  -out /tmp/b.tar.gz

tar -xzf /tmp/b.tar.gz -C backups/

./scripts/restore.sh backups/db-<stamp>.sqlite3.gz backups/media-<stamp>.tar.gz
```

After restoring, update `ALLOWED_HOSTS` in `sandbox/settings.py` with the new
server IP, and re-register the Docker node (the stored row has the old IP and
host key).
