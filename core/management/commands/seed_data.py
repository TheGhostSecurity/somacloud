from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from core.models import HackPhase, ResourceProfile, Tool


DEFAULT_PHASES = [
    {"name": "Kali Linux File System", "slug": "kali-linux-file-system", "description": "Navigate the Linux file system, understand permissions, and get comfortable with the terminal before moving to enumeration.", "order": 1},
    {"name": "Footprinting & Reconnaissance", "slug": "footprinting-recon", "description": "WHOIS, DNS enumeration, website fingerprinting, robots.txt analysis, and passive information gathering.", "order": 2},
    {"name": "Scanning Networks", "slug": "scanning-networks", "description": "Ping sweep, port scanning, service detection, OS fingerprinting, and network mapping.", "order": 3},
    {"name": "Enumeration", "slug": "enumeration", "description": "HTTP, FTP, SMB, SSH, and user enumeration to extract detailed service info.", "order": 4},
    {"name": "Vulnerability Analysis", "slug": "vulnerability-analysis", "description": "Discovery of SQL injection, XSS, authentication weaknesses, file upload flaws, and command injection.", "order": 5},
    {"name": "Exploitation", "slug": "exploitation", "description": "Active exploitation of SQL injection, XSS, broken authentication, file upload, command injection, and LFI/RFI services.", "order": 6},
    {"name": "Post-Exploitation", "slug": "post-exploitation", "description": "Read sensitive files, privilege escalation basics, password hash discovery, log inspection, and evidence collection.", "order": 7},
    {"name": "Reporting & Remediation", "slug": "reporting-remediation", "description": "Capture the flag, submit findings, explain the vulnerability, recommend fixes, and complete the assessment.", "order": 8},
    {"name": "Extras", "slug": "extras", "description": "Additional challenges, CTFs, and bonus labs beyond the core curriculum.", "order": 9},
]

DEFAULT_RESOURCES = [
    {"name": "Light", "cpu_count": 0.25, "memory_mb": 256, "time_limit_minutes": 15, "gui_ready": False, "description": "Basic scanning and enumeration tasks."},
    {"name": "Medium", "cpu_count": 0.5, "memory_mb": 512, "time_limit_minutes": 30, "gui_ready": False, "description": "Standard exploitation and brute-force labs."},
    {"name": "Heavy", "cpu_count": 1, "memory_mb": 1024, "time_limit_minutes": 45, "gui_ready": False, "description": "Resource-intensive cracking and web app testing."},
    {"name": "Ultra", "cpu_count": 2, "memory_mb": 2048, "time_limit_minutes": 60, "gui_ready": False, "description": "Full network simulation with multiple targets."},
    {"name": "Desktop (GUI)", "cpu_count": 2, "memory_mb": 3072, "time_limit_minutes": 45, "gui_ready": True, "description": "GUI desktop (VNC) for Wireshark, Burp Suite and other graphical tools."},
]

DEFAULT_TOOLS = [
    {"name": "nmap", "category": "Scanning", "command": "nmap -sV -sC target"},
    {"name": "gobuster", "category": "Enumeration", "command": "gobuster dir -u target -w wordlist"},
    {"name": "nikto", "category": "Scanning", "command": "nikto -h target"},
    {"name": "netcat", "category": "Networking", "command": "nc -lvnp 4444"},
    {"name": "metasploit", "category": "Exploitation", "command": "msfconsole"},
    {"name": "sqlmap", "category": "Web", "command": "sqlmap -u target"},
    {"name": "hydra", "category": "Cracking", "command": "hydra -l user -P wordlist target ssh"},
    {"name": "john", "category": "Cracking", "command": "john hash.txt"},
    {"name": "hashcat", "category": "Cracking", "command": "hashcat -m 0 hash.txt wordlist"},
    {"name": "burpsuite", "category": "Web", "command": "java -jar burpsuite.jar"},
    {"name": "wireshark", "category": "Networking", "command": "wireshark"},
    {"name": "aircrack-ng", "category": "Wireless", "command": "aircrack-ng capture.cap"},
    {"name": "enum4linux", "category": "Enumeration", "command": "enum4linux target"},
    {"name": "smbclient", "category": "Enumeration", "command": "smbclient -L target"},
    {"name": "wfuzz", "category": "Web", "command": "wfuzz -w wordlist target"},
    {"name": "searchsploit", "category": "Exploitation", "command": "searchsploit keyword"},
    {"name": "ffuf", "category": "Web", "command": "ffuf -u target/FUZZ -w wordlist"},
    {"name": "impacket", "category": "Exploitation", "command": "impacket-secretsdump domain/user:pass@target"},
    {"name": "bloodhound", "category": "Enumeration", "command": "bloodhound-python -d domain -u user -p pass -dc target"},
    {"name": "evil-winrm", "category": "Exploitation", "command": "evil-winrm -i target -u user -H hash"},
]

INSTRUCTOR_GROUP = "Instructor"


class Command(BaseCommand):
    help = "Seed default hack phases, resource profiles, and tools into the database."

    def handle(self, *args, **options):
        self._seed_phases()
        self._seed_resources()
        self._seed_tools()
        self._seed_groups()
        self.stdout.write(self.style.SUCCESS("Seed data loaded successfully."))

    def _seed_phases(self):
        new_slugs = {p["slug"] for p in DEFAULT_PHASES}
        HackPhase.objects.exclude(slug__in=new_slugs).delete()
        count = 0
        for phase_data in DEFAULT_PHASES:
            _, created = HackPhase.objects.update_or_create(
                slug=phase_data["slug"],
                defaults=phase_data,
            )
            if created:
                count += 1
        self.stdout.write(f"  HackPhases: {count} created, {HackPhase.objects.count()} total")

    def _seed_resources(self):
        count = 0
        for r in DEFAULT_RESOURCES:
            _, created = ResourceProfile.objects.update_or_create(
                name=r["name"],
                defaults=r,
            )
            if created:
                count += 1
        self.stdout.write(f"  ResourceProfiles: {count} created, {len(DEFAULT_RESOURCES)} total")

    def _seed_tools(self):
        count = 0
        for t in DEFAULT_TOOLS:
            _, created = Tool.objects.update_or_create(
                name=t["name"],
                defaults=t,
            )
            if created:
                count += 1
        self.stdout.write(f"  Tools: {count} created, {len(DEFAULT_TOOLS)} total")

    def _seed_groups(self):
        group, created = Group.objects.get_or_create(name=INSTRUCTOR_GROUP)
        status = "created" if created else "already exists"
        self.stdout.write(f"  Group '{INSTRUCTOR_GROUP}': {status}")
