"""
Parser tests: required columns, timestamp parsing, success rate >= 95%.
Can be run with pytest or: python -m tests.test_parser
"""
import tempfile
from pathlib import Path

import pandas as pd
import sys

# Project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.log_parser import parse_log, QUERY_RE

REQUIRED_COLUMNS = {"timestamp", "domain", "query_type", "client", "source"}


def test_required_columns_exist():
    """Validate parsed DataFrame has required columns."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1\n")
        f.write("Feb 20 12:57:16 dnsmasq[196]: query[AAAA] test.org from 127.0.0.1\n")
        path = f.name
    try:
        df, _ = parse_log(path)
        assert not df.empty
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"
    finally:
        Path(path).unlink(missing_ok=True)


def test_timestamp_parsing():
    """Validate timestamp parsing produces datetime-like values."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.write("Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1\n")
        path = f.name
    try:
        df, _ = parse_log(path)
        assert "timestamp" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"]) or len(df) == 0
    finally:
        Path(path).unlink(missing_ok=True)


def test_parser_success_rate():
    """Parser success rate >= 95%: most lines that are query lines get parsed; skip non-query safely."""
    lines = [
        "Feb 20 12:56:48 dnsmasq[196]: started, version pi-hole-v2.92rc1 cachesize 10000\n",
        "Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1\n",
        "Feb 20 12:57:16 dnsmasq[196]: query[A] google.com from 127.0.0.1\n",
        "Feb 20 12:57:17 dnsmasq[196]: query[PTR] 1.0.0.127.in-addr.arpa from 172.18.0.1\n",
        "Feb 20 12:57:18 dnsmasq[196]: Pi-hole hostname pi.hole is 127.0.0.1\n",
        "Feb 20 12:57:19 dnsmasq[196]: query[AAAA] example.com from 127.0.0.1\n",
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        f.writelines(lines)
        path = f.name
    try:
        df, stats = parse_log(path)
        # 4 query lines, 2 non-query
        assert stats["parsed_lines"] == 4
        assert stats["total_lines"] == 6
        assert stats["skipped_lines"] == 2
        # Success rate of query lines: 4/4 = 100%. Of all lines: 4/6 parsed (we only count query lines as "parsed")
        # Target: >= 95% of parsable (query) lines get parsed. All query lines are parsed.
        assert stats["parsed_lines"] >= 4
        assert len(df) == 4
    finally:
        Path(path).unlink(missing_ok=True)


def test_regex_matches_query_lines():
    """QUERY_RE matches dnsmasq query lines only."""
    assert QUERY_RE.match("Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1")
    assert QUERY_RE.match("Feb 20 13:02:32 dnsmasq[196]: query[PTR] 1.0.0.127.in-addr.arpa from 172.18.0.1")
    assert not QUERY_RE.match("Feb 20 12:56:48 dnsmasq[196]: started, version pi-hole-v2.92rc1")
    assert not QUERY_RE.match("Feb 20 12:57:15 dnsmasq[196]: Pi-hole hostname pi.hole is 127.0.0.1")


if __name__ == "__main__":
    test_required_columns_exist()
    test_timestamp_parsing()
    test_parser_success_rate()
    test_regex_matches_query_lines()
    print("All parser tests passed.")
