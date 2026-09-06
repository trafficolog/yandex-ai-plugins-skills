from __future__ import annotations

from html import escape
from typing import Any


CSP = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def _e(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    return escape(str(value), quote=True)


def _metric_text(metrics: Any) -> str:
    if not isinstance(metrics, dict) or not metrics:
        return "—"
    parts: list[str] = []
    for name in sorted(metrics):
        value = metrics[name]
        if not isinstance(value, dict):
            continue
        parts.append(
            f"{_e(name)}: {_e(value.get('previous'))} → {_e(value.get('current'))} "
            f"(Δ {_e(value.get('delta'))})"
        )
    return "; ".join(parts) if parts else "—"


def _table(headers: list[str], rows: list[list[str]], *, table_id: str) -> str:
    head = "".join(f'<th data-sort="{index}">{_e(label)}</th>' for index, label in enumerate(headers))
    if rows:
        body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    else:
        body = f'<tr><td colspan="{len(headers)}">No data</td></tr>'
    return f'<table id="{_e(table_id)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def render_html(report: dict[str, Any]) -> str:
    if not isinstance(report, dict) or report.get("schema") != "seo-weekly-organic-report/v1":
        raise ValueError("unsupported weekly report schema")

    project = report.get("project") or {}
    coverage = report.get("coverage") or {}
    summary = report.get("summary") or {}
    limitations = report.get("limitations") or []
    findings = report.get("findings") or []
    query_movers = report.get("query_movers") or []
    page_movers = report.get("page_movers") or []
    evidence = report.get("evidence") or []
    delegated = report.get("delegated_previews") or []

    finding_rows = [
        [
            _e(item.get("finding_id")),
            _e(item.get("kind")),
            _e(item.get("claim_class")),
            _e(item.get("subject")),
            _metric_text(item.get("metrics")),
            _e(", ".join(item.get("evidence_ids", []))),
        ]
        for item in findings
        if isinstance(item, dict)
    ]
    query_rows = [
        [
            _e(item.get("query_id")),
            _e(item.get("query")),
            _metric_text(item.get("metrics")),
            _e(", ".join(item.get("evidence_ids", []))),
        ]
        for item in query_movers
        if isinstance(item, dict)
    ]
    page_rows = [
        [
            _e(item.get("page_id")),
            _e(item.get("url")),
            _metric_text(item.get("metrics")),
            _e(", ".join(item.get("evidence_ids", []))),
        ]
        for item in page_movers
        if isinstance(item, dict)
    ]

    limitation_items = "".join(f"<li>{_e(item)}</li>" for item in limitations) or "<li>None declared</li>"
    coverage_items = "".join(
        f'<div class="stat"><span>{_e(name)}</span><strong>{_e(coverage[name])}</strong></div>'
        for name in sorted(coverage)
    )
    summary_items = "".join(
        f'<div class="stat"><span>{_e(name.replace("_", " ").title())}</span><strong>{_e(summary[name])}</strong></div>'
        for name in sorted(summary)
    )

    preview_rows = "".join(
        "<tr>"
        f"<td>{_e(item.get('preview_id'))}</td>"
        f"<td>{_e(item.get('owner'))}</td>"
        f"<td>{_e(item.get('operation'))}</td>"
        "<td><strong>PREVIEW-ONLY</strong></td>"
        "</tr>"
        for item in delegated
        if isinstance(item, dict)
    ) or '<tr><td colspan="4">No delegated previews</td></tr>'

    evidence_blocks = "".join(
        "<details>"
        f"<summary>{_e(item.get('evidence_id'))} · {_e(item.get('claim_class'))} · {_e(item.get('source'))}</summary>"
        '<dl class="evidence">'
        + "".join(
            f"<dt>{_e(key)}</dt><dd>{_e(value)}</dd>"
            for key, value in sorted(item.items())
            if key not in {"evidence_id", "claim_class", "source"}
        )
        + "</dl></details>"
        for item in evidence
        if isinstance(item, dict)
    ) or "<p>No evidence records.</p>"

    findings_table = (
        _table(
            ["ID", "Kind", "Claim class", "Subject", "Metrics", "Evidence"],
            finding_rows,
            table_id="findings-table",
        )
        if finding_rows
        else "<p>No findings</p>"
    )

    style = """
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#16202a;background:#f6f8fa}
body{margin:0;padding:0}main{max-width:1180px;margin:0 auto;padding:32px}h1{margin-bottom:4px}h2{margin-top:34px}
.muted{color:#59636e}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.stat{background:#fff;border:1px solid #d8dee4;border-radius:8px;padding:12px;display:flex;flex-direction:column;gap:6px}.stat span{font-size:12px;color:#59636e;text-transform:uppercase}.limitations{border:2px solid #b54708;background:#fff8eb;padding:14px 18px;border-radius:8px}table{width:100%;border-collapse:collapse;background:#fff}th,td{border:1px solid #d8dee4;padding:8px;text-align:left;vertical-align:top}th{background:#eef2f6;cursor:pointer}input{width:100%;max-width:460px;padding:9px;margin:0 0 12px;border:1px solid #9da7b1;border-radius:6px}details{background:#fff;border:1px solid #d8dee4;border-radius:6px;margin:8px 0;padding:10px}summary{cursor:pointer;font-weight:600}.evidence{display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:4px 12px}.evidence dt{font-weight:600}.evidence dd{margin:0;overflow-wrap:anywhere}.preview{font-weight:700;color:#8a2d00}
""".strip()

    script = """
(function(){
  function text(row){return row.textContent.toLowerCase();}
  var filter=document.getElementById('finding-filter');
  if(filter){filter.addEventListener('input',function(){var q=this.value.toLowerCase();document.querySelectorAll('#findings-table tbody tr').forEach(function(row){row.hidden=q && text(row).indexOf(q)<0;});});}
  document.querySelectorAll('th[data-sort]').forEach(function(th){th.addEventListener('click',function(){var table=th.closest('table');var body=table.querySelector('tbody');var index=Number(th.getAttribute('data-sort'));var rows=Array.from(body.querySelectorAll('tr'));rows.sort(function(a,b){return a.children[index].textContent.localeCompare(b.children[index].textContent,undefined,{numeric:true});});rows.forEach(function(row){body.appendChild(row);});});});
})();
""".strip()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="{escape(CSP, quote=True)}">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(project.get('name', 'Weekly Organic Report'))} — Weekly Organic Report</title>
<style>{style}</style>
</head>
<body><main>
<h1>Weekly Organic Report</h1>
<p class="muted">{_e(project.get('name'))} · {_e(report.get('period', {}).get('from'))} — {_e(report.get('period', {}).get('to'))} · report {_e(report.get('report_id'))}</p>
<h2>Summary</h2><div class="grid">{summary_items}</div>
<h2>Coverage</h2><div class="grid">{coverage_items}</div>
<h2>Limitations</h2><div class="limitations"><ul>{limitation_items}</ul></div>
<h2>Findings</h2><input id="finding-filter" type="search" placeholder="Filter findings" aria-label="Filter findings">{findings_table}
<h2>Query movers</h2>{_table(['ID','Query','Metrics','Evidence'], query_rows, table_id='query-movers')}
<h2>Page movers</h2>{_table(['ID','URL','Metrics','Evidence'], page_rows, table_id='page-movers')}
<h2>Delegated previews</h2><p class="preview">PREVIEW-ONLY: these rows are recommendations, not approvals or executable write permission.</p><table><thead><tr><th>ID</th><th>Owner</th><th>Operation</th><th>State</th></tr></thead><tbody>{preview_rows}</tbody></table>
<h2>Evidence / provenance</h2>{evidence_blocks}
</main><script>{script}</script></body></html>"""
