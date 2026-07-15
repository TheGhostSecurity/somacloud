from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import HackPhase, ResourceProfile, Tool, Lab, ContainerImage

RECON_SLUG = "footprinting-recon"
ENUM_SLUG = "enumeration"


def _recon_lab_1():
    return {
        "title": "WHOIS & DNS Reconnaissance",
        "slug": "whois-dns-recon",
        "summary": "Learn how to gather intelligence about a target domain using WHOIS lookups and DNS enumeration tools like `dig` and `nslookup`.",
        "order": 1,
        "tools": ["nmap"],
        "flag": "FLAG{dns_recon_master}",
        "flag_hint": "Check the TXT records of the target domain using `dig`.",
        "theory_content": """
## What is Reconnaissance?

Reconnaissance is the first phase of any security assessment. It involves collecting as much information as possible about a target before launching any active attacks. Think of it as a detective gathering clues before making a move.

There are two types of recon:

- :tip[Passive Recon]{Gathering information without directly interacting with the target. Examples: WHOIS lookups, search engine queries, social media.}
- :tip[Active Recon]{Interacting with the target's systems directly. Examples: DNS queries, ping sweeps, port scans.}

This lab focuses on **passive and light-active DNS recon** — the least intrusive techniques that give you a treasure trove of data.

## WHOIS Lookups

WHOIS is a protocol that queries databases storing registered domain information. Every domain registration is required to provide contact and technical details.

### What WHOIS reveals:

- Registrant name and organization
- Registration and expiry dates
- Name servers
- Administrative and technical contacts

:q[What kind of information can you find through a WHOIS lookup?]{Registrant contact details|The server's root password|The website's database schema|Registrant contact details|}

### Using `whois` on Kali

Open a terminal and run:

```bash
whois example.com
```

This returns the full WHOIS record. For ethical hacking, you always perform WHOIS lookups only on domains you own or have explicit permission to test.

## DNS Enumeration

The Domain Name System (DNS) translates human-readable domain names into IP addresses. It also stores many other types of records that leak information about a target's infrastructure.

### Key DNS record types:

| Record | Purpose | Example |
|--------|---------|---------|
| **A** | Maps domain to IPv4 address | `example.com → 93.184.216.34` |
| **AAAA** | Maps domain to IPv6 address | `example.com → 2606:2800:220:1:248:1893:25c8:1946` |
| **MX** | Mail exchange server | `mail.example.com` |
| **NS** | Name servers | `ns1.example.com` |
| **TXT** | Arbitrary text (often for verification) | `SPF records, DKIM keys` |
| **CNAME** | Canonical name (alias) | `www → example.com` |

### Using `dig` (DNS Swiss Army Knife)

```bash
dig example.com ANY        # Get all record types
dig example.com A          # Get A record
dig example.com MX         # Get mail servers
dig example.com NS         # Get name servers
dig example.com TXT        # Get TXT records
```

:q[Which `dig` command would you use to find the mail servers for a domain?]{dig example.com MX|dig example.com A|dig example.com TXT|dig example.com MX|}

### Using `nslookup` (Simpler Alternative)

```bash
nslookup example.com
nslookup -type=MX example.com
nslookup -type=TXT example.com
```

## Zone Transfers

A :tip[zone transfer]{A DNS zone transfer is a mechanism for replicating DNS records across name servers. When misconfigured, it allows anyone to download the entire DNS database for a domain.} is a powerful misconfiguration. If a DNS server allows zone transfers to anyone, you can download all DNS records at once.

```bash
dig axfr @ns1.example.com example.com
```

If successful, this will dump every DNS record for the domain — subdomains, internal hosts, everything.

## Putting It All Together

A typical recon workflow:

1. **WHOIS lookup** → get registrant info and name servers
2. **DNS enumeration** → identify A, MX, NS, TXT records
3. **Attempt zone transfer** → try to dump all records
4. **Document findings** → record IPs, subdomains, and services discovered
""",
    }


