#!/usr/bin/env python3
"""
School Time Filter
==================
A DNS-based parental control tool for Windows.

During school hours, ONLY websites in the allowed list will work.
Everything else (YouTube, gaming, AI, social media) is blocked.

Must be run as Administrator.
"""

import os
import sys
import json
import logging
import datetime
import socket
import threading
import time
import subprocess
import ctypes

# ── Auto-elevate to Administrator on Windows ──────────────────────────────────
if sys.platform == "win32":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(f'"{a}"' for a in sys.argv), None, 1
        )
        sys.exit(0)

# ── Auto-install dnslib if missing ────────────────────────────────────────────
try:
    import dnslib
    import dnslib.server
except ImportError:
    print("Installing required package 'dnslib'...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "dnslib"])
    import dnslib
    import dnslib.server

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
LOG_FILE    = os.path.join(SCRIPT_DIR, "filter.log")

# ── Default configuration (written to config.json on first run) ───────────────
DEFAULT_CONFIG = {
    "school_hours": {
        "monday":    {"start": "08:00", "end": "15:30"},
        "tuesday":   {"start": "08:00", "end": "15:30"},
        "wednesday": {"start": "08:00", "end": "15:30"},
        "thursday":  {"start": "08:00", "end": "15:30"},
        "friday":    {"start": "08:00", "end": "15:30"},
        "saturday":  None,
        "sunday":    None
    },
    "_comment_allowed_domains": "Add your school's website domains below. Use *.example.com to allow all subdomains.",
    "allowed_domains": [
        "localhost",
        "microsoft.com",
        "*.microsoft.com",
        "windowsupdate.com",
        "*.windowsupdate.com",
        "khanacademy.org",
        "*.khanacademy.org",
        "classroom.google.com",
        "accounts.google.com",
        "docs.google.com",
        "drive.google.com",
        "slides.google.com",
        "sheets.google.com",
        "forms.google.com",
        "meet.google.com",
        "*.myschool.edu"
    ],
    "upstream_dns":      "8.8.8.8",
    "upstream_dns_port": 53,
    "listen_port":       53,
    "log_blocked":       True
}


# ── Config helpers ────────────────────────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        # Back-fill any missing keys from defaults
        for key, val in DEFAULT_CONFIG.items():
            cfg.setdefault(key, val)
        return cfg
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ── Time helpers ──────────────────────────────────────────────────────────────
def is_school_hours(cfg):
    now      = datetime.datetime.now()
    day_name = now.strftime("%A").lower()
    schedule = cfg["school_hours"].get(day_name)
    if not schedule:
        return False
    start_h, start_m = map(int, schedule["start"].split(":"))
    end_h,   end_m   = map(int, schedule["end"].split(":"))
    start_t = datetime.time(start_h, start_m)
    end_t   = datetime.time(end_h,   end_m)
    return start_t <= now.time() <= end_t


# ── Domain matching ───────────────────────────────────────────────────────────
def is_allowed(domain, allowed_domains):
    domain = domain.lower().rstrip(".")
    for pattern in allowed_domains:
        if not isinstance(pattern, str):
            continue
        pattern = pattern.lower()
        if pattern.startswith("*."):
            suffix = pattern[2:]
            if domain == suffix or domain.endswith("." + suffix):
                return True
        else:
            if domain == pattern or domain.endswith("." + pattern):
                return True
    return False


# ── Upstream DNS forwarding ───────────────────────────────────────────────────
def forward_query(data, upstream, port, timeout=5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(data, (upstream, port))
        response, _ = sock.recvfrom(4096)
        sock.close()
        return response
    except Exception as exc:
        logging.warning(f"Upstream DNS error: {exc}")
        return None


# ── DNS Resolver ──────────────────────────────────────────────────────────────
class SchoolFilterResolver(dnslib.server.BaseResolver):
    def __init__(self, cfg):
        self.cfg = cfg

    def resolve(self, request, handler):
        domain = str(request.q.qname).rstrip(".")

        if is_school_hours(self.cfg) and not is_allowed(domain, self.cfg["allowed_domains"]):
            if self.cfg.get("log_blocked"):
                logging.info(f"BLOCKED  {domain}")
            reply = request.reply()
            reply.header.rcode = dnslib.RCODE.NXDOMAIN
            return reply

        # Allow: forward to upstream DNS
        logging.debug(f"ALLOWED  {domain}")
        data = forward_query(
            request.pack(),
            self.cfg["upstream_dns"],
            self.cfg.get("upstream_dns_port", 53),
        )
        if data:
            try:
                return dnslib.DNSRecord.parse(data)
            except Exception:
                pass

        # Upstream failed — return SERVFAIL
        reply = request.reply()
        reply.header.rcode = dnslib.RCODE.SERVFAIL
        return reply


# ── Windows DNS configuration ─────────────────────────────────────────────────
def _get_active_adapters():
    result = subprocess.run(
        ["powershell", "-Command",
         "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -ExpandProperty Name"],
        capture_output=True, text=True
    )
    return [a.strip() for a in result.stdout.strip().splitlines() if a.strip()]


def set_dns_to_localhost():
    """Point all active network adapters' DNS at the local filter."""
    for adapter in _get_active_adapters():
        subprocess.run(
            ["powershell", "-Command",
             f'Set-DnsClientServerAddress -InterfaceAlias "{adapter}" -ServerAddresses "127.0.0.1"'],
            check=False
        )
        logging.info(f"DNS → 127.0.0.1 for: {adapter}")


def restore_dns():
    """Reset network adapters back to automatic (DHCP) DNS."""
    for adapter in _get_active_adapters():
        subprocess.run(
            ["powershell", "-Command",
             f'Set-DnsClientServerAddress -InterfaceAlias "{adapter}" -ResetServerAddresses'],
            check=False
        )
        logging.info(f"DNS restored for: {adapter}")


# ── Firewall rules: block kids from bypassing with external DNS ───────────────
FIREWALL_RULE_NAME = "SchoolFilter-BlockExternalDNS"

def apply_firewall_rules():
    """Block outbound DNS port 53 to external servers (prevents DNS bypass)."""
    # Remove old rules first (idempotent)
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={FIREWALL_RULE_NAME}"],
        capture_output=True
    )
    # Block UDP 53 outbound to everything except loopback
    subprocess.run([
        "netsh", "advfirewall", "firewall", "add", "rule",
        f"name={FIREWALL_RULE_NAME}", "dir=out", "action=block",
        "protocol=UDP", "remoteport=53",
        "remoteip=1.0.0.0-126.255.255.255,128.0.0.0-223.255.255.255"
    ], check=False)
    # Block TCP 53 outbound as well (DoT bypass prevention)
    subprocess.run([
        "netsh", "advfirewall", "firewall", "add", "rule",
        f"name={FIREWALL_RULE_NAME}-TCP", "dir=out", "action=block",
        "protocol=TCP", "remoteport=53",
        "remoteip=1.0.0.0-126.255.255.255,128.0.0.0-223.255.255.255"
    ], check=False)
    logging.info("Firewall rules applied: external DNS port 53 blocked")


def remove_firewall_rules():
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={FIREWALL_RULE_NAME}"],
        capture_output=True
    )
    subprocess.run(
        ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={FIREWALL_RULE_NAME}-TCP"],
        capture_output=True
    )
    logging.info("Firewall rules removed")


