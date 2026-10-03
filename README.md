# SomaCloud

A self-hosted, browser-based cybersecurity training platform. It provisions
isolated Kali Linux sandboxes on remote Docker nodes and delivers a full
CEH-aligned lab curriculum organised by attack phase — footprinting, scanning,
enumeration, vulnerability analysis, exploitation, post-exploitation, and
extras.

Students get a real terminal in the browser, complete hands-on labs against
deliberately vulnerable services, submit flags, and track their progress.
Instructors author content, define labs, provision the Docker worker nodes, and
analyse student performance.

---

## Highlights

- **Real sandboxes, not simulations** — every lab runs an actual ttyd terminal
  plus purpose-built vulnerable containers (Apache, SMB, LDAP, Kerberos, DNS,
  SQL injection, LFI, IDOR, XSS, and more)
- **59 labs across 9 phases** — a full offensive-security path from Linux
  fundamentals through post-exploitation
- **Multi-node Docker Swarm** — the scheduler places each lab on the node with
  the tightest fit, and refuses to over-commit CPU, RAM, or ports
- **Resource profiles** — per-lab CPU/RAM/time budgets, including a GUI profile
  reserved for VNC-based tooling
- **Auto-provisioned nodes** — register a host, click Setup, and the platform
  installs Docker, issues a TLS certificate, and joins it to the Swarm
- **Instructor analytics** — per-student and cohort charts, activity timelines,
  lab status, and flag submission review
- **Self-hosted CA** — mutual TLS between the app server and every worker, so
  no worker can join without being signed
- **Encrypted, scriptable backups** — one command snapshots the database and
  node keys; restore onto a fresh host in minutes

## Architecture

```
+---------------------------------+
|   Application server            |
|   Django + orchestrator         |
+----------------+----------------+
                 | HTTPS :2376 (mutual TLS)
   +-------------+-------------+
   |                           |
+---------+---------+  +--------+---------+
|  Worker node 1  |  |  Worker node 2   |
|  kali (Docker)  |  |  kali2 (Docker)  |
+-----------------+  +------------------+
```

| Tier | Purpose |
|------|---------|
| **Application server** | Django web app, admin UI, student portal, orchestrator |
| **Worker nodes** | Run student sandbox containers (ttyd terminal + vulnerable services) |
| **TLS infrastructure** | Mutual TLS between app server and workers, via a self-hosted CA (`core/ca.py`) |

The app server and every worker share one Certificate Authority. Each side
presents a certificate signed by that CA, producing mutual TLS.

## Tech stack

| Layer | Technology |
|-------|------------|
| Framework | Django 6.0, Python 3.13 |
| Database | SQLite by default, PostgreSQL supported |
| Sandboxing | Docker Engine 24+ / Docker Swarm |
| Terminal | ttyd |
| Frontend | Tailwind CSS, server-rendered Django templates, Lucide icons |
| Orchestration | Paramiko (SSH), requests (Docker API over mTLS) |
| Analytics | matplotlib |
| Reports | reportlab, pypdf |

## Quick start

```bash
git clone https://github.com/TheGhostSecurity/somacloud.git
cd somacloud

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

export DJANGO_SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
export ALLOWED_HOSTS="localhost,127.0.0.1"

python manage.py migrate
python manage.py createsuperuser
python manage.py seed_data
python manage.py runserver 0.0.0.0:8000
```

A fresh clone has **no labs** — the database is the record of record. Either
restore a backup (see [backups/README.md](backups/README.md)) or seed the
bundled demo material:

```bash
python manage.py populate_labs   # a small demo set (recon + enumeration)
```

The full 59-lab curriculum lives in the encrypted backup committed under
`backups/`, not in the seed scripts. `scripts/seed_*.py` are authoring sources
for individual phases and will not reconstruct labs that were created or
edited through the UI.

Then register a Docker worker node and build the scenario images — see
[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) for the full walkthrough.

## Documentation

| Document | Contents |
|----------|----------|
| [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md) | Complete install, TLS/CA setup, node registration, backup and disaster recovery |
| [backups/README.md](backups/README.md) | Encrypted backup and restore procedure |
| [content/README.md](content/README.md) | Lab content directory layout |

## Repository layout

```
core/                  Django app: models, views, orchestrator, CA, migrations
core/management/       Management commands (register_node, seed_data, ...)
scenario-images/       Dockerfiles for terminals and vulnerable services
templates/             Server-rendered UI
static/                CSS, JS, images
sandbox/               Django project settings and URLs
content/               Bundled learning-path content
scripts/               Lab seeding and backup/restore tooling
docker-tls/            OpenSSL config templates (no keys)
```

## Security

This project manages credentials and TLS private keys, so a few rules are
enforced in `.gitignore`:

| Never committed | Why |
|-----------------|-----|
| `ca/`, `certs/`, `docker-tls/` PKI material | A CA signing key can mint certificates every node trusts, letting an attacker join your Swarm and run containers on your workers |
| `media/` | Holds Docker node SSH private keys |
| `db.sqlite3` | User password hashes and session state |
| `*.pem`, `*.key`, `*.csr`, `*.srl` | Private keys and CSRs |

`docker-tls/` ships only its three OpenSSL `.cnf` templates, which contain no
keys. Generate real certificates locally — see section 5 of the installation
guide.

`sandbox/settings.py` contains **no credentials and no real IPs**. Everything is
read from the environment, and the app refuses to start without
`DJANGO_SECRET_KEY` rather than falling back to a known development key.

If you ever commit a secret, deleting it in a new commit is not enough —
purging it from history is covered in section 5.4 of the installation guide.

## Backups

Lab content lives in the database, **not** in the seed scripts, so the database
snapshot is the record of record.

```bash
./scripts/backup.sh            # consistent snapshot, safe while running
./scripts/backup_encrypt.sh    # encrypt for committing to git
```

Copy the result off the server — a backup on the host you are about to
terminate is not a backup.

## Lab content model

| Phase | Labs |
|-------|-----:|
| Kali Linux File System | 4 |
| Footprinting & Reconnaissance | 12 |
| Scanning Networks | 8 |
| Enumeration | 8 |
| Vulnerability Analysis | 8 |
| Exploitation | 8 |
| Post-Exploitation | 8 |
| Extras | 3 |
| **Total** | **59** |

Each lab bundles theory, a walkthrough, challenge questions, terminal and
service containers, tool references, and a resource profile.

## Scheduling and resource profiles

Every lab declares a CPU, RAM, and time budget through a `ResourceProfile`.
`select_node()` in `core/orchestrator.py` picks the node with the tightest fit
that can still accommodate the lab, and returns nothing when no node can — so a
lab that would exceed a node's capacity fails fast instead of degrading
everyone else's sandbox.

The GUI profile is reserved for labs needing a desktop environment; note that
GUI workloads require noticeably more memory than terminal-only labs, so
check the worker's real available RAM against the profile before assigning one.

## License

For educational use.