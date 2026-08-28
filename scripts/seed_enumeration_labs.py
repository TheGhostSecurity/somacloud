import django, os, sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sandbox.settings")
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from core.models import ContainerImage, HackPhase, Lab, ResourceProfile

INSTRUCTOR = "burhani"
IS_PUBLISHED = True

def img(name, image, kind, port, desc=""):
    obj, _ = ContainerImage.objects.update_or_create(
        name=name,
        defaults=dict(image=image, kind=kind, container_port=port, description=desc),
    )
    return obj

def lab(phase, slug, title, order, profile, terminal, services, summary, theory, notes,
        flag="", flag_hint="", ctype="question", question="", options="", answer=""):
    existing = Lab.objects.filter(hack_phase=phase, slug=slug).first()
    defaults = dict(
        title=title,
        instructor=User.objects.get(username=INSTRUCTOR),
        summary=summary,
        theory_content=theory,
        notes=notes,
        resource_profile=profile,
        terminal_container=terminal,
        flag=flag,
        flag_hint=flag_hint,
        challenge_type=ctype,
        challenge_question=question,
        challenge_options=options,
        challenge_answer=answer,
        is_published=IS_PUBLISHED,
        order=order,
        published_at=timezone.now() if IS_PUBLISHED else None,
    )
    if existing:
        for k, v in defaults.items():
            setattr(existing, k, v)
        existing.service_containers.set(services)
        existing.save()
        print(f"  updated {slug}")
        return existing
    obj = Lab.objects.create(hack_phase=phase, slug=slug, **defaults)
    obj.service_containers.set(services)
    obj.save()
    print(f"  created {slug}")
    return obj

