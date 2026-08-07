# SomaCloud — Customer Deployment Guide

A straightforward guide for deploying SomaCloud on **your own servers**.
SomaCloud was designed to be deployed almost entirely in **automatic mode**:
you provide the servers and one SSH key per worker, and the platform configures
Docker, security certificates (TLS), and everything else for you.

---

## 1. What you need to get started

### 1.1 Servers

| Server | Purpose | Recommended size |
|--------|---------|------------------|
| **Hosting server** | Runs the SomaCloud web application (student portal + admin panel) | 2 vCPU, 4 GB RAM, 40 GB SSD |
| **Worker server(s)** | Run the browser terminals / lab sandboxes | 4 vCPU, 8 GB RAM, 100 GB SSD each |

You can start with one worker server and add more later — SomaCloud spreads
students across every connected worker automatically.

> **Linux only.** Both servers must run a modern Linux distribution
> (Ubuntu 20.04+, Debian 11+, or Kali). SomaCloud installs Docker itself, so
> the worker can be a **fresh** server with nothing pre-installed.

### 1.2 Domain / IP and network ports

- Your hosting server needs a **public IP** (or domain) that students and
  worker servers can reach.
- Open these ports on your cloud firewall / security groups:

| Port | On which server | Purpose |
|------|-----------------|---------|
| 8000 | Hosting server | SomaCloud web application |
| 22 | Hosting + workers | Secure shell (SSH) |
| 2376 | Worker servers | Docker API (secured with TLS automatically) |
| 9000–9100 | Worker servers | Student browser terminals |

### 1.3 A small software checklist

- Python 3.12 or 3.13 on the **hosting** server
- Git on the hosting server
- A **PEM private SSH key** for each worker server (this is how SomaCloud
  connects to and configures your workers automatically)

---

## 2. Step 1 — Get the application

```bash
git clone <your-somacloud-repository-url>
cd somacloud
```

---

## 3. Step 2 — Prepare the hosting server

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git openssl
```

Create the Python virtual environment and install the application:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Step 3 — Configure and install

### 4.1 Set your server's address

In `sandbox/settings.py`, tell the app which address it lives at. Replace the
example with **your** public IP or domain:

```python
ALLOWED_HOSTS = ["your-server-ip-or-domain", "localhost", "127.0.0.1"]
APP_SERVER_URL = "http://your-server-ip-or-domain:8000"   # how workers reach you
SWARM_MANAGER_IP = "your-server-ip-or-domain"             # your public IP
```

### 4.2 Database

The default **SQLite** database works with zero configuration and is perfectly
fine for a small institution. For larger deployments SomaCloud also supports
**PostgreSQL** — simply install PostgreSQL and set the database details through
environment variables (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
`DB_PORT`).

### 4.3 Create the database and first administrator

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4.4 Seed the built-in content

```bash
python manage.py seed_data
python manage.py populate_labs
python manage.py sync_content
```

These commands load the default hacking phases, resource profiles, security
tools, and example labs so you can explore the platform immediately.

---

## 5. Step 4 — Start the platform

### For a quick start

```bash
python manage.py runserver 0.0.0.0:8000
```

### For a persistent 24/7 service (recommended)

Create a system service so the platform runs in the background and restarts
automatically. Create `/etc/systemd/system/somacloud.service`:

```ini
[Unit]
Description=SomaCloud Web Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/somacloud
ExecStart=/path/to/somacloud/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable somacloud
sudo systemctl start somacloud
```

Log in at `http://your-server-ip-or-domain:8000` with the administrator account
you created.

---

## 6. Step 5 — Connect your worker servers (automatic mode)

This is where SomaCloud does the heavy lifting for you.

### 6.1 Upload your SSH keys (one time)

1. Log in as administrator.
2. Go to **Administration → SSH Keys → Upload**.
3. Upload the PEM private key that can log into your worker servers.

> Create one key per worker or reuse one key for all workers if your cloud
> provider allows it. Permissions are set to `600` automatically and the key is
> stored securely on the hosting server.

### 6.2 Register each worker

1. Go to **Administration → Docker Nodes → Add Node**.
2. Enter:
   - **Name** — e.g. `worker-1`
   - **Public IP** — the worker's IP address
   - **SSH user** — the login user for that server (e.g. `ubuntu`, `kali`, `admin`)
   - **SSH key** — select the key you uploaded
   - Leave everything else as the default.
