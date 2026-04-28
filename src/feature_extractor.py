"""
Derive features from normalised log DataFrame: tld, domain_length, label_count, time_bucket.
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


def add_features(df: pd.DataFrame, time_bucket_minutes: int = 5) -> pd.DataFrame:
    """
    Add columns: tld, domain_length, label_count, time_bucket.
    time_bucket is floor of timestamp to N-minute bucket.
    """
    out = df.copy()
    out["tld"] = out["domain"].astype(str).map(extract_tld)
    out["domain_length"] = out["domain"].astype(str).map(extract_domain_length)
    out["label_count"] = out["domain"].astype(str).map(extract_label_count)

    if "timestamp" in out.columns and pd.api.types.is_datetime64_any_dtype(out["timestamp"]):
        out["time_bucket"] = out["timestamp"].dt.floor(f"{time_bucket_minutes}min")
    else:
        out["time_bucket"] = pd.NaT
    return out