def _recon_lab_2():
    return {
        "title": "Website Fingerprinting & Technology Detection",
        "slug": "website-fingerprinting",
        "summary": "Identify the technology stack powering a website — web server, CMS, frameworks, and third-party services — using passive and active techniques.",
        "order": 2,
        "tools": ["nmap", "nikto", "burpsuite"],
        "flag": "FLAG{tech_detective}",
        "flag_hint": "Check the X-Powered-By header or look for common CMS paths.",
        "theory_content": """
## Why Fingerprint a Website?

Before you can exploit a web application, you need to know what it's built with. A WordPress site requires different techniques than a custom Node.js app. Identifying the technology stack helps you:

- Choose the right tools and exploits
- Understand the attack surface
- Find version-specific vulnerabilities

:tip[Banner Grabbing]{The technique of connecting to a service and reading its welcome banner, which often reveals the software name and version.}

## Passive Fingerprinting

### Checking HTTP Headers

Every web server responds with HTTP headers that leak information. Run:

```bash
curl -I https://example.com
```

Look for these headers:

- `Server` — reveals web server (Apache, Nginx, IIS)
- `X-Powered-By` — reveals backend technology (PHP, ASP.NET, Express)
- `Set-Cookie` — session cookie names often reveal the framework

:q[Which HTTP header most directly reveals the backend programming language?]{X-Powered-By|Server|Content-Type|X-Powered-By|}

### Checking `robots.txt`

```bash
curl https://example.com/robots.txt
```

The `robots.txt` file tells search engines which paths to avoid. But it also tells **you** which paths the owner considers sensitive — a great starting point for enumeration.

### Checking `sitemap.xml`

```bash
curl https://example.com/sitemap.xml
```

Sitemaps list all pages the site wants indexed. This gives you a complete map of the application.

## Active Fingerprinting

### Using `whatweb` (Kali Tool)

```bash
whatweb example.com
```

This tool analyzes the entire page and identifies the CMS, JavaScript libraries, analytics tools, and more.

### Using `nmap` Service Detection

```bash
nmap -sV -p 80,443 example.com
```

The `-sV` flag enables version detection. Nmap will probe the open ports and report the exact software version running.

```bash
nmap -sV --script=http-headers -p 80,443 example.com
```

## Detecting Specific CMS Platforms

### WordPress
- Check `/wp-admin/`, `/wp-content/`, `/wp-json/`
- Look for `wp-` in page source or cookies

### Joomla
- Check `/administrator/`, ` components/`, `/modules/`
- Look for `joomla` in meta tags

### Drupal
- Check `/user/`, `/node/1`, `/CHANGELOG.txt`

:tip[Pro Tip]{Always check the `/CHANGELOG.txt` or `/readme.html` on popular CMS platforms — they often include the exact version number.}

## Putting It All Together

A typical fingerprinting workflow:

1. **Curl headers** → identify web server and backend language
2. **Check robots.txt & sitemap.xml** → discover hidden paths
3. **Use whatweb** → identify CMS and JavaScript libraries
4. **Nmap version scan** → detect all services with versions
5. **Document findings** → record tech stack for exploitation phase
""",
    }


def _recon_lab_3():
    return {
        "title": "OSINT & Subdomain Enumeration",
        "slug": "osint-subdomain-enum",
        "summary": "Use open-source intelligence techniques to discover subdomains, email addresses, and leaked information about a target.",
        "order": 3,
        "tools": ["gobuster", "ffuf"],
        "flag": "FLAG{osint_collector}",
        "flag_hint": "Try searching for subdomains using common wordlists like `common.txt`.",
        "theory_content": """
## What is OSINT?

:tip[OSINT]{Open-Source Intelligence — collecting information from publicly available sources like search engines, social media, and public databases.}

OSINT is the art of finding information that's already public but not obvious. A target may leak sensitive data through job postings, forum posts, or misconfigured cloud storage.

## Google Dorking

Google's advanced search operators can reveal hidden information about a target:

```text
site:example.com              # All pages on the domain
site:example.com filetype:pdf # All PDFs on the domain
inurl:admin                   # Pages with "admin" in the URL
intitle:"index of"            # Directory listing pages
```

### Common Google Dorks for Recon

:q[Which Google dork would find login pages on a specific domain?]{site:example.com inurl:login|filetype:pdf site:example.com|intitle:"index of"|site:example.com inurl:login|}

**Try these:**
- `site:example.com intitle:login` — find login pages
- `site:example.com ext:sql | ext:bak` — find database backups
- `site:example.com "password"` — find pages mentioning passwords

## Subdomain Enumeration

Subdomains often reveal hidden parts of a target's infrastructure:
- `admin.example.com` — admin panel
- `dev.example.com` — development environment
- `mail.example.com` — email server
- `api.example.com` — internal API

### Brute-Force with Gobuster

```bash
gobuster dns -d example.com -w /usr/share/wordlists/dns/subdomains-top1million-5000.txt
```

This tries thousands of common subdomain names against the target domain.

### Brute-Force with Ffuf (DNS Mode)

```bash
ffuf -w /usr/share/wordlists/dns/subdomains-top1million-5000.txt -u http://example.com -H "Host: FUZZ.example.com" -fs 0
```

## Certificate Transparency Logs

Every SSL/TLS certificate issued is logged in public :tip[Certificate Transparency]{A public log system that records every SSL/TLS certificate issued by a Certificate Authority.} logs. You can search these logs to find all subdomains that have certificates — which is often ALL subdomains.

Use `crt.sh`:

```text
https://crt.sh/?q=%25.example.com
```

This returns every certificate issued for `*.example.com`, revealing all subdomains.

## Email & User Enumeration

### Hunter.io / theHarvester

```bash
theHarvester -d example.com -b google
```

This searches Google for emails, hosts, and virtual hosts related to the domain.

## Putting It All Together

A complete OSINT workflow:

1. **Google dorking** → find exposed documents and login pages
2. **Subdomain brute-force** → discover hidden subdomains with gobuster
3. **Certificate transparency** → find all subdomains via crt.sh
4. **Email discovery** → identify employee email addresses
5. **Document findings** → map the full external footprint
""",
    }