3. Click **Add**.

### 6.3 Run the automatic setup

1. Open the node you just added and click **Setup**.
2. SomaCloud connects over SSH and automatically:
   - installs Docker Engine,
   - generates a security certificate for the worker,
   - signs it with the platform's own certificate authority,
   - secures the Docker connection with mutual TLS,
   - enables the terminal port range (9000–9100),
   - restarts Docker and confirms the node is online.
3. When setup finishes the node shows **Active**.

### 6.4 Verify it really works

Click **Verify** on the node. SomaCloud runs a full smoke test and shows you
each step:

```
  ✓ Daemon ping: Docker daemon responded
  ✓ Pull test image: alpine:latest pulled successfully
  ✓ Create container: Container 7b95526e3428 created
  ✓ Start container: Container started and exited with code 0
  ✓ Cleanup container: Container 7b95526e3428 removed
  ✓ Cleanup image: alpine:latest removed
```

That's it — the worker is ready. **Repeat steps 6.2–6.4 for each extra worker.**
SomaCloud automatically spreads students across all connected workers.

---

## 7. Step 6 — Add your own lab content

### 7.1 Register container images

Labs run Docker images. Two kinds are available:

- **Terminal** — the Kali browser terminal students work in.
- **Service** — vulnerable target machines for the lab scenario.

Register images from the command line:

```bash
python manage.py register_container_image \
    --name "Kali Terminal" \
    --image "your-org/kali-ttyd:latest" \
    --kind terminal \
    --port 7681 \
    --description "Kali Linux browser terminal"

python manage.py register_container_image \
    --name "Vulnerable Web App" \
    --image "your-org/web-vuln:latest" \
    --kind service \
    --port 80
```

### 7.2 Create and publish labs

1. From the admin panel go to **Lab Management → Create Lab**.
2. Choose a hacking phase, resource profile, terminal image, and any service
   images.
3. Add the theory, notes, and challenge flag/question.
4. **Publish** the lab — it now appears in the student Lab Library.

---

## 8. Step 7 — Go live

1. Open the **Administration** page and confirm:
   - your summary shows your user, lab, and session counts,
   - your worker nodes show **Active**.
2. Create student accounts (Administration → Create user, or students self-register).
3. Students log in, open the **Lab Library**, enroll in a lab, and click
   **Launch** to open their browser terminal in seconds.

---

## 9. Day-to-day operations

| Task | How |
|------|-----|
| See who is online / running sandboxes | **Lab Management → Live Monitor** |
| Check worker health | **Docker Nodes → Health Check / Verify** |
| Update the application | copy updated files to the server, then `sudo systemctl restart somacloud` |
| View logs | `sudo journalctl -u somacloud -f` |
| Add more capacity | register another worker server (steps 6.2–6.4) |
| Clean up expired sandboxes | `python manage.py expire_sessions` |

---

## 10. Troubleshooting (the basics)

**A worker stays "Offline" after setup.**
Run **Verify** on the node and read the failing step. The most common cause is
the node's Docker port (2376) not being open in its firewall/security group.

**Students can't open terminals.**
Confirm the terminal port range **9000–9100** is open on the worker servers,
and that the worker node is **Active**.

**"Docker unreachable" on the admin summary.**
This card reflects the local daemon on the hosting server. Sandboxes run on the
worker servers, so check the **Docker Nodes** page instead for real status.

**Server says "host is not allowed".**
Add your server's IP/domain to `ALLOWED_HOSTS` in `sandbox/settings.py` and
restart.

---

## 11. Frequently asked questions

**How many students can use the platform?**
It depends on your worker servers. Each lab uses a resource profile (256 MB – 2
GB RAM per student). A single 8 GB worker comfortably handles several
concurrent sandboxes; add more workers to scale.

**Do workers need anything pre-installed?**
No. SomaCloud installs Docker and all certificates automatically — a fresh
Linux server is ideal.

**Is the Docker connection secure?**
Yes. Every worker connection uses mutual TLS backed by the platform's own
certificate authority. Certificates are generated, signed, and installed
automatically.

**What if I change cloud providers?**
Nothing in the app is tied to a specific cloud. Provision new servers, register
them as workers, and keep going — or move the hosting server by reinstalling
the application and restoring the database.

**Can I use my own container images?**
Yes. Any Docker Hub image (or a private registry image you can pull) can be
registered as a terminal or service image for labs.