# ── Logging setup ─────────────────────────────────────────────────────────────
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    setup_logging()
    cfg = load_config()

    logging.info("=" * 60)
    logging.info("School Time Filter  —  starting")
    logging.info(f"Config : {CONFIG_FILE}")
    logging.info(f"Log    : {LOG_FILE}")
    logging.info(f"Allowed: {len([d for d in cfg['allowed_domains'] if isinstance(d,str)])} domain patterns")
    logging.info("=" * 60)

    set_dns_to_localhost()
    apply_firewall_rules()

    resolver = SchoolFilterResolver(cfg)
    dns_logger = dnslib.server.DNSLogger(prefix=False)
    server = dnslib.server.DNSServer(
        resolver,
        port=cfg.get("listen_port", 53),
        address="127.0.0.1",
        logger=dns_logger,
    )

    server.start_thread()
    logging.info(f"DNS filter listening on 127.0.0.1:{cfg.get('listen_port', 53)}")

    try:
        while True:
            # Reload config every 5 minutes so changes take effect without restart
            cfg = load_config()
            resolver.cfg = cfg
            status = "ACTIVE (school hours)" if is_school_hours(cfg) else "standby (non-school hours)"
            logging.info(f"Status: {status}")
            time.sleep(300)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        server.stop()
        remove_firewall_rules()
        restore_dns()
        logging.info("DNS restored. Goodbye.")


if __name__ == "__main__":
    main()