def _enum_lab_1():
    return {
        "title": "SMB Enumeration",
        "slug": "smb-enumeration",
        "summary": "Enumerate SMB shares, users, and system information using enum4linux, smbclient, and other tools.",
        "order": 1,
        "tools": ["enum4linux", "smbclient", "nmap"],
        "flag": "FLAG{smb_share_found}",
        "flag_hint": "Look for the `Shares` directory on the target SMB server.",
        "theory_content": """
## What is SMB?

:tip[SMB]{Server Message Block — a network protocol used for sharing files, printers, and other resources between computers on a network. Commonly used by Windows systems.}

SMB (Server Message Block) is a file-sharing protocol primarily used by Windows. It runs on **port 445** (SMB over TCP) and sometimes **port 139** (NetBIOS over TCP).

## Enumerating SMB with Nmap

First, discover SMB services on the target:

```bash
nmap -p 445,139 --script=smb-enum-shares target.com
```

The `smb-enum-shares` script lists all shared folders on the target.

### Nmap SMB Scripts

Nmap has many SMB enumeration scripts:

```bash
nmap -p 445 --script=smb-enum-shares,smb-enum-users,smb-os-discovery target.com
```

- `smb-enum-shares` — list available shares
- `smb-enum-users` — enumerate system users
- `smb-os-discovery` — detect OS version

:q[Which Nmap script lists available SMB shares on a target?]{smb-enum-shares|smb-enum-users|smb-os-discovery|smb-enum-shares|}

## Using enum4linux

`enum4linux` is a dedicated SMB enumeration tool that automates many tasks:

```bash
enum4linux -a target.com
```

The `-a` flag performs all enumeration options:

- List shares
- List users
- List groups
- List password policy
- Check for null sessions

:tip[Null Session]{An SMB connection made without valid credentials. Misconfigured Windows systems allow anonymous access, revealing extensive system information.}

## Using smbclient

Connect to an SMB share:

```bash
smbclient //target.com/SHARENAME -N
```

The `-N` flag attempts a null session (no password). Once connected, use:

- `ls` — list files
- `get filename` — download a file
- `put filename` — upload a file
- `exit` — disconnect

## Manual SMB Enumeration

### Listing Shares with smbclient

```bash
smbclient -L target.com -N
```

This lists all available shares without connecting.

### Common SMB Shares to Check

| Share Name | Purpose |
|------------|---------|
| `C$` | Admin hidden C: drive |
| `Admin$` | Admin hidden directory |
| `IPC$` | Inter-process communication |
| `Shares` | Common user-created share |
| `Data` | Common user-created share |
| `Backup` | Common user-created share |

## Putting It All Together

A typical SMB enumeration workflow:

1. **Nmap scan** → find open ports 139/445
2. **Run enum4linux** → gather all available info
3. **List shares** → use smbclient to enumerate shares
4. **Try null sessions** → connect without credentials
5. **Download interesting files** → extract data from open shares
6. **Document findings** → record usernames, shares, OS info
""",
    }


