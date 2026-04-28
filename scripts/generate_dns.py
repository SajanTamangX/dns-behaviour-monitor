#!/usr/bin/env python3
"""
DNS query generator for 127.0.0.1:5354. Profiles: baseline, burst, nxdomain, longdomain.
Uses dnspython for port-configurable queries (nslookup on Windows cannot set port).
"""
import argparse
import random
import string
import time
import sys

try:
    import dns.resolver
    import dns.query
    import dns.message
except ImportError:
    print("Install dnspython: pip install dnspython", file=sys.stderr)
    sys.exit(1)

DNS_SERVER = "127.0.0.1"
DNS_PORT = 5354

# Popular domains for baseline (real domains that resolve)
BASELINE_DOMAINS = [
    "google.com", "github.com", "stackoverflow.com", "wikipedia.org", "amazon.com",
    "microsoft.com", "youtube.com", "reddit.com", "twitter.com", "linkedin.com",
    "cloudflare.com", "apple.com", "netflix.com", "spotify.com", "zoom.us",
    "slack.com", "dropbox.com", "medium.com", "bbc.co.uk", "cnn.com",
]


def query_a(domain: str) -> tuple[bool, str | None]:
    """Send A query to resolver; return (success, rcode_or_none)."""
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = [DNS_SERVER]
    resolver.port = DNS_PORT
    try:
        resolver.resolve(domain, "A")
        return True, None
    except dns.resolver.NXDOMAIN:
        return False, "NXDOMAIN"
    except Exception as e:
        return False, str(type(e).__name__)


def run_baseline(count: int = 80, sleep_sec: float = 0.5) -> None:
    """Normal popular domains over time."""
    for _ in range(count):
        domain = random.choice(BASELINE_DOMAINS)
        ok, rcode = query_a(domain)
        print(f"  {domain} -> {'ok' if ok else rcode}")
        time.sleep(sleep_sec)


def run_burst(count: int = 100, sleep_sec: float = 0.02) -> None:
    """Rapid repeated queries (high QPS)."""
    domains = random.choices(BASELINE_DOMAINS, k=count)
    for domain in domains:
        ok, rcode = query_a(domain)
        print(f"  {domain} -> {'ok' if ok else rcode}")
        time.sleep(sleep_sec)


def run_nxdomain(count: int = 50, sleep_sec: float = 0.3) -> None:
    """Random non-existent domains (failed lookups for heuristic)."""
    for _ in range(count):
        # Random subdomain + random string so it almost certainly does not exist
        label = "".join(random.choices(string.ascii_lowercase, k=12))
        tld = random.choice(["com", "net", "org", "xyz"])
        domain = f"{label}.nonexistent-{label}.{tld}"
        ok, rcode = query_a(domain)
        print(f"  {domain} -> {'ok' if ok else rcode}")
        time.sleep(sleep_sec)


def run_longdomain(count: int = 40, sleep_sec: float = 0.4) -> None:
    """Deep subdomain / long domain strings."""
    for _ in range(count):
        # Very long subdomain chain
        parts = [
            "".join(random.choices(string.ascii_lowercase, k=20))
            for _ in range(random.randint(4, 7))
        ]
        domain = ".".join(parts) + ".com"
        ok, rcode = query_a(domain)
        print(f"  {domain} -> {'ok' if ok else rcode}")
        time.sleep(sleep_sec)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate DNS traffic to 127.0.0.1:5354")
    p.add_argument("--profile", required=True, choices=["baseline", "burst", "nxdomain", "longdomain"])
    p.add_argument("--count", type=int, default=None, help="Override loop count")
    p.add_argument("--sleep", type=float, default=None, help="Override sleep between queries (sec)")
    args = p.parse_args()

    defaults = {
        "baseline": (80, 0.5),
        "burst": (100, 0.02),
        "nxdomain": (50, 0.3),
        "longdomain": (40, 0.4),
    }
    count, sleep_sec = defaults[args.profile]
    if args.count is not None:
        count = args.count
    if args.sleep is not None:
        sleep_sec = args.sleep

    print(f"Profile: {args.profile}  count={count}  sleep={sleep_sec}s  target={DNS_SERVER}:{DNS_PORT}")
    if args.profile == "baseline":
        run_baseline(count, sleep_sec)
    elif args.profile == "burst":
        run_burst(count, sleep_sec)
    elif args.profile == "nxdomain":
        run_nxdomain(count, sleep_sec)
    else:
        run_longdomain(count, sleep_sec)
    print("Done.")


if __name__ == "__main__":
    main()
