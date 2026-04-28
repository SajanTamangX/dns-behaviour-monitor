"""
Compute baseline metrics from parsed+featured DataFrame: volume over time, top domains,
TLD distribution, domain length distribution. Write JSON summary and CSV tables to outputs/<dataset_name>/.
"""
import json
from pathlib import Path
from typing import Any

import pandas as pd


def compute_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """Compute all metrics; return dict suitable for JSON and tables."""
    if df.empty:
        return {
            "total_queries": 0,
            "unique_domains": 0,
            "time_range": {},
            "volume_over_time": [],
            "top_domains": [],
            "tld_distribution": [],
            "domain_length_distribution": [],
        }
    total = len(df)
    unique = df["domain"].nunique()
    ts = df["timestamp"]
    time_range = {}
    if pd.api.types.is_datetime64_any_dtype(ts):
        time_range = {
            "min": pd.Timestamp(ts.min()).isoformat() if pd.notna(ts.min()) else None,
            "max": pd.Timestamp(ts.max()).isoformat() if pd.notna(ts.max()) else None,
        }

    volume_over_time = []
    if "time_bucket" in df.columns and pd.api.types.is_datetime64_any_dtype(df["time_bucket"]):
        vol = df.groupby("time_bucket").size().reset_index(name="count")
        volume_over_time = [
            {"bucket": pd.Timestamp(r["time_bucket"]).isoformat(), "count": int(r["count"])}
            for _, r in vol.iterrows()
        ]

    top_domains = (
        df["domain"]
        .value_counts()
        .head(50)
        .reset_index()
    )
    top_domains.columns = ["domain", "count"]
    top_domains = top_domains.to_dict("records")

    tld_dist = []
    if "tld" in df.columns:
        tld_dist = (
            df["tld"]
            .value_counts()
            .reset_index()
        )
        tld_dist.columns = ["tld", "count"]
        tld_dist = tld_dist.to_dict("records")

    length_dist = []
    if "domain_length" in df.columns:
        length_dist = (
            df["domain_length"]
            .value_counts()
            .sort_index()
            .reset_index()
        )
        length_dist.columns = ["domain_length", "count"]
        length_dist = length_dist.to_dict("records")

    label_count_dist = []
    if "label_count" in df.columns:
        label_count_dist = (
            df["label_count"]
            .value_counts()
            .sort_index()
            .reset_index()
        )
        label_count_dist.columns = ["label_count", "count"]
        label_count_dist = label_count_dist.to_dict("records")

    query_type_dist = []
    if "query_type" in df.columns:
        query_type_dist = (
            df["query_type"]
            .value_counts()
            .reset_index()
        )
        query_type_dist.columns = ["query_type", "count"]
        query_type_dist = query_type_dist.to_dict("records")

    return {
        "total_queries": int(total),
        "unique_domains": int(unique),
        "time_range": time_range,
        "volume_over_time": volume_over_time,
        "top_domains": top_domains,
        "tld_distribution": tld_dist,
        "domain_length_distribution": length_dist,
        "label_count_distribution": label_count_dist,
        "query_type_distribution": query_type_dist,
    }


def write_outputs(metrics: dict[str, Any], dataset_name: str, outputs_root: str | Path) -> None:
    """Write summary JSON and CSV tables to outputs/<dataset_name>/."""
    root = Path(outputs_root) / dataset_name
    root.mkdir(parents=True, exist_ok=True)

    with open(root / "summary.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    if metrics.get("volume_over_time"):
        pd.DataFrame(metrics["volume_over_time"]).to_csv(root / "volume_over_time.csv", index=False)
    if metrics.get("top_domains"):
        pd.DataFrame(metrics["top_domains"]).to_csv(root / "top_domains.csv", index=False)
    if metrics.get("tld_distribution"):
        pd.DataFrame(metrics["tld_distribution"]).to_csv(root / "tld_distribution.csv", index=False)
    if metrics.get("domain_length_distribution"):
        pd.DataFrame(metrics["domain_length_distribution"]).to_csv(
            root / "domain_length_distribution.csv", index=False
        )
    if metrics.get("label_count_distribution"):
        pd.DataFrame(metrics["label_count_distribution"]).to_csv(
            root / "label_count_distribution.csv", index=False
        )
    if metrics.get("query_type_distribution"):
        pd.DataFrame(metrics["query_type_distribution"]).to_csv(
            root / "query_type_distribution.csv", index=False
        )
