# Evaluation Summary

Reference run on the four committed datasets in `data/*.log`.
Re-run any time with `.\scripts\run_evaluation.ps1` (Pi-hole running) or by
invoking `python src\run_analysis.py` against the existing logs (no Pi-hole
required, since the datasets are checked in).

## Parser quality

Target: ≥ 95 % parse success on query lines.

| dataset    | total queries | unique domains | parse success rate |
|------------|---------------|----------------|--------------------|
| baseline   | 81            | 20             | 100.0 %            |
| burst      | 100           | 20             | 100.0 %            |
| nxdomain   | 51            | 51             | 100.0 %            |
| longdomain | 41            | 41             | 100.0 %            |

Response codes (NOERROR / NXDOMAIN / NODATA / SERVFAIL / REFUSED) are recovered
on every query in all four datasets via the `query[…] → reply / cached /
config / Pi-hole hostname` correlation in `src/log_parser.py`.

## Heuristic trigger matrix

Each profile is designed to exercise one heuristic; some profiles also
legitimately trigger an adjacent one (e.g. `longdomain` uses NXDOMAIN-shaped
fake names, so `nxdomain_excess` fires too).

| dataset    | burst_window | nxdomain_excess | long_domain | rare_tld |
|------------|:------------:|:---------------:|:-----------:|:--------:|
| baseline   |     —        |        —        |      —      |    —     |
| burst      |   **1**      |        —        |      —      |    —     |
| nxdomain   |     —        |     **1**       |   **20**    |    —     |
| longdomain |     —        |       1         |   **20**    |    —     |

Bold cells are the heuristic each dataset is designed to trigger.

### Burst evidence (sample)

```
type:        burst_window
time_bucket: 2026-04-29T12:27:20
query_count: 100
threshold:   40 (baseline p95 × 2.0)
```

### NXDOMAIN evidence (sample)

```
type:             nxdomain_excess
nxdomain_count:   50 / 51 queries
nxdomain_ratio:   0.980
baseline_ratio:   0.000
```

### Long-domain evidence (sample)

```
type:    long_domain
domain:  bjabjqfiofex.nonexistent-bjabjqfiofex.net (length 41)
threshold: 17 chars (baseline-driven: max(baseline-max, mean + 2σ))
```

## Outputs reference

Every dataset folder under `outputs/<name>/` contains:

| file                                | purpose                                     |
|-------------------------------------|---------------------------------------------|
| `summary.json`                      | All metrics in one place                    |
| `findings.json`                     | List of fired heuristics with evidence      |
| `parse_stats.json`                  | Parser counters and success rate            |
| `volume_over_time.csv`              | 10-second query buckets                     |
| `top_domains.csv`                   | Top 50 most-queried domains                 |
| `tld_distribution.csv`              | TLD frequency                               |
| `domain_length_distribution.csv`    | Length histogram                            |
| `label_count_distribution.csv`      | Subdomain depth histogram                   |
| `query_type_distribution.csv`       | A / AAAA / PTR / MX / …                     |
| `response_code_distribution.csv`    | NOERROR / NXDOMAIN / NODATA / …             |

## Notes

- All output values are **behavioural / analytical** observations. The
  project does not make threat-detection or security claims.
- Heuristic thresholds are derived from the `baseline` summary so each
  rule has an explicit, reproducible reason for firing.
