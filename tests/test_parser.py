"""
Parser tests: required columns, timestamp parsing, success rate >= 95%,
response-code correlation between query and reply lines.

Can be run with pytest or: python -m tests.test_parser
"""
import tempfile
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.log_parser import parse_log, QUERY_RE, REPLY_RE

REQUIRED_COLUMNS = {"timestamp", "domain", "query_type", "client", "response_code", "source"}


def _write(lines: list[str]) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False)
    f.writelines(lines)
    f.close()
    return f.name


def test_required_columns_exist():
    """Validate parsed DataFrame has the full normalised schema."""
    path = _write([
        "Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1\n",
        "Feb 20 12:57:16 dnsmasq[196]: query[AAAA] test.org from 127.0.0.1\n",
    ])
    try:
        df, _ = parse_log(path)
        assert not df.empty
        for col in REQUIRED_COLUMNS:
            assert col in df.columns, f"Missing column: {col}"
    finally:
        Path(path).unlink(missing_ok=True)


def test_timestamp_parsing():
    """Validate timestamp parsing produces datetime-like values."""
    path = _write([
        "Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1\n",
    ])
    try:
        df, _ = parse_log(path)
        assert "timestamp" in df.columns
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"]) or len(df) == 0
    finally:
        Path(path).unlink(missing_ok=True)


def test_parser_success_rate():
    """Parser success rate >= 95% on query lines; non-query lines skipped safely."""
    lines = [
        "Feb 20 12:56:48 dnsmasq[196]: started, version pi-hole-v2.92rc1 cachesize 10000\n",
        "Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1\n",
        "Feb 20 12:57:16 dnsmasq[196]: query[A] google.com from 127.0.0.1\n",
        "Feb 20 12:57:17 dnsmasq[196]: query[PTR] 1.0.0.127.in-addr.arpa from 172.18.0.1\n",
        "Feb 20 12:57:18 dnsmasq[196]: Pi-hole hostname pi.hole is 127.0.0.1\n",
        "Feb 20 12:57:19 dnsmasq[196]: query[AAAA] example.com from 127.0.0.1\n",
    ]
    path = _write(lines)
    try:
        df, stats = parse_log(path)
        assert stats["parsed_lines"] == 4
        assert stats["total_lines"] == 6
        assert stats["skipped_lines"] == 2
        assert stats["parse_success_rate"] >= 95.0
        assert len(df) == 4
    finally:
        Path(path).unlink(missing_ok=True)


def test_regex_matches_query_and_reply_lines():
    """QUERY_RE matches query lines only; REPLY_RE matches reply/cached/config."""
    assert QUERY_RE.match("Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1")
    assert QUERY_RE.match("Feb 20 13:02:32 dnsmasq[196]: query[PTR] 1.0.0.127.in-addr.arpa from 172.18.0.1")
    assert not QUERY_RE.match("Feb 20 12:56:48 dnsmasq[196]: started, version pi-hole-v2.92rc1")
    assert not QUERY_RE.match("Feb 20 12:57:15 dnsmasq[196]: Pi-hole hostname pi.hole is 127.0.0.1")
    assert REPLY_RE.match("Feb 20 12:57:15 dnsmasq[196]: reply example.com is 1.2.3.4")
    assert REPLY_RE.match("Feb 20 12:57:15 dnsmasq[196]: cached example.com is 1.2.3.4")
    assert REPLY_RE.match("Feb 20 12:57:15 dnsmasq[196]: reply foo.test is NXDOMAIN")
    assert not REPLY_RE.match("Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1")


def test_response_code_correlation_noerror_and_nxdomain():
    """Each query is correlated with the matching reply line and gets a real rcode."""
    lines = [
        "Feb 20 12:57:15 dnsmasq[196]: query[A] example.com from 127.0.0.1\n",
        "Feb 20 12:57:15 dnsmasq[196]: forwarded example.com to 8.8.8.8\n",
        "Feb 20 12:57:15 dnsmasq[196]: reply example.com is 93.184.216.34\n",
        "Feb 20 12:57:16 dnsmasq[196]: query[A] does-not-exist.test from 127.0.0.1\n",
        "Feb 20 12:57:16 dnsmasq[196]: forwarded does-not-exist.test to 8.8.8.8\n",
        "Feb 20 12:57:16 dnsmasq[196]: reply does-not-exist.test is NXDOMAIN\n",
        "Feb 20 12:57:17 dnsmasq[196]: query[A] cached.example from 127.0.0.1\n",
        "Feb 20 12:57:17 dnsmasq[196]: cached cached.example is 10.0.0.1\n",
    ]
    path = _write(lines)
    try:
        df, stats = parse_log(path)
        assert len(df) == 3
        rcodes = dict(zip(df["domain"], df["response_code"]))
        assert rcodes["example.com"] == "NOERROR"
        assert rcodes["does-not-exist.test"] == "NXDOMAIN"
        assert rcodes["cached.example"] == "NOERROR"
        assert stats["queries_with_rcode"] == 3
        assert stats["replies_seen"] >= 3
    finally:
        Path(path).unlink(missing_ok=True)


def test_pihole_self_resolved_hostname_counts_as_noerror():
    """`Pi-hole hostname X is Y` lines back-fill the matching query as NOERROR."""
    lines = [
        "Feb 20 12:57:15 dnsmasq[196]: query[A] pi.hole from 127.0.0.1\n",
        "Feb 20 12:57:15 dnsmasq[196]: Pi-hole hostname pi.hole is 127.0.0.1\n",
    ]
    path = _write(lines)
    try:
        df, _ = parse_log(path)
        assert len(df) == 1
        assert df.iloc[0]["response_code"] == "NOERROR"
    finally:
        Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    test_required_columns_exist()
    test_timestamp_parsing()
    test_parser_success_rate()
    test_regex_matches_query_and_reply_lines()
    test_response_code_correlation_noerror_and_nxdomain()
    test_pihole_self_resolved_hostname_counts_as_noerror()
    print("All parser tests passed.")
