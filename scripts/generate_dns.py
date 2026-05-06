#!/usr/bin/env python3
"""
DNS query generator for 127.0.0.1:5354. Profiles: baseline, burst, nxdomain, longdomain.
Uses dnspython for port-configurable queries (nslookup on Windows cannot set port).
"""
import argparse
import random
import socket
import string
import time
import sys
from collections import Counter

try:
    import dns.resolver
    import dns.query
    import dns.message
except ImportError:
    print("Install dnspython: pip install dnspython", file=sys.stderr)
    sys.exit(1)

DNS_SERVER = "127.0.0.1"
DNS_PORT = 5354
DNS_TIMEOUT_SECONDS = 1.0

# Popular domains for baseline (real domains that resolve)
BASELINE_DOMAINS = [
    "google.com", "github.com", "stackoverflow.com", "wikipedia.org", "amazon.com",
    "microsoft.com", "youtube.com", "reddit.com", "twitter.com", "linkedin.com",
    "cloudflare.com", "apple.com", "netflix.com", "spotify.com", "zoom.us",
    "slack.com", "dropbox.com", "medium.com", "bbc.co.uk", "cnn.com",
]


def query_a(domain: str) -> tuple[bool, str | None]:
    """Send an A query packet to Pi-hole without waiting for upstream replies.

    This keeps dataset generation reliable in environments where Docker egress
    DNS is blocked or intermittent, while still producing Pi-hole query logs.
    """
    try:
        query = dns.message.make_query(domain, "A")
        payload = query.to_wire()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(DNS_TIMEOUT_SECONDS)
            sock.sendto(payload, (DNS_SERVER, DNS_PORT))
        return True, None
    except Exception as e:
        return False, str(type(e).__name__)


def emit_result(
    domain: str,
    ok: bool,
    rcode: str | None,
    quiet_timeouts: bool,
    stats: Counter[str],
) -> None:
    result = "ok" if ok else (rcode or "ERROR")
    stats[result] += 1
    if quiet_timeouts and result == "LifetimeTimeout":
        return
    print(f"  {domain} -> {result}")


def run_queries(domains: list[str], sleep_sec: float, quiet_timeouts: bool) -> Counter[str]:
    stats: Counter[str] = Counter()
    for domain in domains:
        ok, rcode = query_a(domain)
        emit_result(domain, ok, rcode, quiet_timeouts, stats)
        time.sleep(sleep_sec)
    return stats


def run_baseline(count: int = 80, sleep_sec: float = 0.5, quiet_timeouts: bool = False) -> Counter[str]:
    """Normal popular domains over time."""
    domains = [random.choice(BASELINE_DOMAINS) for _ in range(count)]
    return run_queries(domains, sleep_sec, quiet_timeouts)


def run_burst(count: int = 100, sleep_sec: float = 0.02, quiet_timeouts: bool = False) -> Counter[str]:
    """Rapid repeated queries (high QPS)."""
    domains = random.choices(BASELINE_DOMAINS, k=count)
    return run_queries(domains, sleep_sec, quiet_timeouts)


def run_nxdomain(count: int = 50, sleep_sec: float = 0.3, quiet_timeouts: bool = False) -> Counter[str]:
    """Random non-existent domains (failed lookups for heuristic)."""
    domains: list[str] = []
    for _ in range(count):
        # Random subdomain + random string so it almost certainly does not exist
        label = "".join(random.choices(string.ascii_lowercase, k=12))
        tld = random.choice(["com", "net", "org", "xyz"])
        domains.append(f"{label}.nonexistent-{label}.{tld}")
    return run_queries(domains, sleep_sec, quiet_timeouts)


def run_longdomain(count: int = 40, sleep_sec: float = 0.4, quiet_timeouts: bool = False) -> Counter[str]:
    """Deep subdomain / long domain strings."""
    domains: list[str] = []
    for _ in range(count):
        # Very long subdomain chain
        parts = [
            "".join(random.choices(string.ascii_lowercase, k=20))
            for _ in range(random.randint(4, 7))
        ]
        domains.append(".".join(parts) + ".com")
    return run_queries(domains, sleep_sec, quiet_timeouts)


def main() -> None:
    global DNS_TIMEOUT_SECONDS
    p = argparse.ArgumentParser(description="Generate DNS traffic to 127.0.0.1:5354")
    p.add_argument("--profile", required=True, choices=["baseline", "burst", "nxdomain", "longdomain"])
    p.add_argument("--count", type=int, default=None, help="Override loop count")
    p.add_argument("--sleep", type=float, default=None, help="Override sleep between queries (sec)")
    p.add_argument(
        "--timeout",
        type=float,
        default=DNS_TIMEOUT_SECONDS,
        help="Per-query timeout in seconds (default: 1.0)",
    )
    p.add_argument(
        "--quiet-timeouts",
        action="store_true",
        help="Do not print per-domain LifetimeTimeout lines; print summary instead.",
    )
    args = p.parse_args()
    DNS_TIMEOUT_SECONDS = max(0.1, args.timeout)

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

    print(
        f"Profile: {args.profile}  count={count}  sleep={sleep_sec}s  "
        f"timeout={DNS_TIMEOUT_SECONDS}s  target={DNS_SERVER}:{DNS_PORT}"
    )
    if args.profile == "baseline":
        stats = run_baseline(count, sleep_sec, args.quiet_timeouts)
    elif args.profile == "burst":
        stats = run_burst(count, sleep_sec, args.quiet_timeouts)
    elif args.profile == "nxdomain":
        stats = run_nxdomain(count, sleep_sec, args.quiet_timeouts)
    else:
        stats = run_longdomain(count, sleep_sec, args.quiet_timeouts)
    if args.quiet_timeouts and stats.get("LifetimeTimeout", 0):
        print(f"  LifetimeTimeouts suppressed: {stats['LifetimeTimeout']}")
    totals = ", ".join(f"{k}={v}" for k, v in sorted(stats.items()))
    print(f"Results: {totals if totals else 'none'}")
    print("Done.")


if __name__ == "__main__":
    main()
