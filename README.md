# DNS Behaviour Monitor

Reproducible pipeline: Pi-hole in Docker (DNS on host port **5354**, admin **8081**), scripted DNS traffic, log export, normalised parsing, baseline metrics and heuristics, and a Streamlit dashboard. Wording is behavioural/analytical only (no threat or security claims).

## Prerequisites (do this once)

- **Windows** with PowerShell
- **Docker Desktop** installed and **running** (so Pi-hole can start)
- **Python 3.10+** with dependencies installed:
  ```powershell
  cd d:\dns-behaviour-monitor
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

You do **not** need Pi-hole or any logs set up beforehand. The demo script starts Pi-hole, generates the traffic, creates the log files, then opens the app.

## One-command demo (creates everything)

From the project folder:

```powershell
.\scripts\demo.ps1
```

This will:

1. **Start Pi-hole** in Docker (first time may take 1–2 minutes to pull the image).
2. **Wait** until Pi-hole is ready to answer DNS on port 5354.
3. **Generate** four datasets (baseline, burst, nxdomain, longdomain) by sending DNS queries to Pi-hole and **exporting** `pihole.log` into `data/*.log`.
4. **Run analysis** and write results to `outputs/`.
5. **Open the Streamlit dashboard** at http://localhost:8501.

So you get logs and the full pipeline from a single run; no manual Pi-hole setup or pre-existing logs required.

## Manual steps (if you prefer)

1. **Start Pi-hole** (DNS 5354, admin 8081, logs in `pihole/logs`):
   ```powershell
   .\scripts\pihole_up.ps1
   ```
   Wait until the container is up (e.g. 15–20 s, or longer on first pull).

2. **Generate traffic and export datasets**:
   ```powershell
   .\scripts\generate_traffic.ps1 -Profile baseline
   .\scripts\export_dataset.ps1 -Name baseline
   ```
   Repeat with `burst`, `nxdomain`, `longdomain` if you want all four.
   
   `export_dataset.ps1` now validates that the exported file contains real query lines and at least one non-`pi.hole` domain. If it only sees health checks, it exits with an error.

3. **Run analysis** (writes to `outputs/<name>/`):
   ```powershell
   python src/run_analysis.py data/baseline.log --name baseline --outputs outputs
   ```

4. **Start dashboard**:
   ```powershell
   .\scripts\run_app.ps1
   ```

## Port policy

- **Host DNS port: 5354** (Windows port 53 is not used; safe and reproducible).
- All scripted traffic targets `127.0.0.1:5354` via the Python dnspython script.

## Layout

| Path | Purpose |
|------|--------|
| `pihole/` | Docker Compose, Pi-hole config and logs |
| `scripts/` | `pihole_up.ps1`, `pihole_down.ps1`, `generate_traffic.ps1`, `generate_dns.py`, `export_dataset.ps1`, `flush_pihole_log.ps1`, `run_app.ps1`, `run_evaluation.ps1`, `demo.ps1` |
| `src/` | `log_parser`, `feature_extractor`, `metrics_engine`, `heuristic_engine`, `run_analysis` |
| `app/streamlit_app.py` | Dashboard: dataset selector, KPIs, charts, highlighted observations |
| `data/` | Exported datasets (`*.log`) |
| `outputs/<name>/` | Summary JSON, CSVs, `findings.json` |
| `tests/` | Parser tests (columns, timestamps, success rate) |

## Evaluation

```powershell
.\scripts\run_evaluation.ps1
```

Generates all four datasets, runs analysis, checks that burst/longdomain/nxdomain trigger the expected heuristics, and writes `outputs/evaluation_summary.md` and `outputs/evaluation_tables/*.csv`.

## Testing

```powershell
python -m pytest tests/test_parser.py -v
# or
python -m tests.test_parser
```

Parser success rate target: ≥ 95% on query lines; required columns and timestamp parsing are validated.