def run():
    phase = HackPhase.objects.get(slug="enumeration")
    enum = img("Enum Target (multi-service)", "theghostriley23/enum-target:latest", "service", 21,
               "Globex enumeration appliance: FTP, SMTP, DNS, HTTP, Kerberos, rpcbind, Samba, LDAP, NFS.")
    terminal = ContainerImage.objects.filter(kind="terminal").order_by("id").last()
    light = ResourceProfile.objects.get(name="Light")
    medium = ResourceProfile.objects.get(name="Medium")

    print("instructor ready, phase:", phase.slug, "terminal:", terminal)

    lab(phase, "enumeration-fundamentals-and-smb-netbios",
        "Enumeration Fundamentals & SMB/NetBIOS", 0, light, terminal, [enum],
        summary="Learn the purpose of enumeration, then discover the Globex SMB file shares with smbclient and enum4linux.",
        theory="""# Enumeration Fundamentals & SMB/NetBIOS

## What is enumeration?

Enumeration is the systematic extraction of low-hanging but highly valuable
information from services you already found open during the Scanning phase:

* valid **user accounts** and usernames
* **share names** and published network resources
* service **banners**, versions and configurations
* server roles, domains, and trust relationships

Enumeration turns a port list into an attack surface map.

## SMB and NetBIOS

The Globex file server speaks the **SMB/CIFS** protocol on TCP `445` and legacy
**NetBIOS** on UDP/TCP `137-139`. Samba (smbd) answers on both. Enumerating it
lets us list shares, connected users, and OS details.

Tools used in this lab:

| Tool | Purpose |
|------|---------|
| `smbclient -L //host` | list shares |
| `smbclient //host/share` | browse a share |
| `enum4linux` | full SMB/NetBIOS/OS enumeration bundle |
| `nmap smb-enum-*` scripts | scripted share and user enumeration |

Anonymous access relies on two weaknesses: guest access (`guest ok`) and
shares that were created with no password. Both are extremely common in real
networks.""",
        notes="""## Walkthrough

Your terminal is on the same Docker network as the Globex target. Its IP is
already exported for you as `$SERVICE_IP`.

### 1. Prep your tools

```bash
apt-get update && apt-get install -y nmap smbclient
export TARGET="$SERVICE_IP"
echo "$TARGET"
```

### 2. Locate SMB services

```bash
nmap -sS -p 137,139,445 "$TARGET"
```

Note both the legacy NetBIOS ports (139) and modern SMB (445).

### 3. List the shares

```bash
smbclient -L "//$TARGET" -N
```

The `-N` flag means "no password". Write down every share name shown:
`public`, `IT-Department`, `backup` and the `IPC$` administrative share.

### 4. Peek into the public share

```bash
smbclient "//$TARGET/public" -N -c "ls"
smbclient "//$TARGET/public" -N -c "get welcome.txt -"
```

`welcome.txt` describes the share layout.

### 5. Full SMB enumeration (bonus)

```bash
apt-get install -y enum4linux
enum4linux -a "$TARGET"
```

Compare the share list, users, and OS info enum4linux reports with what
smbclient showed you. Now answer the question.""",
        ctype="question",
        question="Using `smbclient -L //$SERVICE_IP -N`, which set of shares is visible on the Globex target?",
        options='["public, IT-Department, backup, IPC$", "public, backup, IPC$", "IT-Department, IPC$", "public only"]',
        answer="public, IT-Department, backup, IPC$")

    lab(phase, "smb-share-enumeration-anonymous-access",
        "SMB Share Enumeration & Anonymous Access", 1, medium, terminal, [enum],
        summary="Stay in the Samba shares: harvest credentials from the misconfigured public share, then map what they unlock.",
        theory="""# SMB Share Enumeration & Anonymous Access

In the previous lab you listed the shares. Listing is free. **Reading** the
contents is where the finding starts.

## Anonymous and guest access

Samba shares with `guest ok = yes` or `public = yes` let anyone connect with
no password. These are commonly left open for "convenience". Attackers treat
every open share as a potential credential or data leak.

## Credential harvesting from misconfigured shares

Documents that admins "temporarily" drop into a public dropbox are a classic
leak source: password bundles, spreadsheets of users, config exports. When you
find a valid pair of corporate credentials, treat it as a pivot: try it against
more sensitive shares, the domain services, and the network at large.

## Next week's password: always in rotation

Real networks rotate credentials. A leaked bundle usually describes the CURRENT
rotation. Keep that in mind for the capstone.""",
        notes="""## Walkthrough

### 1. Open the public share

```bash
export TARGET="$SERVICE_IP"
smbclient "//$TARGET/public" -N -c "ls"
```

You'll see `welcome.txt` and `creds.txt`.

### 2. Read the credential bundle

```bash
smbclient "//$TARGET/public" -N -c "get creds.txt -"
```

The file is a **credential rotation bundle**. Note exactly which username and
password it reveals, and which account it says it belongs to.

### 3. Compare with the welcome note

```bash
smbclient "//$TARGET/public" -N -c "get welcome.txt -"
```

The notes orient you: shares, owners, and where the IT archives live.

### 4. Try the leaked credentials on the restricted share

```bash
smbclient "//$TARGET/IT-Department" -U 'globex%Globex@2026' -c "ls"
```

If the pair works you now have read access to the IT archives — a perfect
demonstration of credential pivoting. (You will complete the final step of
that share in the capstone.)

### 5. (Optional) The backup share

```bash
smbclient "//$TARGET/backup" -N -c "ls"
```

Is the legacy backup share guest-readable too? Note what it contains. Now
answer the question.""",
        ctype="question",
        question="The anonymous `public` share leaks a credential rotation bundle. Which username:password pair does `creds.txt` reveal?",
        options='["globex / Globex@2026", "bsmith / Operations@2026", "root / toor", "svc_http / Svc@P@ss2026"]',
        answer="globex / Globex@2026")

    lab(phase, "snmp-enumeration",
        "SNMP Enumeration", 2, medium, terminal, [enum],
        summary="Probe the SNMP agent on UDP 161, compare community strings, and walk the MIB tree to enumerate the appliance.",
        theory="""# SNMP Enumeration

Simple Network Management Protocol (**SNMP**) runs over **UDP 161** and lets
managers read (and write) a device's management information base (MIB).

## Community strings

SNMP has no real authentication; the only "password" is a community string:

| Community | Typical role |
|-----------|--------------|
| `public` | read-only, default |
| `private` | read-write, default |
| custom | site-specific |

A device configured with `public` exposes its MIB to anyone. **Version 2c**
sends the community IN THE CLEAR, so it can also be sniffed.

## Enumerating with snmpwalk/snmpget

Key OID branches:

* `1.3.6.1.2.1.1` — system info (description, uptime, hostname, location)
* `1.3.6.1.2.1.2` — interfaces
* `1.3.6.1.2.1.25` — processes, software, users

A limited view (a few OIDs) versus the full tree tells you there are multiple
communities at play — an enumeration win by itself.""",
        notes="""## Walkthrough

### 1. Install the SNMP client

```bash
apt-get update && apt-get install -y snmp
export TARGET="$SERVICE_IP"
```

### 2. Single OID read with the default community

```bash
snmpget -v2c -c public "$TARGET" 1.3.6.1.2.1.1.1.0
```

You get the system description **"Globex Enumeration Appliance v2.7.1"** — a
useful service fingerprint.

### 3. Walk the whole tree with `public`

```bash
snmpwalk -v2c -c public "$TARGET" .1
```

Notice how little a walk with `public` returns: the agent restricts that
community to a view.

### 4. This device has a custom community

Production appliances often add a second, richer community. Try common values:

```bash
snmpwalk -v2c -c globex "$TARGET" 1.3.6.1.2.1.1
snmpwalk -v2c -c globex "$TARGET" 1.3.6.1.2.1.2.2.1.2
```

The `globex` community walks much further: interfaces, counters, and more.

### 5. Prove the difference

```bash
snmpwalk -v2c -c globex "$TARGET" .1 | wc -l
snmpwalk -v2c -c public "$TARGET" .1 | wc -l
```

Many more OIDs are readable with the right community. Answer the question.""",
        ctype="question",
        question="Which SNMP community string grants UNRESTRICTED (full MIB) access on the Globex appliance?",
        options='["globex", "public", "private", "community"]',
        answer="globex")

    lab(phase, "ldap-enumeration",
        "LDAP Enumeration", 3, medium, terminal, [enum],
        summary="Bind anonymously to the OpenLDAP directory and walk the Globex tree: users, groups, mail attributes and service accounts.",
        theory="""# LDAP Enumeration

Lightweight Directory Access Protocol (**LDAP**) uses **TCP 389** (cleartext)
and 636 (LDAPS). Directories store every identity in an organisation: users,
groups, computers, printers, service accounts.

## Directory structure

Entries live in a tree rooted at the **base DN**:

```
dc=globex, dc=local            <- domain component
├── ou=People                  <- users
│   ├── cn=Bob Smith
│   └── cn=Jane Taylor
└── ou=Groups                  <- groups
```

Each entry has **attributes** — and admins routinely stuff useful clues into
free-text attributes such as `description` or `info`.

## Anonymous bind

Misconfigured `slapd`/Active Directory lets you `search` with NO credentials.
`ldapsearch -x` performs an anonymous bind and returns the entire tree unless
access controls stop it. This is one of the fastest ways to dump every username
in an environment.

## What to harvest

* `uid` / `cn`: usernames (feed into Kerberos, SMTP VRFY, brute-force lists)
* `mail`: addresses (cross-check with SMTP)
* `description`/`info`: comments — often leaking roles or credentials
* service accounts (`svc_*`): application identities, prime for Kerberoasting later""",
        notes="""## Walkthrough

### 1. Install the LDAP client

```bash
apt-get update && apt-get install -y ldap-utils
export TARGET="$SERVICE_IP"
```

### 2. Confirm the service

```bash
nmap -sV -p 389 "$TARGET"
```

### 3. Anonymous search of the whole tree

```bash
ldapsearch -x -H ldap://$TARGET -b "dc=globex,dc=local"
```

You receive every entry: People, Groups, and all their attributes. Collect the
list of `cn=`/`uid=` usernames.

### 4. Limit output to the juicy fields

```bash
ldapsearch -x -H ldap://$TARGET -b "dc=globex,dc=local" description mail sn
```

### 5. Focus on the service account

```bash
ldapsearch -x -H ldap://$TARGET -b "dc=globex,dc=local" "(cn=*HTTP*)"
```

Look closely at `svc_http`'s **description** attribute — someone left an
operational note pointing straight at the Kerberos realm. Also check
`bsmith`'s description for a hint about SMB credentials.

### 6. Count your loot

```bash
ldapsearch -x -H ldap://$TARGET -b "dc=globex,dc=local" "(objectClass=*)"
```

You now own the entire directory identity list. Answer the question.""",
        ctype="question",
        question="Which LDAP service account leaks its Kerberos principal inside its `description` attribute?",
        options='["svc_http", "globex", "jdoe", "jtaylor"]',
        answer="svc_http")

    lab(phase, "nfs-and-rpc-enumeration",
        "NFS & RPC Enumeration", 4, medium, terminal, [enum],
        summary="Enumerate the portmapper, identify NFS programs, list exports with showmount, and read files from the open share.",
        theory="""# NFS & RPC Enumeration

## RPC and rpcbind

The **rpcbind** service (port **111**) is the network's RPC registrar. Clients
ask rpcbind "who runs program X?" and get back a port number. Every RPC-based
service registers here — that means **the portmap is a directory of services**:

| Program | Number | Purpose |
|---------|--------|---------|
| portmapper | 100000 | rpcbind itself |
| nfs | 100003 | file access protocol (v2/v3/v4) |
| mountd | 100005 | handles mount requests / export list |

## rpcinfo and showmount

* `rpcinfo -p host` — dump every registered RPC service and its port.
* `showmount -e host` — ask mountd for the list of NFS **exports**.

An NFS export is a directory a server shares over the network. Export rules are
described in `/etc/exports`. A world-readable export is a silent file-drop.

## Reading mounts from a locked-down box

Kernel NFS mounts (`mount -t nfs -o nolock`) need privileges that security
containers may deny. User-space clients — `nfs-ls`, `nfs-cat` — speak NFSv3
over the network with no kernel mount at all, which is perfect for
enumeration.""",
        notes="""## Walkthrough

### 1. Install NFS + RPC tools

```bash
apt-get update && apt-get install -y nfs-common rpcbind libnfs-utils
export TARGET="$SERVICE_IP"
```

### 2. Dump the portmap

```bash
rpcinfo -p "$TARGET"
```

Identify every program and its port. You are hunting for **nfs (100003)** and
**mountd (100005)**.

### 3. Ask mountd what is exported

```bash
showmount -e "$TARGET"
```

The answer: `/export/enroll` is shared to the lab network (CIDR shown is the
export rule).

### 4. Browse the export with a user-space client

```bash
nfs-ls nfs://$TARGET/export/enroll
```

### 5. Read a file

```bash
nfs-cat nfs://$TARGET/export/enroll/roster.csv
```

`roster.csv` lists the corporate accounts — the same identities you saw in LDAP
and will verify in SMTP next.

### 6. Cross-reference the audit note

```bash
nfs-cat nfs://$TARGET/export/enroll/README-NFS.txt
nfs-cat nfs://$TARGET/export/enroll/audit-report.txt
```

The README and audit notes confirm the account map and the KDC realm. Now
answer the question.""",
        ctype="question",
        question="Which path is exposed as an NFS export on the Globex target?",
        options='["/export/enroll", "/export/hr", "/srv/smb/it", "/var/www/html"]',
        answer="/export/enroll")

    lab(phase, "smtp-and-service-banner-enumeration",
        "SMTP & Service Banner Enumeration", 5, medium, terminal, [enum],
        summary="Grab service banners across the appliance and use SMTP VRFY/EXPN to confirm which usernames exist.",
        theory="""# SMTP & Service Banner Enumeration

## Banner grabbing

Many services announce themselves with a **banner** on connect: the product,
version, and (sometimes) OS. Grabbing banners is idle, fast, and legal to do
against a target you are allowed to test — every banner is one more data point
for version-based lookup (searchsploit / CVE mapping).

* FTP: `SYST` / `STAT` commands
* HTTP: response `Server:` header, `X-Powered-By`
* SMTP: the `220` greeting line
* SSH: version string

## SMTP VRFY / EXPN

SMTP servers accept command verbs that can double as user enumeration:

| Command | Asks |
|---------|------|
| `VRFY user` | "does this mailbox exist?" → `252` yes / `550` no |
| `EXPN list` | "expand this mailing list" → member addresses |
| `RCPT TO:` | "can you deliver to this address?" → `250` yes / `550` no |

Because mail servers have to answer these to interoperate, they are rarely
locked down — a permanent user enumeration oracle.

## Correlate everything

An enumerated mail username is your Joining-the-dots anchor: same account
appears in LDAP (`uid`), the Kerberos principal list, SMTP VRFY, and NFS
roster.csv. Consistent accounts = real identities.""",
        notes="""## Walkthrough

### 1. Banner-grab the whole appliance

```bash
apt-get update && apt-get install -y nmap curl
export TARGET="$SERVICE_IP"

nmap -sV -p 21,25,53,80,88,111,139,389,445,2049 "$TARGET"
```

Every banner you receive identifies the exact service stack. The appendix
above explains each one.

### 2. SMTP banner

```bash
timeout 5 bash -c 'exec 3<>/dev/tcp/$SERVICE_IP/25; cat <&3 & sleep 1; printf "EHLO x\\r\\nQUIT\\r\\n" >&3; sleep 1'
```

Read the `220 globex.local ESMTP GlobexMail 2.3.1` greeting and the EHLO
extension list — note that `VRFY` and `EXPN` are advertised.

### 3. Verify users

```bash
printf "EHLO x\\r\\nVRFY bsmith\\r\\nVRFY root\\r\\nVRFY webmaster\\r\\nQUIT\\r\\n" \
  | timeout 5 bash -c 'exec 3<>/dev/tcp/$SERVICE_IP/25; cat <&3 & sleep 1; cat >&3; sleep 2'
```

A `252` reply means the user exists; a `550` means rejected user unknown.

### 4. Expand a mailing list

```bash
printf "EHLO x\\r\\nEXPN webteam\\r\\nQUIT\\r\\n" \
  | timeout 5 bash -c 'exec 3<>/dev/tcp/$SERVICE_IP/25; cat <&3 & sleep 1; cat >&3; sleep 2'
```

The webteam distribution expands to real mailboxes.

### 5. Match accounts across services

Compare the confirmed mailboxes with `roster.csv` from the NFS lab and the LDAP
`uid`s. Same people, five channels. Answer the question.""",
        ctype="question",
        question="SMTP VRFY enumeration confirms which of these as a VALID mailbox on the Globex mail service?",
        options='["bsmith", "root", "webmaster", "admin"]',
        answer="bsmith")

    lab(phase, "kerberos-and-service-enumeration",
        "Kerberos & Service Enumeration", 6, medium, terminal, [enum],
        summary="Identify the KDC on TCP 88 and recover the full set of Kerberos principals with nmap's krb5-enum-users script.",
        theory="""# Kerberos & Service Enumeration

Kerberos is the authentication engine of Windows domains and MIT realms. The
**Key Distribution Center (KDC)** listens on **TCP/UDP 88** and hands out
tickets.

## Realms and principals

A **realm** is Kerberos's "domain" (traditionally UPPERCASE, e.g. `GLOBEX.LOCAL`).
A **principal** identifies a user or service: `bsmith@GLOBEX.LOCAL`,
`svc_http@GLOBEX.LOCAL`.

## Enumerating users via the KDC

Kerberos accidentally exposes whether a user exists: send an AS-REQ (a ticket
request) for a username and the KDC replies differently:

| Response | Meaning |
|----------|---------|
| `KDC_ERR_PREAUTH_REQUIRED` | user EXISTS — answer "prove who you are" |
| `KDC_ERR_C_PRINCIPAL_UNKNOWN` | user does NOT exist |

Nmap's `krb5-enum-users` script automates exactly this over TCP 88 using a
wordlist — a clean user/principal enumeration attack straight from CEH Module
4. The realm is the script's one required argument; you can find it in the
`version.txt`/HTTP fingerprints or the LDAP `description` leak from the LDAP
lab.""",
        notes="""## Walkthrough

### 1. Locate Kerberos

```bash
apt-get update && apt-get install -y nmap
export TARGET="$SERVICE_IP"
nmap -sV -p 88 "$TARGET"
```

The fingerprint `MIT Kerberos` plus the server's advertised time confirms a KDC
lives on the realm you saw hinted in the LDAP `svc_http` description.

### 2. Build a small user list

```bash
printf "admin\nroot\njdoe\nbsmith\njtaylor\nglobex\nsvc_http\nwebmaster\n" > /tmp/users.txt
```

### 3. Enumerate principals via the KDC

```bash
nmap -p 88 --script krb5-enum-users --script-args "krb5-enum-users.realm=GLOBEX.LOCAL,userdb=/tmp/users.txt" "$TARGET"
```

The script marks the **valid principals** in its output.

### 4. Compare with the 'unknown' ones

`admin`, `root` and `webmaster` should NOT appear as principals — the KDC
rejected them with unknown-principal, which is exactly the behaviour that makes
this enumeration reliable.

### 5. Confirm via the service account

Notice `svc_http@GLOBEX.LOCAL` — the service account your LDAP lab sniffed out.
Kerberos now confirms it, hinting at potential service-ticket attacks in a
later phase. Answer the question.""",
        ctype="question",
        question="Kerberos enumeration with `krb5-enum-users` reveals the KDC realm. Which realm is correct?",
        options='["GLOBEX.LOCAL", "globex.local", "GLOBEX.COM", "globex"]',
        answer="GLOBEX.LOCAL")

    lab(phase, "enumeration-capstone",
        "Enumeration Capstone", 7, medium, terminal, [enum],
        summary="Capstone: run the full enumeration methodology on the Globex appliance and pivot from an anonymous share to the restricted IT archive to capture the flag.",
        theory="""# Enumeration Capstone

Everything in the Enumeration phase comes together. Follow the CEH enumeration
methodology end to end:

1. **Port & service identification** — what is actually running?
2. **SMB/NetBIOS** — list shares, spot the anonymous ones.
3. **Anonymous share dive** — harvest the leaked credential bundle.
4. **Credential pivot** — use the recovered pair on the restricted share.
5. **Recover the flag** — the restricted IT archive holds it.

The other enumeration channels (LDAP, SNMP, NFS, SMTP, Kerberos) are your
corroboration layer: every username, community, realm and export you already
found supports the SMB trail.

> **Persistence pays off.** The verbose service banner from the very first scan
> keeps telling you the same thing: everything interesting lives in the file
> shares, and the public dropbox leaks the key to the IT archives.""",
        notes="""## Walkthrough

### 1. Prep

```bash
apt-get update && apt-get install -y nmap smbclient
export TARGET="$SERVICE_IP"
```

### 2. Full port sweep + versions

```bash
nmap -sS -p- -T4 --open "$TARGET"
nmap -sV -sC -p 21,25,53,80,88,111,139,389,445,2049 "$TARGET"
```

Build the complete service map. `139/445` are the file shares you will use.

### 3. List the shares

```bash
smbclient -L "//$TARGET" -N
```

The anonymous tab: `public`, `backup`; the restricted one: `IT-Department`.

### 4. Harvest the leaked credentials

```bash
smbclient "//$TARGET/public" -N -c "get creds.txt -"
```

`creds.txt` is the **email rotation bundle**. The account and password revealed
are the exact pair the IT-Department share is guarded by.

### 5. Pivot to the restricted share

```bash
smbclient "//$TARGET/IT-Department" -U 'globex%Globex@2026' -c "ls"
```

You are now inside the IT archives.

### 6. Recover the flag

```bash
smbclient "//$TARGET/IT-Department" -U 'globex%Globex@2026' -c "get flag.txt -"
```

Submit the complete flag. Every other enumeration channel you practised in this
phase simply corroborated the same identity map — which is precisely how real
assessments proceed.""",
        flag="Globex{enumeration_complete_2026}",
        flag_hint="The IT-Department share is the final goal. It is credential-protected but not anonymous — the exact pair you need was left in the anonymous public share's creds.txt (credential rotation bundle). Read it, then authenticate to the share with smbclient -U.",
        ctype="flag")

    print("DONE")

if __name__ == "__main__":
    run()