"""
DNS Behaviour Monitor — Futuristic modular Streamlit dashboard.
Analytical view of DNS query behaviour. No threat or security claims.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"

# ── Palette ───────────────────────────────────────────────────────────────────
C_BG      = "#080c14"
C_SURFACE = "#0d1525"
C_BORDER  = "#1a2a44"
C_ACCENT  = "#00e5ff"
C_ACCENT2 = "#7b2fff"
C_GREEN   = "#00ff9f"
C_YELLOW  = "#ffe600"
C_RED     = "#ff4060"
C_TEXT    = "#c8d8f0"
C_MUTED   = "#5a7090"

# Base layout dict — NO xaxis/yaxis here to avoid duplicate-kwarg errors
_LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,21,37,0.8)",
    font=dict(color=C_TEXT, family="monospace"),
    colorway=[C_ACCENT, C_ACCENT2, C_GREEN, C_YELLOW, C_RED,
              "#ff6ec7", "#ff9a00", "#00cfff", "#a8ff3e"],
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=C_BORDER),
    margin=dict(l=10, r=10, t=40, b=10),
    height=320,
)
_AXIS_STYLE = dict(gridcolor=C_BORDER, linecolor=C_BORDER, zerolinecolor=C_BORDER)


def _layout(extra: dict | None = None, title: str = "", height: int = 320) -> dict:
    """Merge base layout with optional overrides — safe from duplicate-kwarg errors."""
    d = dict(_LAYOUT_BASE)
    d["height"] = height
    if title:
        d["title"] = dict(text=title, font=dict(family="Share Tech Mono",
                                                 size=13, color=C_ACCENT), x=0)
    d["xaxis"] = dict(_AXIS_STYLE)
    d["yaxis"] = dict(_AXIS_STYLE)
    if extra:
        d.update(extra)
    return d


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Exo+2:wght@300;400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    background: {C_BG} !important;
    color: {C_TEXT};
    font-family: 'Exo 2', sans-serif;
}}
[data-testid="stSidebar"] {{
    background: {C_SURFACE} !important;
    border-right: 1px solid {C_BORDER};
}}
[data-testid="stSidebar"] * {{ color: {C_TEXT} !important; }}
h1,h2,h3,h4 {{ font-family: 'Share Tech Mono', monospace !important; letter-spacing: 2px; }}

/* top header bar */
.dns-header {{
    background: linear-gradient(135deg, {C_SURFACE} 0%, #0a1830 100%);
    border: 1px solid {C_BORDER};
    border-left: 4px solid {C_ACCENT};
    border-radius: 6px;
    padding: 18px 28px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 18px;
}}
.dns-header-title {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.7rem;
    letter-spacing: 4px;
    background: linear-gradient(90deg, {C_ACCENT}, {C_ACCENT2});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-transform: uppercase;
}}
.dns-header-sub {{
    font-size: 0.75rem;
    color: {C_MUTED};
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: 2px;
}}
.dot-pulse {{
    width: 10px; height: 10px; border-radius: 50%;
    background: {C_GREEN};
    box-shadow: 0 0 8px {C_GREEN};
    animation: blink 1.8s infinite;
    flex-shrink: 0;
}}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}

/* module card */
.module-card {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 20px 24px;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}}
.module-card::before {{
    content: '';
    position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, {C_ACCENT}, {C_ACCENT2});
}}
.module-label {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 3px;
    color: {C_MUTED};
    text-transform: uppercase;
    margin-bottom: 4px;
}}
.module-title {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.0rem;
    letter-spacing: 2px;
    color: {C_ACCENT};
    text-transform: uppercase;
    margin-bottom: 16px;
    border-bottom: 1px solid {C_BORDER};
    padding-bottom: 10px;
}}

/* KPI grid */
.kpi-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px; }}
.kpi-card {{
    flex: 1; min-width: 140px;
    background: linear-gradient(135deg, rgba(0,229,255,.04), rgba(123,47,255,.04));
    border: 1px solid {C_BORDER};
    border-top: 2px solid {C_ACCENT};
    border-radius: 6px;
    padding: 16px 18px;
    text-align: center;
}}
.kpi-label {{
    font-size: 0.65rem; letter-spacing: 2px;
    color: {C_MUTED}; text-transform: uppercase; margin-bottom: 8px;
}}
.kpi-value {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 2.0rem; color: {C_ACCENT};
    text-shadow: 0 0 12px {C_ACCENT}66; line-height: 1;
}}
.kpi-sub {{ font-size: 0.65rem; color: {C_MUTED}; margin-top: 6px; }}

/* rules panel */
.rules-grid {{ display: flex; gap: 14px; flex-wrap: wrap; }}
.rule-card {{
    flex: 1; min-width: 180px;
    border-radius: 6px; padding: 14px 16px;
    border: 1px solid; position: relative;
}}
.rule-fired  {{ border-color: {C_RED};    background: rgba(255,64,96,.08); }}
.rule-clear  {{ border-color: {C_BORDER}; background: rgba(13,21,37,.6); }}
.rule-name {{
    font-family: 'Share Tech Mono', monospace;
    font-size: .72rem; letter-spacing: 2px; text-transform: uppercase;
    margin-bottom: 6px;
}}
.rule-status {{ font-size: .8rem; margin-bottom: 4px; }}
.rule-count  {{ font-family: 'Share Tech Mono', monospace; font-size: 1.5rem; }}
.rule-desc   {{ font-size: .7rem; color: {C_MUTED}; margin-top: 6px; line-height: 1.5; }}

/* alert cards */
.alert-card {{
    border-radius: 6px; padding: 14px 18px; margin-bottom: 12px;
    border-left: 4px solid; background: rgba(13,21,37,0.9);
}}
.alert-high {{ border-color: {C_RED};    background: rgba(255,64,96,.06); }}
.alert-med  {{ border-color: {C_YELLOW}; background: rgba(255,230,0,.05); }}
.alert-low  {{ border-color: {C_ACCENT}; background: rgba(0,229,255,.04); }}
.alert-type {{ font-family:'Share Tech Mono',monospace; font-size:.75rem;
               letter-spacing:2px; text-transform:uppercase; }}
.alert-why  {{ font-size:.85rem; color:{C_TEXT}; margin-top:4px; }}
.alert-evid {{ font-size:.75rem; color:{C_MUTED}; margin-top:6px;
               font-family:'Share Tech Mono',monospace; }}

/* domain feed */
.domain-row {{ display:flex; align-items:center; gap:10px; padding:5px 0;
               border-bottom:1px solid {C_BORDER}; }}
.domain-rank {{ font-family:'Share Tech Mono',monospace; color:{C_MUTED};
                font-size:.75rem; width:24px; }}
.domain-name {{ flex:1; font-family:'Share Tech Mono',monospace; font-size:.85rem; color:{C_TEXT}; }}
.domain-bar  {{ height:6px; border-radius:3px;
                background:linear-gradient(90deg,{C_ACCENT},{C_ACCENT2}); min-width:4px; }}
.domain-cnt  {{ font-size:.8rem; color:{C_ACCENT}; font-family:'Share Tech Mono',monospace;
                min-width:30px; text-align:right; }}

.no-data {{ color:{C_MUTED}; font-size:.85rem; letter-spacing:1px;
            font-family:'Share Tech Mono',monospace; }}

/* streamlit overrides */
[data-testid="stMetricLabel"] {{ color:{C_MUTED}!important; font-size:.65rem!important;
                                  letter-spacing:2px!important; text-transform:uppercase!important; }}
[data-testid="stMetricValue"] {{ font-family:'Share Tech Mono',monospace!important;
                                  color:{C_ACCENT}!important; }}
#MainMenu, footer {{ visibility:hidden; }}

/* keep the top toolbar slot but hide only the deploy/share/help buttons inside it,
   so the sidebar collapse/expand control next to it stays clickable. */
[data-testid="stToolbarActions"],
[data-testid="stDeployButton"],
[data-testid="stStatusWidget"] {{ visibility:hidden !important; }}

/* always keep the sidebar visible and the collapse control reachable. */
[data-testid="stSidebar"] {{ display:flex !important; min-width:280px !important; }}
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"] {{
    visibility:visible !important;
    display:flex !important;
    opacity:1 !important;
    z-index:9999 !important;
}}
</style>
"""

