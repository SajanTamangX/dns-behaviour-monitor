"""
Run full analysis on a dataset: parse -> features -> metrics -> heuristics.
Loads baseline summary for heuristic baseline if available.
"""
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.log_parser import parse_log
from src.feature_extractor import add_features
from src.metrics_engine import compute_metrics, write_outputs
from src.heuristic_engine import run_heuristics


def run_analysis(
    log_path: str | Path,
    dataset_name: str,
    outputs_root: str | Path = "outputs",
    baseline_summary_path: str | Path | None = None,
) -> tuple[object, dict, list]:
    """
    Run full pipeline. Returns (df, metrics_dict, findings_list).
    If baseline_summary_path is set, load baseline summary for heuristic comparison.
    """
    df, parse_stats = parse_log(log_path)
    df = add_features(df)
    metrics = compute_metrics(df)
    write_outputs(metrics, dataset_name, outputs_root)

    import json as _json
    _stats_path = Path(outputs_root) / dataset_name / "parse_stats.json"
    _stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(_stats_path, "w", encoding="utf-8") as _f:
        _json.dump(parse_stats, _f, indent=2)

    baseline_metrics = None
    if baseline_summary_path and Path(baseline_summary_path).exists():
        import json
        with open(baseline_summary_path, encoding="utf-8") as f:
            baseline_metrics = json.load(f)
    findings = run_heuristics(df, dataset_name, baseline_metrics, outputs_root)
    return df, metrics, findings


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("log_path", help="Path to pihole.log or exported dataset log")
    p.add_argument("--name", required=True, help="Dataset name (e.g. baseline, burst)")
    p.add_argument("--outputs", default="outputs", help="Outputs root")
    p.add_argument("--baseline-summary", default=None, help="Path to baseline summary.json for heuristics")
    args = p.parse_args()
    run_analysis(args.log_path, args.name, args.outputs, args.baseline_summary)
    print(f"Done: {args.outputs}/{args.name}/")
