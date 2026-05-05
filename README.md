# DNS Behaviour Monitor

> **Version 1.0.0** · MIT licence · Python 3.10+ · Windows + Docker Desktop
>
> Reproducible behavioural-analysis pipeline for DNS traffic. Pi-hole runs in
> Docker (host DNS port **5354**, admin **8081**), traffic is generated
> programmatically, logs are normalised, baseline metrics and four
> transparent heuristics are computed, and a Streamlit dashboard renders the
> result. **Wording is behavioural / analytical only — no threat or security
> claims.**

---

## TL;DR — reproduce the project from scratch

```powershell
git clone <this-repo> dns-behaviour-monitor
cd dns-behaviour-monitor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Option A — full demo (boots Pi-hole, generates 4 datasets, runs analysis,
# opens the dashboard). Requires Docker Desktop running.
.\scripts\demo.ps1

# Option B — analyse the four committed datasets without Pi-hole.
python src\run_analysis.py data\baseline.log   --name baseline   --outputs outputs
python src\run_analysis.py data\burst.log      --name burst      --outputs outputs --baseline-summary outputs\baseline\summary.json
python src\run_analysis.py data\nxdomain.log   --name nxdomain   --outputs outputs --baseline-summary outputs\baseline\summary.json
python src\run_analysis.py data\longdomain.log --name longdomain --outputs outputs --baseline-summary outputs\baseline\summary.json
.\scripts\run_app.ps1
```

## Reproducibility checklist (for a marker)

| step | command | what to verify |
|------|---------|----------------|
| 1 | `python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt` | All deps install, no errors |
| 2 | `python -m pytest tests\test_parser.py -v` | **6 tests pass** — schema, timestamps, ≥ 95 % parse rate, response-code correlation |
| 3 | Run Option A or Option B above | `outputs\<dataset>\summary.json`, `findings.json`, `parse_stats.json` written for all four datasets |
| 4 | `Get-Content outputs\evaluation_summary.md` | Reference run table matches re-generated run |
| 5 | `.\scripts\run_app.ps1` | Streamlit dashboard at <http://localhost:8501>, rule-firing matrix matches `findings.json` |

A canonical reference run is committed under `outputs/` so steps 3 + 4 can be
checked without running the pipeline.

## Normalised schema and metrics

The parser emits one row per query with the schema:

| field | example |
|-------|---------|
| `timestamp` | `2026-04-29T12:26:43` |
| `domain` | `github.com` |
| `query_type` | `A`, `AAAA`, `PTR`, … |
| `client` | `172.19.0.1` |
| `response_code` | `NOERROR`, `NXDOMAIN`, `NODATA`, `SERVFAIL`, `REFUSED` |
| `source` | `pihole` |

Response codes are recovered by correlating each `query[…]` line with the
next `reply` / `cached` / `config` / `Pi-hole hostname` line for the same
domain.

Per-dataset metrics written to `outputs/<dataset>/`:

- `summary.json` — total queries, unique domains, time range, all distributions
- `volume_over_time.csv` — 10-second query buckets
- `top_domains.csv` — top 50 most-queried domains
- `tld_distribution.csv`, `domain_length_distribution.csv`,
  `label_count_distribution.csv`, `query_type_distribution.csv`,
  `response_code_distribution.csv`
- `parse_stats.json` — parser counters and success rate

## Heuristics

All four are transparent and baseline-driven. Each finding records `type`,
`evidence`, and `why_flagged`.

| type | rule |
|------|------|
| `long_domain`     | length > max(baseline-max-length, baseline mean + 2σ); hard cap 60 chars |
| `burst_window`    | 10-second bucket count > baseline p95 × 2 |
| `nxdomain_excess` | NXDOMAIN ratio ≥ 20 % AND ≥ 20 pp above baseline ratio |
| `rare_tld`        | TLD appears in < 1 % of queries |

## Reference run results

| dataset    | queries | unique | parse rate | findings (rule × count)              |
|------------|--------:|-------:|-----------:|--------------------------------------|
| baseline   |     81  |    20  |   100.0 %  | none (clean)                         |
| burst      |    100  |    20  |   100.0 %  | `burst_window` × 1                   |
| nxdomain   |     51  |    51  |   100.0 %  | `nxdomain_excess` × 1, `long_domain` × 20 |
| longdomain |     41  |    41  |   100.0 %  | `nxdomain_excess` × 1, `long_domain` × 20 |

Detail: [`outputs/evaluation_summary.md`](outputs/evaluation_summary.md).

## Project layout