# ── Rule catalogue ─────────────────────────────────────────────────────────────
RULES = [
    {
        "type":     "burst_window",
        "label":    "Burst Window",
        "desc":     "Query count in a 10-second bucket exceeds baseline p95 × 2.0",
        "severity": "high",
    },
    {
        "type":     "nxdomain_excess",
        "label":    "NXDOMAIN Excess",
        "desc":     "NXDOMAIN ratio ≥ 20 % AND ≥ 20 pp above baseline NXDOMAIN ratio",
        "severity": "high",
    },
    {
        "type":     "long_domain",
        "label":    "Long Domain",
        "desc":     "Domain length > max(baseline max, mean + 2 σ); hard cap 60 chars",
        "severity": "med",
    },
    {
        "type":     "rare_tld",
        "label":    "Rare TLD",
        "desc":     "TLD appears in < 1 % of total queries",
        "severity": "low",
    },
]

SEVERITY_COLOR = {"high": C_RED, "med": C_YELLOW, "low": C_ACCENT}
SEVERITY_CLASS = {"high": "alert-high", "med": "alert-med", "low": "alert-low"}
SEVERITY_ICON  = {"high": "🔴", "med": "🟡", "low": "🔵"}


# ── Data helpers ───────────────────────────────────────────────────────────────

