"""
Parse Pi-hole pihole.log (dnsmasq format) into a normalised DataFrame.

Schema: timestamp, domain, query_type, client, response_code, source.

Query lines and reply/cached/config lines are processed sequentially. Each
parsed query row is then back-filled with a response code by associating it
with the next reply/cached/config line for the same domain. This recovers the
DNS rcode (NOERROR / NXDOMAIN / NODATA / SERVFAIL) that the spec lists in
section 8.3.1 and section 1.3.2 as a core baseline metric.

Malformed and unrelated lines are skipped safely.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# dnsmasq query line:
#   "Apr 29 12:26:43 dnsmasq[68]: query[A] github.com from 172.19.0.1"
QUERY_RE = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+dnsmasq\[\d+\]:\s+query\[([^\]]+)\]\s+(\S+)\s+from\s+(\S+)\s*$"
)
# dnsmasq reply / cached / config line:
#   "Apr 29 12:26:43 dnsmasq[68]: reply github.com is 20.26.156.215"
#   "Apr 29 12:27:31 dnsmasq[68]: reply foo.example is NXDOMAIN"
#   "Apr 29 12:26:47 dnsmasq[68]: cached github.com is 20.26.156.215"
REPLY_RE = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+dnsmasq\[\d+\]:\s+(reply|cached|config)\s+(\S+)\s+is\s+(.+?)\s*$"
)
# Pi-hole self-resolved hostname line (counts as NOERROR):
#   "Apr 29 12:27:37 dnsmasq[68]: Pi-hole hostname pi.hole is 127.0.0.1"
PIHOLE_HOSTNAME_RE = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+dnsmasq\[\d+\]:\s+Pi-hole hostname\s+(\S+)\s+is\s+(.+?)\s*$"
)

SOURCE = "pihole"


def _parse_timestamp(ts_str: str, year: int) -> Any:
    """Parse 'Apr 29 12:26:43' to datetime using the supplied year."""
    try:
        dt = datetime.strptime(f"{year} {ts_str.strip()}", "%Y %b %d %H:%M:%S")
        return dt
    except ValueError:
        return pd.NaT


def _classify_rcode(reply_data: str) -> str:
    """Map the text after 'is' on a reply/cached line to a DNS rcode label."""
    s = reply_data.strip()
    if s.startswith("NXDOMAIN"):
        return "NXDOMAIN"
    if s.startswith("NODATA"):
        return "NODATA"
    if s.startswith("SERVFAIL"):
        return "SERVFAIL"
    if s.startswith("REFUSED"):
        return "REFUSED"
    return "NOERROR"


def parse_log(log_path: str | Path, default_year: int | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Parse a Pi-hole / dnsmasq log file and return:
      - DataFrame with columns: timestamp, domain, query_type, client,
        response_code, source.
      - stats dict: total_lines, query_attempts, parsed_lines, skipped_lines,
        parse_success_rate, replies_seen, queries_with_rcode.

    response_code is derived by matching each query to the next reply/cached/
    config line for the same domain. Unmatched queries get response_code=None.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        raise FileNotFoundError(str(log_path))

    year = default_year or datetime.now().year
    rows: list[dict] = []
    pending_idx_by_domain: dict[str, list[int]] = {}

    total_lines = 0
    parsed_lines = 0
    query_attempts = 0
    replies_seen = 0
    queries_with_rcode = 0

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            line = line.rstrip("\n")

            if "]: query[" in line:
                query_attempts += 1
                m = QUERY_RE.match(line)
                if not m:
                    continue
                ts_str, query_type, domain, client = m.groups()
                domain = domain.strip()
                rows.append({
                    "timestamp": _parse_timestamp(ts_str, year),
                    "domain": domain,
                    "query_type": query_type.strip().upper(),
                    "client": client.strip(),
                    "response_code": None,
                    "source": SOURCE,
                })
                parsed_lines += 1
                pending_idx_by_domain.setdefault(domain, []).append(len(rows) - 1)
                continue

            m_reply = REPLY_RE.match(line)
            if m_reply:
                replies_seen += 1
                _, _kind, domain, data = m_reply.groups()
                domain = domain.strip()
                rcode = _classify_rcode(data)
                pending = pending_idx_by_domain.get(domain)
                if pending:
                    idx = pending.pop(0)
                    if rows[idx]["response_code"] is None:
                        rows[idx]["response_code"] = rcode
                        queries_with_rcode += 1
                continue

            m_self = PIHOLE_HOSTNAME_RE.match(line)
            if m_self:
                replies_seen += 1
                _, domain, _data = m_self.groups()
                domain = domain.strip()
                pending = pending_idx_by_domain.get(domain)
                if pending:
                    idx = pending.pop(0)
                    if rows[idx]["response_code"] is None:
                        rows[idx]["response_code"] = "NOERROR"
                        queries_with_rcode += 1
                continue

    skipped_lines = total_lines - parsed_lines
    parse_success_rate = round(parsed_lines / query_attempts * 100, 1) if query_attempts else 100.0
    df = pd.DataFrame(rows)
    if not df.empty and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df = df.sort_values("timestamp").reset_index(drop=True)

    stats = {
        "total_lines": total_lines,
        "query_attempts": query_attempts,
        "parsed_lines": parsed_lines,
        "skipped_lines": skipped_lines,
        "parse_success_rate": parse_success_rate,
        "replies_seen": replies_seen,
        "queries_with_rcode": queries_with_rcode,
    }
    return df, stats