```
dns-behaviour-monitor/
├── README.md, CHANGELOG.md, LICENSE, requirements.txt, .gitignore
├── app/
│   └── streamlit_app.py        # 13-module dashboard
├── src/
│   ├── log_parser.py           # dnsmasq → normalised DataFrame
│   ├── feature_extractor.py    # adds time_bucket, domain_length, tld, …
│   ├── metrics_engine.py       # builds summary.json + CSVs
│   ├── heuristic_engine.py     # 4 baseline-driven rules
│   └── run_analysis.py         # entry point (parse → features → metrics → rules)
├── scripts/
│   ├── pihole_up.ps1, pihole_down.ps1
│   ├── flush_pihole_log.ps1
│   ├── generate_dns.py         # 4 traffic profiles (baseline/burst/nxdomain/longdomain)
│   ├── generate_traffic.ps1
│   ├── export_dataset.ps1      # validates non-pi.hole traffic
│   ├── run_app.ps1, run_evaluation.ps1, demo.ps1
├── data/                       # committed sample logs (one per profile)
├── outputs/                    # canonical reference run + evaluation_summary.md
├── pihole/
│   └── docker-compose.yml      # the only tracked Pi-hole file; runtime state ignored
├── tests/
│   └── test_parser.py          # 6 tests
└── fyp files/                  # report template, marking criteria, poster, mid-point review
```

## Prerequisites

- **Windows** with PowerShell
- **Docker Desktop** running (only required for the live Pi-hole pipeline; not
  needed to re-analyse the committed datasets)
- **Python 3.10+**

## One-command demo

From the project folder:

```powershell
.\scripts\demo.ps1
```

This will:

1. **Start Pi-hole** in Docker (first time may take 1–2 minutes to pull the image).
2. **Wait** until Pi-hole answers DNS on port 5354.
3. **Generate** four datasets (`baseline`, `burst`, `nxdomain`, `longdomain`)
   by sending DNS queries to Pi-hole and **exporting** `pihole.log` into
   `data\<name>.log`.
4. **Run analysis** and write results to `outputs\<name>\`.
5. **Open the Streamlit dashboard** at <http://localhost:8501>.

No pre-existing Pi-hole or logs required — the script creates everything.

## Manual steps (if you prefer)

1. **Start Pi-hole** (DNS 5354, admin 8081, logs in `pihole\logs`):
   ```powershell
   .\scripts\pihole_up.ps1
   ```
   Wait until the container is up (≈15–20 s, longer on first pull).

2. **Generate traffic and export datasets**:
   ```powershell
   .\scripts\generate_traffic.ps1 -Profile baseline
   .\scripts\export_dataset.ps1 -Name baseline
   ```
   Repeat with `burst`, `nxdomain`, `longdomain`. `export_dataset.ps1`
   validates that the export contains real query lines and at least one
   non-`pi.hole` domain; if not, it exits with an error.

3. **Run analysis** (writes to `outputs\<name>\`):
   ```powershell
   python src\run_analysis.py data\baseline.log --name baseline --outputs outputs
   ```

4. **Start dashboard**:
   ```powershell
   .\scripts\run_app.ps1
   ```

## Evaluation

```powershell
.\scripts\run_evaluation.ps1
```

Generates all four datasets, runs analysis, checks that
`burst` / `longdomain` / `nxdomain` trigger their expected heuristics, and
writes `outputs\evaluation_summary.md` and `outputs\evaluation_tables\*.csv`.

## Testing

```powershell
python -m pytest tests\test_parser.py -v
```

Parser success-rate target: ≥ 95 % on query lines. Required columns,
timestamp parsing, and response-code correlation
(NOERROR / NXDOMAIN / cached) are validated.

## Port policy

- **Host DNS port: 5354** (Windows port 53 is not used; safe and reproducible).
- All scripted traffic targets `127.0.0.1:5354` via the Python `dnspython`
  script.

## What is **not** in this repo (and why)

| item | reason |
|------|--------|
| `.venv\` | Always recreate locally with `python -m venv .venv`. |
| `__pycache__\`, `.pytest_cache\` | Auto-generated. |
| `pihole\etc-pihole\`, `pihole\logs\` | Pi-hole runtime state (gravity DB, FTL DB, admin password file `cli_pw`, rotated logs). Recreated on first `pihole_up.ps1`. |
| Generated `data\*.log` other than the four committed profiles | Generated by `generate_traffic.ps1` + `export_dataset.ps1`. |
| `outputs\evaluation_tables\` | Re-built every evaluation run. |

## Licence

MIT — see [`LICENSE`](LICENSE).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.