def list_datasets() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted(f.stem for f in DATA_DIR.glob("*.log"))


def load_outputs(name: str) -> tuple[dict, list]:
    out = OUTPUTS_DIR / name
    metrics, findings = {}, []
    sp, fp = out / "summary.json", out / "findings.json"
    if sp.exists():
        metrics = json.loads(sp.read_text(encoding="utf-8"))
    if fp.exists():
        findings = json.loads(fp.read_text(encoding="utf-8"))
    return metrics, findings


def load_parse_stats(name: str) -> dict:
    p = OUTPUTS_DIR / name / "parse_stats.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def run_analysis_for(name: str, force: bool = False) -> tuple[dict, list]:
    import sys
    sys.path.insert(0, str(ROOT))
    log_path = DATA_DIR / f"{name}.log"
    if not log_path.exists():
        return {}, []
    if force:
        from src.run_analysis import run_analysis
        bl = OUTPUTS_DIR / "baseline" / "summary.json"
        run_analysis(log_path, name, outputs_root=OUTPUTS_DIR,
                     baseline_summary_path=bl if bl.exists() else None)
    return load_outputs(name)


# ── Chart builders ─────────────────────────────────────────────────────────────

def chart_volume(vol: list) -> go.Figure | None:
    if not vol:
        return None
    df = pd.DataFrame(vol)
    if "bucket" not in df.columns:
        return None
    df["bucket"] = pd.to_datetime(df["bucket"])
    fig = go.Figure(go.Scatter(
        x=df["bucket"], y=df["count"],
        mode="lines+markers", fill="tozeroy",
        line=dict(color=C_ACCENT, width=2),
        fillcolor="rgba(0,229,255,0.08)",
        marker=dict(color=C_ACCENT, size=5, line=dict(color=C_ACCENT2, width=1)),
        name="queries",
    ))
    fig.update_layout(**_layout(title="QUERY VOLUME · OVER TIME"))
    return fig


def chart_tld(tld_dist: list) -> go.Figure | None:
    if not tld_dist:
        return None
    df = pd.DataFrame(tld_dist).head(12)
    if "tld" not in df.columns:
        return None
    colors = [C_ACCENT, C_ACCENT2, C_GREEN, C_YELLOW, C_RED,
              "#ff6ec7", "#ff9a00", "#00cfff", "#a8ff3e",
              "#ff4d94", "#00b4d8", "#7b2fff"]
    fig = go.Figure(go.Pie(
        labels=df["tld"], values=df["count"],
        hole=0.55,
        marker=dict(colors=colors[:len(df)], line=dict(color=C_BG, width=2)),
        textfont=dict(family="Share Tech Mono", size=11, color=C_TEXT),
        hovertemplate="<b>%{label}</b><br>%{value} queries (%{percent})<extra></extra>",
    ))
    fig.update_layout(**_layout(title="TLD DISTRIBUTION",
                                extra=dict(showlegend=True,
                                           legend=dict(bgcolor="rgba(0,0,0,0)",
                                                       bordercolor=C_BORDER,
                                                       font=dict(family="Share Tech Mono",
                                                                 size=10)))))
    return fig