def _enum_lab_2():
    return {
        "title": "HTTP & Directory Enumeration",
        "slug": "http-directory-enum",
        "summary": "Enumerate web directories, hidden files, and backup archives using gobuster, ffuf, and nikto.",
        "order": 2,
        "tools": ["gobuster", "ffuf", "nikto", "wfuzz"],
        "flag": "FLAG{dir_buster}",
        "flag_hint": "Look for the `/secret` directory using a wordlist like `directory-list-2.3-medium.txt`.",
        "theory_content": """
## Why Enumerate Web Directories?

Web applications often have hidden directories that aren't linked from the main page. These may contain:

- Admin panels
- Backup files (`.bak`, `.old`, `~`)
- Configuration files (`.env`, `config.php`)
- Development versions of the site
- Uploaded files

:tip[Directory Busting]{The technique of systematically trying thousands of common directory and file names against a web server to discover hidden resources.}

## Using Gobuster

Gobuster is a fast directory brute-forcing tool:

```bash
gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt
```

### Useful Flags

- `-u` — target URL
- `-w` — wordlist path
- `-x php,txt,html` — file extensions to append
- `-t 50` — threads (faster but louder)
- `-s 200,204,301,302` — only show these status codes

:q[Which gobuster flag adds file extensions like `.php` and `.bak` to each word?]{-x|-e|-f|-X|-x|}

### Common Wordlists

| Wordlist | Location | Size |
|----------|----------|------|
| Common | `/usr/share/wordlists/dirb/common.txt` | ~4600 words |
| Medium | `/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` | ~220k words |
| Big | `/usr/share/wordlists/dirbuster/directory-list-2.3-big.txt` | ~870k words |

## Using ffuf (Faster Alternative)

`ffuf` is a modern, high-performance fuzzing tool:

```bash
ffuf -u http://target.com/FUZZ -w /usr/share/wordlists/dirb/common.txt
```

The `FUZZ` keyword marks where the wordlist entries are inserted.

### Filtering Results

```bash
ffuf -u http://target.com/FUZZ -w wordlist.txt -fs 1234
```

- `-fs 1234` — filter out responses with size 1234 (useful for false positives)
- `-fc 404` — filter out 404 status codes

## Using nikto

Nikto is a comprehensive web server scanner:

```bash
nikto -h http://target.com
```

It checks for:

- Outdated server software
- Dangerous files/CGIs
- Misconfigurations
- Default files and directories

## Checking for Backup Files

Web developers often leave backup files on the server:

```bash
gobuster dir -u http://target.com -w wordlist.txt -x bak,txt,old,php~,swp,save
```

Common backup file names to check:

- `index.php~` or `index.php.bak` — Vim/editor backups
- `.htaccess.save` — Apache config backup
- `wp-config.php.bak` — WordPress backup
- `config.php.old` — Old config file

:tip[Vim Swap Files]{Vim creates `.swp` files when editing. Accessing `/.index.php.swp` can reveal the source code of PHP files!}

## Putting It All Together

A typical web enumeration workflow:

1. **Gobuster directory scan** → find hidden paths
2. **Extension scan** → look for backup files (.bak, .old, ~)
3. **Nikto scan** → identify vulnerabilities and misconfigurations
4. **Check interesting paths** → manually inspect discovered directories
5. **Document findings** → map the full web application structure
""",
    }


