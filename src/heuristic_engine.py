"""
Transparent heuristics (baseline-driven): long domains, burst windows, NXDOMAIN-like, rare TLD.
Each finding: type, evidence, why_flagged. Output: outputs/<dataset>/findings.json.
No security/threat language — use "unusual behaviour" wording.
"""
import json
from pathlib import Path
from typing import Any

import pandas as pd


# Hard threshold for long domain (chars) if baseline stats unavailable
LONG_DOMAIN_HARD_THRESHOLD = 60
# Burst: bucket count > baseline_p95 * multiplier
BURST_MULTIPLIER = 2.0
# Rare TLD: frequency < this fraction of total
RARE_TLD_THRESHOLD = 0.01


def _get_baseline_stats(baseline_metrics: dict[str, Any] | None) -> dict[str, Any]:
    """Extract baseline mean/std for domain length and p95 for bucket count."""
    stats = {
        "domain_length_mean": None,
        "domain_length_std": None,
        "bucket_count_p95": None,
    }
    if not baseline_metrics:
        return stats
    length_dist = baseline_metrics.get("domain_length_distribution") or []
    if length_dist:
        lengths = []
        for row in length_dist:
            L = row.get("domain_length")
            c = row.get("count", 0)
            lengths.extend([L] * c)
        if lengths:
            s = pd.Series(lengths)
            stats["domain_length_mean"] = float(s.mean())
            stats["domain_length_std"] = float(s.std()) if len(lengths) > 1 else 0.0
    vol = baseline_metrics.get("volume_over_time") or []
    if vol:
        counts = [r.get("count", 0) for r in vol]
        if counts:
            stats["bucket_count_p95"] = float(pd.Series(counts).quantile(0.95))
    return stats


def run_heuristics(
    df: pd.DataFrame,
    dataset_name: str,
    baseline_metrics: dict[str, Any] | None,
    outputs_root: str | Path,
) -> list[dict]:
    """
    Run heuristics; write findings to outputs/<dataset_name>/findings.json.
    Returns list of findings.
    """
    findings: list[dict] = []
    base = _get_baseline_stats(baseline_metrics)

    # --- Long domains ---
    if "domain_length" in df.columns:
        mean_len = base.get("domain_length_mean")
        std_len = base.get("domain_length_std")
        if mean_len is not None and std_len is not None and std_len > 0:
            threshold = mean_len + 2 * std_len
        else:
            threshold = LONG_DOMAIN_HARD_THRESHOLD
        long_domains = df[df["domain_length"] > threshold]
        if not long_domains.empty:
            for _, row in long_domains.drop_duplicates("domain").head(20).iterrows():
                findings.append({
                    "type": "long_domain",
                    "evidence": {"domain": row["domain"], "length": int(row["domain_length"])},
                    "why_flagged": f"Domain length {int(row['domain_length'])} exceeds threshold {threshold:.0f} (baseline-driven or hard limit). Unusual behaviour.",
                })

    # --- Burst windows ---
    if "time_bucket" in df.columns and pd.api.types.is_datetime64_any_dtype(df["time_bucket"]):
        bucket_counts = df.groupby("time_bucket").size()
        p95_baseline = base.get("bucket_count_p95")
        if p95_baseline is not None and p95_baseline > 0:
            burst_threshold = p95_baseline * BURST_MULTIPLIER
        else:
            burst_threshold = bucket_counts.quantile(0.95) * BURST_MULTIPLIER if len(bucket_counts) else 0
        burst_buckets = bucket_counts[bucket_counts > burst_threshold]
        for bucket, count in burst_buckets.items():
            findings.append({
                "type": "burst_window",
                "evidence": {"time_bucket": pd.Timestamp(bucket).isoformat(), "query_count": int(count)},
                "why_flagged": f"Query count in time window ({int(count)}) exceeds baseline-driven threshold. Unusual high volume.",
            })

    # --- Rare TLD ---
    if "tld" in df.columns:
        tld_counts = df["tld"].value_counts()
        total = len(df)
        if total > 0:
            for tld, count in tld_counts.items():
                if count / total < RARE_TLD_THRESHOLD:
                    domains_sample = df[df["tld"] == tld]["domain"].head(5).tolist()
                    findings.append({
                        "type": "rare_tld",
                        "evidence": {"tld": tld, "count": int(count), "sample_domains": domains_sample},
                        "why_flagged": f"TLD '{tld}' appears in <1% of queries. Unusual behaviour.",
                    })

    # NXDOMAIN-like: we do not have rcode in dnsmasq pihole.log. The plan says to "simulate failed lookups
    # by querying known invalid domains during dataset generation and track them separately". So NXDOMAIN
    # behaviour is reflected by the nxdomain dataset having many unique non-existent domains; we can flag
    # datasets that have a high ratio of unique domains to total queries (many one-off failures) if we had
    # that signal. Alternatively we add a heuristic: "nxdomain_like" when unique_domains/total_queries is
    # very high and domain_length is high (random-looking). Use a simple proxy: many unique domains with
    # no or low repeat = unusual. We'll add a heuristic that flags when unique_domains/total > 0.9 and
    # total > 20 as "nxdomain_like" (many one-off lookups).
    total_q = len(df)
    if total_q > 20 and df["domain"].nunique() / total_q > 0.9:
        findings.append({
            "type": "nxdomain_like",
            "evidence": {"unique_domains": int(df["domain"].nunique()), "total_queries": total_q},
            "why_flagged": "High ratio of unique domains to total queries (many one-off lookups). Unusual behaviour often associated with failed lookups.",
        })

    out_dir = Path(outputs_root) / dataset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "findings.json", "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)
    return findings