def chart_length(length_dist: list) -> go.Figure | None:
    if not length_dist:
        return None
    df = pd.DataFrame(length_dist)
    if "domain_length" not in df.columns:
        return None
    fig = go.Figure(go.Bar(
        x=df["domain_length"], y=df["count"],
        marker=dict(
            color=df["count"],
            colorscale=[[0, C_ACCENT2], [0.5, C_ACCENT], [1, C_GREEN]],
            line=dict(color=C_BG, width=0.5),
        ),
        hovertemplate="length %{x}: %{y} queries<extra></extra>",
    ))
    fig.update_layout(**_layout(title="DOMAIN LENGTH DISTRIBUTION"))
    return fig


def chart_top_domains(top: list) -> go.Figure | None:
    if not top:
        return None
    df = pd.DataFrame(top).head(15).sort_values("count")
    fig = go.Figure(go.Bar(
        x=df["count"], y=df["domain"],
        orientation="h",
        marker=dict(
            color=df["count"],
            colorscale=[[0, C_ACCENT2], [1, C_ACCENT]],
            line=dict(color=C_BG, width=0.3),
        ),
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    yaxis_override = dict(_AXIS_STYLE,
                          tickfont=dict(family="Share Tech Mono", size=10))
    fig.update_layout(**_layout(title="TOP QUERIED DOMAINS", height=380,
                                extra=dict(yaxis=yaxis_override)))
    return fig


def chart_label_count(label_dist: list) -> go.Figure | None:
    if not label_dist:
        return None
    df = pd.DataFrame(label_dist)
    if "label_count" not in df.columns:
        return None
    fig = go.Figure(go.Bar(
        x=df["label_count"], y=df["count"],
        marker=dict(
            color=df["count"],
            colorscale=[[0, C_ACCENT2], [0.5, C_GREEN], [1, C_ACCENT]],
            line=dict(color=C_BG, width=0.5),
        ),
        hovertemplate="depth %{x} labels: %{y} queries<extra></extra>",
    ))
    fig.update_layout(**_layout(title="SUBDOMAIN DEPTH · LABEL COUNT DISTRIBUTION"))
    return fig


def chart_query_types(qt_dist: list) -> go.Figure | None:
    if not qt_dist:
        return None
    df = pd.DataFrame(qt_dist)
    if "query_type" not in df.columns:
        return None
    colors = [C_ACCENT, C_ACCENT2, C_GREEN, C_YELLOW, C_RED,
              "#ff6ec7", "#ff9a00", "#00cfff"]
    fig = go.Figure(go.Bar(
        x=df["query_type"], y=df["count"],
        marker=dict(
            color=colors[:len(df)],
            line=dict(color=C_BG, width=0.5),
        ),
        hovertemplate="%{x}: %{y} queries<extra></extra>",
    ))
    fig.update_layout(**_layout(title="QUERY TYPE DISTRIBUTION  (A / AAAA / MX …)"))
    return fig


def chart_response_codes(rc_dist: list) -> go.Figure | None:
    if not rc_dist:
        return None
    df = pd.DataFrame(rc_dist)
    if "response_code" not in df.columns:
        return None
    color_map = {
        "NOERROR":  C_GREEN,
        "NXDOMAIN": C_RED,
        "NODATA":   C_YELLOW,
        "SERVFAIL": "#ff6ec7",
        "REFUSED":  "#ff9a00",
        "UNKNOWN":  C_MUTED,
    }
    bar_colors = [color_map.get(rc, C_ACCENT) for rc in df["response_code"]]
    fig = go.Figure(go.Bar(
        x=df["response_code"], y=df["count"],
        marker=dict(color=bar_colors, line=dict(color=C_BG, width=0.5)),
        hovertemplate="%{x}: %{y} queries<extra></extra>",
    ))
    fig.update_layout(**_layout(title="RESPONSE CODE DISTRIBUTION  (RFC 1035)"))
    return fig


def chart_compare(datasets: list[str]) -> go.Figure | None:
    rows = []
    for name in datasets:
        m, _ = load_outputs(name)
        if m:
            rows.append({"dataset": name,
                         "total_queries": m.get("total_queries", 0),
                         "unique_domains": m.get("unique_domains", 0)})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    fig = go.Figure([
        go.Bar(name="Total Queries",  x=df["dataset"], y=df["total_queries"],
               marker_color=C_ACCENT),
        go.Bar(name="Unique Domains", x=df["dataset"], y=df["unique_domains"],
               marker_color=C_ACCENT2),
    ])
    fig.update_layout(**_layout(title="DATASET COMPARISON",
                                extra=dict(barmode="group")))
    return fig


def chart_rules_heatmap(datasets: list[str]) -> go.Figure | None:
    """Matrix: datasets × rule types — count of firings."""
    rule_types = [r["type"] for r in RULES]
    z, text = [], []
    for name in datasets:
        _, findings = load_outputs(name)
        row, trow = [], []
        for rt in rule_types:
            cnt = sum(1 for f in findings if f.get("type") == rt)
            row.append(cnt)
            trow.append(str(cnt) if cnt else "·")
        z.append(row)
        text.append(trow)
    if not datasets:
        return None
    colorscale = [[0, C_SURFACE], [0.01, "rgba(123,47,255,0.3)"],
                  [0.5, C_ACCENT2], [1, C_RED]]
    fig = go.Figure(go.Heatmap(
        z=z, x=[r["label"] for r in RULES], y=datasets,
        text=text, texttemplate="%{text}",
        colorscale=colorscale,
        showscale=False,
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z} firing(s)<extra></extra>",
        textfont=dict(family="Share Tech Mono", size=13, color=C_TEXT),
    ))
    fig.update_layout(**_layout(title="RULE FIRING MATRIX · ALL DATASETS",
                                height=220 + 40 * len(datasets),
                                extra=dict(
                                    xaxis=dict(_AXIS_STYLE,
                                               tickfont=dict(family="Share Tech Mono",
                                                             size=11)),
                                    yaxis=dict(_AXIS_STYLE,
                                               tickfont=dict(family="Share Tech Mono",
                                                             size=11)),
                                )))
    return fig


# ── UI helpers ────────────────────────────────────────────────────────────────

def card_open(label: str, title: str) -> None:
    st.markdown(f"""
    <div class="module-card">
      <div class="module-label">{label}</div>
      <div class="module-title">{title}</div>
    """, unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _finding_severity(f: dict) -> str:
    rule = next((r for r in RULES if r["type"] == f.get("type")), None)
    return rule["severity"] if rule else "low"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="DNS Behaviour Monitor",
                       layout="wide", initial_sidebar_state="expanded")
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="font-family:'Share Tech Mono',monospace;font-size:1.1rem;
                    letter-spacing:3px;color:{C_ACCENT};text-transform:uppercase;
                    margin-bottom:4px;">DNS Monitor</div>
        <div style="font-size:.65rem;color:{C_MUTED};letter-spacing:2px;
                    text-transform:uppercase;margin-bottom:24px;">
            Behaviour Analysis System
        </div>
        """, unsafe_allow_html=True)

        datasets = list_datasets()
        if not datasets:
            st.error("No datasets found in data/")
            st.stop()

        st.markdown(f'<div style="font-size:.65rem;color:{C_MUTED};letter-spacing:2px;'
                    'text-transform:uppercase;margin-bottom:8px;">Active Dataset</div>',
                    unsafe_allow_html=True)
        selected = st.selectbox("", datasets, key="dataset",
                                label_visibility="collapsed")

        st.markdown(f'<div style="margin-top:20px;font-size:.65rem;color:{C_MUTED};'
                    'letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">'
                    'Compare Datasets</div>', unsafe_allow_html=True)
        compare_sel = st.multiselect("", datasets,
                                     default=datasets[:min(3, len(datasets))],
                                     key="compare", label_visibility="collapsed")

        st.markdown(f"<hr style='border-color:{C_BORDER};margin:20px 0;'>",
                    unsafe_allow_html=True)
        run_clicked = st.button("⚡  Re-run Analysis", use_container_width=True)

        # Sidebar rule legend
        st.markdown(f"""
        <div style="margin-top:24px;font-size:.65rem;color:{C_MUTED};
                    letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">
            Heuristic Rules
        </div>
        """, unsafe_allow_html=True)
        for r in RULES:
            col = SEVERITY_COLOR[r["severity"]]
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
              <div style="width:8px;height:8px;border-radius:50%;
                          background:{col};box-shadow:0 0 6px {col};flex-shrink:0;"></div>
              <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;
                          color:{C_TEXT};letter-spacing:1px;">{r['label']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="margin-top:20px;font-size:.65rem;color:{C_MUTED};
                    letter-spacing:1px;line-height:1.6;">
            Analytical view only.<br>No threat or security claims.
        </div>
        """, unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    with st.spinner(""):
        metrics, findings = run_analysis_for(selected, force=run_clicked)

    # ── Header ────────────────────────────────────────────────────────────────
    alert_n    = len(findings)
    header_dot = C_RED if alert_n else C_GREEN
    st.markdown(f"""
    <div class="dns-header">
        <div class="dot-pulse" style="background:{header_dot};box-shadow:0 0 8px {header_dot};"></div>
        <div>
            <div class="dns-header-title">DNS Behaviour Monitor</div>
            <div class="dns-header-sub">
                Dataset &nbsp;/&nbsp;
                <span style="color:{C_ACCENT};font-family:'Share Tech Mono',monospace;">
                    {selected.upper()}
                </span>
                &nbsp;·&nbsp;
                {'<span style="color:' + C_RED + ';">' + str(alert_n) + ' observation(s) flagged</span>'
                  if alert_n else
                  '<span style="color:' + C_GREEN + ';">All clear</span>'}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not metrics:
        st.markdown(f"""
        <div class="module-card">
            <div class="module-title">NO DATA</div>
            <div class="no-data">
                No metrics found for <b>{selected}</b>.<br>
                Click ⚡ Re-run Analysis in the sidebar.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    total  = metrics.get("total_queries", 0)
    unique = metrics.get("unique_domains", 0)
    tr     = metrics.get("time_range") or {}
    tr_min = (tr.get("min") or "—")[:16]
    tr_max = (tr.get("max") or "—")[:16]
    repeat = round((total - unique) / total * 100, 1) if total else 0
    parse_stats   = load_parse_stats(selected)
    parse_total   = parse_stats.get("total_lines", 0)
    parse_parsed  = parse_stats.get("parsed_lines", 0)
    parse_attempts = parse_stats.get("query_attempts", 0)
    parse_rate    = parse_stats.get("parse_success_rate", None)

    # ── MODULE 01 · PULSE — KPIs ─────────────────────────────────────────────
    obs_color = "#ff4060" if alert_n else "#00ff9f"
    obs_sub   = "rules fired" if alert_n else "none flagged"

    parse_card_html = ""
    if parse_rate is not None:
        parse_color = "#00ff9f" if parse_rate >= 95 else "#ffe600"
        parse_card_html = (
            f'<div class="kpi-card">'
            f'<div class="kpi-label">Parse Success Rate</div>'
            f'<div class="kpi-value" style="color:{parse_color};">'
            f'{parse_rate}<span style="font-size:1rem;">%</span></div>'
            f'<div class="kpi-sub">{parse_parsed:,} / {parse_attempts:,} query lines</div>'
            f'</div>'
        )

    pulse_html = (
        '<div class="module-card">'
        '<div class="module-label">Module 01</div>'
        '<div class="module-title">PULSE · KEY METRICS</div>'
        '<div class="kpi-grid">'
        f'<div class="kpi-card"><div class="kpi-label">Total Queries</div>'
        f'<div class="kpi-value">{total:,}</div></div>'
        f'<div class="kpi-card"><div class="kpi-label">Unique Domains</div>'
        f'<div class="kpi-value">{unique:,}</div></div>'
        f'<div class="kpi-card"><div class="kpi-label">Repeat Rate</div>'
        f'<div class="kpi-value">{repeat}<span style="font-size:1rem;">%</span></div>'
        f'<div class="kpi-sub">of queries are repeats</div></div>'
        f'<div class="kpi-card"><div class="kpi-label">Observations</div>'
        f'<div class="kpi-value" style="color:{obs_color};">{alert_n}</div>'
        f'<div class="kpi-sub">{obs_sub}</div></div>'
        f'<div class="kpi-card" style="min-width:220px;">'
        f'<div class="kpi-label">Time Range</div>'
        f'<div style="font-family:\'Share Tech Mono\',monospace;font-size:.85rem;'
        f'color:{C_ACCENT};margin-top:4px;line-height:1.7;">'
        f'{tr_min}<br>→ {tr_max}</div></div>'
        f'{parse_card_html}'
        '</div></div>'
    )
    st.markdown(pulse_html, unsafe_allow_html=True)

    # ── MODULE 02 · RULES STATUS ──────────────────────────────────────────────
    finding_types = {f.get("type") for f in findings}
    rules_html = ""
    for r in RULES:
        fired  = r["type"] in finding_types
        cnt    = sum(1 for f in findings if f.get("type") == r["type"])
        cls    = "rule-fired" if fired else "rule-clear"
        col    = SEVERITY_COLOR[r["severity"]]
        status = (f'<span style="color:{col};">▲ TRIGGERED</span>'
                  if fired else f'<span style="color:{C_MUTED};">— CLEAR</span>')
        cnt_color = col if fired else C_MUTED
        rules_html += f"""
        <div class="rule-card {cls}">
          <div class="rule-name" style="color:{col};">{r['label']}</div>
          <div class="rule-status">{status}</div>
          <div class="rule-count" style="color:{cnt_color};">{cnt}</div>
          <div class="rule-desc">{r['desc']}</div>
        </div>"""

    st.markdown(f"""
    <div class="module-card">
      <div class="module-label">Module 02</div>
      <div class="module-title">RULES · HEURISTIC STATUS</div>
      <div class="rules-grid">{rules_html}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── MODULE 03 · SIGNAL + INTEL ────────────────────────────────────────────
    col_left, col_right = st.columns([2, 1])

    with col_left:
        card_open("Module 03", "SIGNAL · QUERY VOLUME OVER TIME")
        fig = chart_volume(metrics.get("volume_over_time") or [])
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="no-data">No volume-over-time data.</div>',
                        unsafe_allow_html=True)
        card_close()

    with col_right:
        card_open("Module 04", "INTEL · TOP DOMAINS")
        top = (metrics.get("top_domains") or [])[:10]
        if top:
            max_c = top[0]["count"] if top else 1
            rows_html = ""
            for i, row in enumerate(top):
                bar_w = max(4, int(row["count"] / max_c * 80))
                rows_html += f"""
                <div class="domain-row">
                  <div class="domain-rank">{i+1:02d}</div>
                  <div class="domain-name">{row['domain']}</div>
                  <div class="domain-bar" style="width:{bar_w}px;"></div>
                  <div class="domain-cnt">{row['count']}</div>
                </div>"""
            st.markdown(rows_html, unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">No domain data.</div>',
                        unsafe_allow_html=True)
        card_close()

    # ── MODULE 05 & 06 · SPECTRUM + SIGNATURE ────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        card_open("Module 05", "SPECTRUM · TLD DISTRIBUTION")
        fig = chart_tld(metrics.get("tld_distribution") or [])
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="no-data">No TLD data.</div>',
                        unsafe_allow_html=True)
        card_close()

    with col_b:
        card_open("Module 06", "SIGNATURE · DOMAIN LENGTH")
        fig = chart_length(metrics.get("domain_length_distribution") or [])
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="no-data">No length data.</div>',
                        unsafe_allow_html=True)
        card_close()

    # ── MODULE 07 · FREQUENCY ─────────────────────────────────────────────────
    card_open("Module 07", "FREQUENCY · TOP DOMAIN BREAKDOWN")
    fig = chart_top_domains(metrics.get("top_domains") or [])
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div class="no-data">No data.</div>', unsafe_allow_html=True)
    card_close()

    # ── MODULE 08 · DEPTH + QUERY TYPES ──────────────────────────────────────
    col_d, col_q = st.columns(2)
    with col_d:
        card_open("Module 08", "DEPTH · SUBDOMAIN STRUCTURE  (label count)")
        fig = chart_label_count(metrics.get("label_count_distribution") or [])
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(f"""
            <div class="no-data">No label-count data yet.<br>
            Click ⚡ Re-run Analysis to populate.</div>
            """, unsafe_allow_html=True)
        card_close()

    with col_q:
        card_open("Module 09", "RECORD TYPES · QUERY TYPE DISTRIBUTION")
        fig = chart_query_types(metrics.get("query_type_distribution") or [])
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(f"""
            <div class="no-data">No query-type data yet.<br>
            Click ⚡ Re-run Analysis to populate.</div>
            """, unsafe_allow_html=True)
        card_close()

    # ── MODULE 10 · RESPONSE CODES ────────────────────────────────────────────
    card_open("Module 10", "RESPONSE CODES · RFC 1035 RCODE DISTRIBUTION")
    fig = chart_response_codes(metrics.get("response_code_distribution") or [])
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown(f"""
        <div class="no-data">No response-code data yet.<br>
        Click ⚡ Re-run Analysis to populate.</div>
        """, unsafe_allow_html=True)
    card_close()

    # ── MODULE 11 · RULE FIRING MATRIX ───────────────────────────────────────
    card_open("Module 11", "MATRIX · RULE FIRINGS ACROSS DATASETS")
    all_ds = list_datasets()
    if all_ds:
        fig = chart_rules_heatmap(all_ds)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.markdown('<div class="no-data">No datasets found.</div>',
                    unsafe_allow_html=True)
    card_close()

    # ── MODULE 12 · COMPARE ───────────────────────────────────────────────────
    card_open("Module 12", "COMPARE · MULTI-DATASET OVERVIEW")
    if compare_sel:
        fig = chart_compare(compare_sel)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown('<div class="no-data">Run analysis on each dataset first.</div>',
                        unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">Select datasets in the sidebar.</div>',
                    unsafe_allow_html=True)
    card_close()

    # ── MODULE 13 · ALERTS ────────────────────────────────────────────────────
    card_open("Module 13", "ALERTS · DETAILED OBSERVATIONS")
    if findings:
        # Group by rule type
        for rule in RULES:
            rule_findings = [f for f in findings if f.get("type") == rule["type"]]
            if not rule_findings:
                continue
            sev = rule["severity"]
            cls = SEVERITY_CLASS[sev]
            col = SEVERITY_COLOR[sev]
            icon = SEVERITY_ICON[sev]
            st.markdown(f"""
            <div style="font-family:'Share Tech Mono',monospace;font-size:.7rem;
                        letter-spacing:2px;color:{col};text-transform:uppercase;
                        margin:14px 0 6px;">
                {icon} &nbsp; {rule['label']} &nbsp;
                <span style="color:{C_MUTED};">({len(rule_findings)} finding{'s' if len(rule_findings)>1 else ''})</span>
            </div>
            """, unsafe_allow_html=True)
            for f in rule_findings:
                why   = f.get("why_flagged", "")
                evid  = f.get("evidence") or {}
                evid_str = "  ·  ".join(f"{k}: {v}" for k, v in list(evid.items())[:5])
                st.markdown(f"""
                <div class="alert-card {cls}">
                  <div class="alert-why">{why}</div>
                  {"<div class='alert-evid'>" + evid_str + "</div>" if evid_str else ""}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="alert-card alert-low">
          <div class="alert-type" style="color:{C_GREEN};">✔ &nbsp; ALL CLEAR</div>
          <div class="alert-why">No unusual behaviour flagged for this dataset.</div>
        </div>
        """, unsafe_allow_html=True)
    card_close()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center;padding:32px 0 16px;
                font-family:'Share Tech Mono',monospace;font-size:.65rem;
                color:{C_MUTED};letter-spacing:2px;text-transform:uppercase;">
        DNS Behaviour Monitor &nbsp;·&nbsp; Analytical view only
        &nbsp;·&nbsp; No threat or security claims
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
