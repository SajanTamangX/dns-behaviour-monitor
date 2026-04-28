"""
Parse Pi-hole pihole.log (dnsmasq format) into a normalised DataFrame.
Schema: timestamp, domain, query_type, client, source.
Skips malformed lines; tracks total, parsed, skipped.
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# dnsmasq query line: "Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1"
QUERY_RE = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+dnsmasq\[\d+\]:\s+query\[([^\]]+)\]\s+(\S+)\s+from\s+(\S+)\s*$"
)
SOURCE = "pihole"


def _parse_timestamp(ts_str: str, year: int | None = None) -> Any:
    """Parse 'Feb 20 12:57:15' to datetime; use year if provided."""
    try:
        dt = datetime.strptime(ts_str.strip(), "%b %d %H:%M:%S")
        if year is not None:
            dt = dt.replace(year=year)
        return dt
    except ValueError:
        return pd.NaT


def parse_log(log_path: str | Path, default_year: int | None = None) -> tuple[pd.DataFrame, dict]:
    """
    Parse Pi-hole log file. Returns (DataFrame with normalised records, stats dict).
    stats: total_lines, parsed_lines, skipped_lines.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        raise FileNotFoundError(str(log_path))

    year = default_year or datetime.now().year
    rows: list[dict] = []
    total_lines = 0
    parsed_lines = 0
    query_attempts = 0  # lines that look like query lines (contain "query[")

    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            total_lines += 1
            line = line.rstrip("\n")
            if "]: query[" in line:
                query_attempts += 1
            m = QUERY_RE.match(line)
            if not m:
                continue
            parsed_lines += 1
            ts_str, query_type, domain, client = m.groups()
            ts = _parse_timestamp(ts_str, year)
            rows.append({
                "timestamp": ts,
                "domain": domain.strip(),
                "query_type": query_type.strip().upper(),
                "client": client.strip(),
                "source": SOURCE,
            })

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
    }
    return df, stats