def _enum_lab_3():
    return {
        "title": "Service Enumeration with Nmap",
        "slug": "service-enum-nmap",
        "summary": "Master Nmap's service detection, version enumeration, and NSE scripts to identify and fingerprint running services.",
        "order": 3,
        "tools": ["nmap", "netcat"],
        "flag": "FLAG{version_hunter}",
        "flag_hint": "Find the exact version of the SSH service on the target using Nmap's version detection.",
        "theory_content": """
## Why Service Enumeration?

Knowing what services are running on a target tells you:

- What operating system is in use
- What software versions are deployed
- What vulnerabilities might exist
- What attack vectors are available

:tip[Service Fingerprinting]{The process of identifying the exact software and version running on an open port by analyzing its behavior and response.}

## Nmap Version Detection

Basic service detection:

```bash
nmap -sV target.com
```

The `-sV` flag probes open ports to determine service versions.

### Aggressive Detection

```bash
nmap -sV --version-intensity 9 target.com
```

The version intensity (1-9) controls how deep Nmap probes. Higher is more accurate but louder.

:q[Which Nmap flag enables version detection?]{-sV|-sS|-sT|-O|-sV|}

## Operating System Detection

```bash
nmap -O target.com
```

Nmap uses TCP/IP stack fingerprinting to guess the operating system. Combine with version detection:

```bash
nmap -sV -O target.com
```

## Nmap NSE Scripts

The Nmap Scripting Engine (NSE) extends Nmap with enumeration and vulnerability detection scripts.

### Service-Specific Scripts

```bash
# SSH enumeration
nmap -p 22 --script=ssh2-enum-algos,ssh-hostkey target.com

# FTP enumeration
nmap -p 21 --script=ftp-anon,ftp-bounce target.com

# HTTP enumeration
nmap -p 80,443 --script=http-enum,http-headers target.com

# Database enumeration
nmap -p 3306 --script=mysql-info target.com
```

### Categories of NSE Scripts

| Category | Purpose | Example |
|----------|---------|---------|
| `safe` | Won't crash services | `http-headers` |
| `intrusive` | May affect services | `smb-enum-shares` |
| `vuln` | Check for vulnerabilities | `smb-vuln-ms17-010` |
| `discovery` | Discover more info | `dns-zone-transfer` |
| `auth` | Auth-related checks | `ftp-anon` |

Run all safe scripts:

```bash
nmap -sV --script=safe target.com
```

## Manual Banner Grabbing

Sometimes manual inspection is more reliable than automated tools.

### Using Netcat

```bash
nc -nv target.com 22
```

This connects to port 22 (SSH) and shows the banner:

```text
SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6
```

### Using OpenSSL for HTTPS

```bash
openssl s_client -connect target.com:443
```

## Putting It All Together

A complete service enumeration workflow:

1. **Nmap port scan** → find all open ports (`-p-`)
2. **Version detection** → identify service versions (`-sV`)
3. **OS detection** → identify OS (`-O`)
4. **NSE scripts** → run service-specific scripts (`--script=...`)
5. **Manual banner grab** → confirm versions with netcat
6. **Document findings** → record all services, versions, and OS details
""",
    }


LAB_DEFS = {
    RECON_SLUG: [_recon_lab_1, _recon_lab_2, _recon_lab_3],
    ENUM_SLUG: [_enum_lab_1, _enum_lab_2, _enum_lab_3],
}


class Command(BaseCommand):
    help = "Populate Footprinting & Reconnaissance and Enumeration phases with structured lab content."

    def add_arguments(self, parser):
        parser.add_argument("--instructor", default="burhani", help="Username of the instructor to own the labs.")

    def handle(self, *args, **options):
        instructor = User.objects.filter(username=options["instructor"]).first()
        if not instructor:
            self.stderr.write(f"Instructor '{options['instructor']}' not found. Create one first.")
            return

        for slug, lab_builders in LAB_DEFS.items():
            phase = HackPhase.objects.filter(slug=slug).first()
            if not phase:
                self.stderr.write(f"Phase '{slug}' not found. Run seed_data first.")
                continue

            resource = ResourceProfile.objects.filter(name="Light").first() or ResourceProfile.objects.first()
            if not resource:
                self.stderr.write("No ResourceProfile found.")
                continue

            created_count = 0
            for builder in lab_builders:
                data = builder()
                tool_names = data.pop("tools", [])
                tools = list(Tool.objects.filter(name__in=tool_names))
                defaults = {k: v for k, v in data.items() if k != "tools"}
                defaults.update(
                    hack_phase=phase,
                    instructor=instructor,
                    resource_profile=resource,
                    is_published=True,
                )
                lab, created = Lab.objects.update_or_create(
                    slug=data["slug"],
                    hack_phase=phase,
                    defaults=defaults,
                )
                if created:
                    lab.tools.set(tools)
                    lab.save()
                    created_count += 1
                self.stdout.write(f"  {'Created' if created else 'Updated'} lab: {lab.title}")

            self.stdout.write(self.style.SUCCESS(f"{phase.name}: {created_count} labs created"))
