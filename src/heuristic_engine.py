"""
Transparent, baseline-driven heuristics:

  - long_domain      : domain length far above baseline (or above a hard cap).
  - burst_window     : query count in a time bucket far above baseline p95.
  - nxdomain_excess  : real NXDOMAIN ratio far above baseline ratio.
  - rare_tld         : TLD seen in <1% of queries.

Each finding is a dict with: type, evidence, why_flagged.
Output: outputs/<dataset>/findings.json.

Wording stays behavioural / analytical — no security or threat language.
"""
import json
from pathlib import Path
from typing import Any

import pandas as pd


# Hard fallback for long domain (chars) when baseline is unavailable.
LONG_DOMAIN_HARD_THRESHOLD = 60
# Burst: bucket count > baseline_p95 * multiplier (or > self p95 * multiplier
# when no baseline is supplied).
BURST_MULTIPLIER = 2.0
# Rare TLD: frequency < this fraction of total.
RARE_TLD_THRESHOLD = 0.01
# nxdomain_excess: trigger when the dataset's NXDOMAIN ratio is at least this
# many percentage points above the baseline ratio AND at least this absolute
# fraction of queries (so a clean baseline does not falsely fire on a single
# stray NXDOMAIN).
NXDOMAIN_RATIO_DELTA = 0.20
NXDOMAIN_MIN_RATIO = 0.20


def _get_baseline_stats(baseline_metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Extract baseline mean/std/max for domain length, p95 bucket count, and NXDOMAIN ratio."""
    stats: dict[str, Any] = {
        "domain_length_mean": None,
        "domain_length_std": None,
        "domain_length_max": None,
        "bucket_count_p95": None,
        "nxdomain_ratio": 0.0,
    }
    if not baseline_metrics:
        return stats

    length_dist = baseline_metrics.get("domain_length_distribution") or []
    if length_dist:
        lengths: list[int] = []
        for row in length_dist:
            L = row.get("domain_length")
            c = row.get("count", 0)
            lengths.extend([L] * c)
        if lengths:
            s = pd.Series(lengths)
            stats["domain_length_mean"] = float(s.mean())
            stats["domain_length_std"] = float(s.std()) if len(lengths) > 1 else 0.0
            stats["domain_length_max"] = int(s.max())

    vol = baseline_metrics.get("volume_over_time") or []
    if vol:
        counts = [r.get("count", 0) for r in vol]
        if counts:
            stats["bucket_count_p95"] = float(pd.Series(counts).quantile(0.95))

    rc_dist = baseline_metrics.get("response_code_distribution") or []
    if rc_dist:
        total = sum(r.get("count", 0) for r in rc_dist) or 0
        nx = next((r.get("count", 0) for r in rc_dist if r.get("response_code") == "NXDOMAIN"), 0)
        stats["nxdomain_ratio"] = (nx / total) if total else 0.0

    return stats


def run_heuristics(
    df: pd.DataFrame,
    dataset_name: str,
    baseline_metrics: dict[str, Any] | None,
    outputs_root: str | Path,
) -> list[dict]:
    """
    Run all heuristics; write findings to outputs/<dataset_name>/findings.json.
    Returns the list of findings.
    """
    findings: list[dict] = []
    base = _get_baseline_stats(baseline_metrics)

    # ---- Long domains -------------------------------------------------------
    if "domain_length" in df.columns and not df.empty:
        mean_len = base.get("domain_length_mean")
        std_len = base.get("domain_length_std")
        max_len = base.get("domain_length_max")
        if mean_len is not None and std_len is not None and std_len > 0:
            stat_threshold = mean_len + 2 * std_len
            # Never flag a length that was already seen in baseline traffic;
            # this prevents false positives on real domains the user routinely
            # visits (e.g. "stackoverflow.com").
            threshold = max(stat_threshold, float(max_len)) if max_len is not None else stat_threshold
        else:
            threshold = LONG_DOMAIN_HARD_THRESHOLD
        long_domains = df[df["domain_length"] > threshold]
        if not long_domains.empty:
            for _, row in long_domains.drop_duplicates("domain").head(20).iterrows():
                findings.append({
                    "type": "long_domain",
                    "evidence": {"domain": row["domain"], "length": int(row["domain_length"])},
                    "why_flagged": (
                        f"Domain length {int(row['domain_length'])} exceeds threshold "
                        f"{threshold:.0f} (baseline-driven or hard limit). Unusual behaviour."
                    ),
                })

    # ---- Burst windows ------------------------------------------------------
    if "time_bucket" in df.columns and pd.api.types.is_datetime64_any_dtype(df["time_bucket"]) and not df.empty:
        bucket_counts = df.groupby("time_bucket").size()
        p95_baseline = base.get("bucket_count_p95")
        if p95_baseline is not None and p95_baseline > 0:
            burst_threshold = p95_baseline * BURST_MULTIPLIER
            threshold_source = "baseline p95"
        else:
            self_p95 = bucket_counts.quantile(0.95) if len(bucket_counts) else 0
            burst_threshold = self_p95 * BURST_MULTIPLIER
            threshold_source = "self p95"
        burst_buckets = bucket_counts[bucket_counts > burst_threshold]
        for bucket, count in burst_buckets.items():
            findings.append({
                "type": "burst_window",
                "evidence": {
                    "time_bucket": pd.Timestamp(bucket).isoformat(),
                    "query_count": int(count),
                    "threshold": float(burst_threshold),
                },
                "why_flagged": (
                    f"Query count in time window ({int(count)}) exceeds {threshold_source}-driven "
                    f"threshold {burst_threshold:.0f}. Unusual high volume."
                ),
            })

    # ---- Rare TLD -----------------------------------------------------------
    if "tld" in df.columns and not df.empty:
        tld_counts = df["tld"].value_counts()
        total = len(df)
        if total > 0:
            for tld, count in tld_counts.items():
                if not tld:
                    continue
                if count / total < RARE_TLD_THRESHOLD:
                    domains_sample = df[df["tld"] == tld]["domain"].head(5).tolist()
                    findings.append({
                        "type": "rare_tld",
                        "evidence": {"tld": tld, "count": int(count), "sample_domains": domains_sample},
                        "why_flagged": f"TLD '{tld}' appears in <1% of queries. Unusual behaviour.",
                    })

    # ---- NXDOMAIN excess (uses real response codes when available) ----------
    if "response_code" in df.columns and not df.empty:
        total_q = len(df)
        nx_count = int((df["response_code"] == "NXDOMAIN").sum())
        nx_ratio = nx_count / total_q if total_q else 0.0
        baseline_ratio = base.get("nxdomain_ratio", 0.0)
        if (
            nx_ratio >= NXDOMAIN_MIN_RATIO
            and (nx_ratio - baseline_ratio) >= NXDOMAIN_RATIO_DELTA
        ):
            findings.append({
                "type": "nxdomain_excess",
                "evidence": {
                    "nxdomain_count": nx_count,
                    "total_queries": total_q,
                    "nxdomain_ratio": round(nx_ratio, 3),
                    "baseline_ratio": round(baseline_ratio, 3),
                },
                "why_flagged": (
                    f"NXDOMAIN responses are {nx_ratio*100:.1f}% of queries "
                    f"(baseline {baseline_ratio*100:.1f}%). Unusual behaviour often associated "
                    f"with repeated failed lookups."
                ),
            })

    out_dir = Path(outputs_root) / dataset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "findings.json", "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    return findings
