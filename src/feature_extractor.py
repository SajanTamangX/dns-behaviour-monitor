"""
Derive features from normalised log DataFrame:
  tld, domain_length, label_count, time_bucket.

The time bucket is configurable in seconds. A 10-second default works well
across the project's small datasets: it is fine enough to surface bursts in
the burst dataset while still grouping baseline traffic into a handful of
buckets for stable p95-style baselines.
"""
import pandas as pd


def extract_tld(domain: str) -> str:
    """Extract TLD (last label). Fallback to empty string."""
    if not domain or "." not in domain:
        return ""
    return domain.split(".")[-1].lower()


def extract_domain_length(domain: str) -> int:
    """Character length of domain."""
    return len(domain) if domain else 0


def extract_label_count(domain: str) -> int:
    """Number of labels (parts separated by dots)."""
    if not domain:
        return 0
    return len(domain.split("."))


def add_features(df: pd.DataFrame, time_bucket_seconds: int = 10) -> pd.DataFrame:
    """
    Add columns: tld, domain_length, label_count, time_bucket.

    time_bucket is the floor of timestamp to a bucket of `time_bucket_seconds`.
    """
    out = df.copy()
    out["tld"] = out["domain"].astype(str).map(extract_tld)
    out["domain_length"] = out["domain"].astype(str).map(extract_domain_length)
    out["label_count"] = out["domain"].astype(str).map(extract_label_count)

    if "timestamp" in out.columns and pd.api.types.is_datetime64_any_dtype(out["timestamp"]):
        out["time_bucket"] = out["timestamp"].dt.floor(f"{int(time_bucket_seconds)}s")
    else:
        out["time_bucket"] = pd.NaT
    return out
