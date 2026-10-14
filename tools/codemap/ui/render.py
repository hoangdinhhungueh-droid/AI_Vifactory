#!/usr/bin/env python3
"""tools/codemap/ui/render.py — Self-contained HTML Visual Pipeline Flow Generator.

Embeds codemap registry and optional runtime traces into a 0-dependency offline HTML dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.codemap.lineage import compute_lineage_report


def generate_pipeline_html(
    codemap_file: Path | None = None,
    run_id: str | None = None,
    output_html: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    root = (repo_root or Path.cwd()).resolve()
    cmap_path = codemap_file or (root / ".codemap" / "codemap.json")
    out_path = output_html or (root / ".codemap" / "pipeline.html")

    if not cmap_path.exists():
        raise FileNotFoundError(f"Codemap file not found at {cmap_path}. Run build first.")

    codemap_data = json.loads(cmap_path.read_text(encoding="utf-8"))

    # Load runtime events if run_id given
    run_events = []
    run_approvals = []
    lineage_reports = []

    available_runs = []
    runs_dir = root / ".codemap" / "runs"
    if runs_dir.exists():
        for r_path in sorted(runs_dir.iterdir(), reverse=True):
            if r_path.is_dir():
                available_runs.append(r_path.name)

    selected_run = run_id or (available_runs[0] if available_runs else None)

    if selected_run:
        target_run_dir = runs_dir / selected_run
        events_file = target_run_dir / "events.jsonl"
        if events_file.exists():
            for line in events_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        run_events.append(json.loads(line))
                    except Exception:
                        pass

        approvals_file = target_run_dir / "approvals.jsonl"
        if approvals_file.exists():
            for line in approvals_file.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        run_approvals.append(json.loads(line))
                    except Exception:
                        pass

        lineage_objs = compute_lineage_report(selected_run, repo_root=root)
        lineage_reports = [r.model_dump(mode="json") for r in lineage_objs]

    payload = {
        "codemap": codemap_data,
        "selected_run": selected_run,
        "available_runs": available_runs,
        "events": run_events,
        "approvals": run_approvals,
        "lineage": lineage_reports,
        "repo_root": str(root),
    }

    # Safe JSON embed escaping </ to prevent closing </script> tags early
    json_str = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    template_file = Path(__file__).parent / "template.html"
    if not template_file.exists():
        # Fallback to inline minimal template if template.html missing
        html_content = _build_default_html(json_str)
    else:
        raw_tmpl = template_file.read_text(encoding="utf-8")
        html_content = raw_tmpl.replace("<!-- DATA_PAYLOAD_PLACEHOLDER -->", json_str)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_content, encoding="utf-8")
    print(f"[+] Interactive Visual Pipeline Map generated: {out_path.as_uri()}")
    return out_path


def _build_default_html(json_payload: str) -> str:
    """Built-in production single-page HTML canvas application."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Video Factory — Pipeline GPS Code Map</title>
  <style>
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #38bdf8;
      --success: #22c55e;
      --warning: #f59e0b;
      --danger: #ef4444;
      --code-bg: #090d16;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .title-group {{ display: flex; align-items: center; gap: 12px; }}
    .badge {{
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid var(--accent);
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
    }}
    .badge-ok {{ background: rgba(34, 197, 94, 0.15); color: var(--success); border-color: var(--success); }}
    .badge-warn {{ background: rgba(245, 158, 11, 0.15); color: var(--warning); border-color: var(--warning); }}
    .badge-err {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); border-color: var(--danger); }}

    .nav-tabs {{ display: flex; gap: 8px; }}
    .tab-btn {{
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
    }}
    .tab-btn.active {{
      background: var(--accent);
      color: #0f172a;
      border-color: var(--accent);
      font-weight: 700;
    }}

    main {{
      display: flex;
      flex: 1;
      overflow: hidden;
    }}
    #flow-panel {{
      flex: 1;
      overflow: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 16px;
    }}
    #detail-panel {{
      width: 480px;
      background: var(--surface);
      border-left: 1px solid var(--border);
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}

    /* Stage Nodes */
    .stage-card {{
      background: var(--surface);
      border: 2px solid var(--border);
      border-radius: 8px;
      width: 640px;
      padding: 16px;
      cursor: pointer;
      transition: all 0.15s ease-in-out;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .stage-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
    .stage-card.selected {{
      border-color: var(--accent);
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.3);
    }}
    .stage-header {{ display: flex; justify-content: space-between; align-items: center; }}
    .stage-title {{ font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
    .stage-meta {{ font-size: 12px; color: var(--text-muted); font-family: monospace; }}

    .stage-io {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      background: var(--code-bg);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-family: monospace;
    }}
    .io-label {{ color: var(--text-muted); font-size: 11px; text-transform: uppercase; }}

    .connector {{
      width: 2px;
      height: 24px;
      background: var(--border);
      position: relative;
    }}
    .connector::after {{
      content: "▼";
      position: absolute;
      bottom: -10px;
      left: -5px;
      font-size: 10px;
      color: var(--border);
    }}

    /* Inspector */
    h3 {{ font-size: 15px; text-transform: uppercase; color: var(--accent); letter-spacing: 0.5px; }}
    .code-block {{
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      font-family: Consolas, monospace;
      font-size: 12px;
      overflow-x: auto;
      white-space: pre-wrap;
    }}
    .btn-copy {{
      background: rgba(56, 189, 248, 0.2);
      border: 1px solid var(--accent);
      color: var(--accent);
      padding: 4px 10px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 11px;
      margin-top: 6px;
    }}
    .ide-link {{
      color: var(--accent);
      text-decoration: none;
      display: inline-block;
      margin-top: 4px;
      font-size: 12px;
    }}
    .ide-link:hover {{ text-decoration: underline; }}

    /* Lineage table */
    .lineage-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    .lineage-table th, .lineage-table td {{
      border: 1px solid var(--border);
      padding: 8px 10px;
      text-align: left;
    }}
    .lineage-table th {{ background: var(--code-bg); color: var(--text-muted); }}
  </style>
</head>
<body>
  <header>
    <div class="title-group">
      <h2>🎬 AI Video Factory — Pipeline GPS Code Map</h2>
      <span class="badge" id="hdr-summary">Loading...</span>
    </div>
    <div class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab('flow')">🗺️ Pipeline Flow</button>
      <button class="tab-btn" onclick="switchTab('lineage')">🔍 Lineage Audit</button>
      <button class="tab-btn" onclick="switchTab('handoffs')">📐 Handoffs</button>
    </div>
  </header>

  <main>
    <div id="flow-panel"></div>
    <div id="detail-panel">
      <h3>Select a Stage Node</h3>
      <p style="color:var(--text-muted);font-size:13px;">Click on any pipeline stage to view source lines, Pydantic schemas, failure modes, and verification commands.</p>
    </div>
  </main>

  <script type="application/json" id="data">
{json_payload}
  </script>

  <script>
    const payload = JSON.parse(document.getElementById('data').textContent);
    const codemap = payload.codemap || {{}};
    const stages = codemap.stages || [];
    const handoffs = codemap.handoffs || [];
    const lineage = payload.lineage || [];

    document.getElementById('hdr-summary').textContent = `${{stages.length}} Stages | ${{handoffs.length}} Handoffs`;

    let activeTab = 'flow';
    let selectedStageId = stages.length > 0 ? stages[0].id : null;

    function renderFlow() {{
      const container = document.getElementById('flow-panel');
      container.innerHTML = '';

      stages.forEach((stage, idx) => {{
        const card = document.createElement('div');
        card.className = `stage-card ${{stage.id === selectedStageId ? 'selected' : ''}}`;
        card.onclick = () => selectStage(stage.id);

        card.innerHTML = `
          <div class="stage-header">
            <span class="stage-title">#${{stage.order}} ${{stage.name}}</span>
            <span class="badge badge-ok">SCHEMA READY</span>
          </div>
          <div class="stage-meta">${{stage.ref.file}}:${{stage.ref.line_start}}</div>
          <div class="stage-io">
            <div>
              <div class="io-label">Input Model</div>
              <div>${{stage.input_model || '(None / Seed Input)'}}</div>
            </div>
            <div>
              <div class="io-label">Output Model</div>
              <div>${{stage.output_model || '(Artifact / Video)'}}</div>
            </div>
          </div>
        `;
        container.appendChild(card);

        if (idx < stages.length - 1) {{
          const conn = document.createElement('div');
          conn.className = 'connector';
          container.appendChild(conn);
        }}
      }});
    }}

    function selectStage(stageId) {{
      selectedStageId = stageId;
      renderFlow();
      renderDetail();
    }}

    function renderDetail() {{
      const panel = document.getElementById('detail-panel');
      const stage = stages.find(s => s.id === selectedStageId);
      if (!stage) return;

      const ideLink = `vscode://file/${{payload.repo_root}}/${{stage.ref.file}}:${{stage.ref.line_start}}`;

      panel.innerHTML = `
        <div>
          <h3>Stage Node: ${{stage.name}}</h3>
          <div style="font-size:13px;color:var(--text-muted);margin-top:4px;">ID: <code>${{stage.id}}</code> (Order ${{stage.order}})</div>
          <a class="ide-link" href="${{ideLink}}">📍 Open in VS Code (${{stage.ref.file}}:${{stage.ref.line_start}})</a>
        </div>

        <div>
          <h3>In / Out Models</h3>
          <div class="code-block">Input:  ${{stage.input_model || 'None'}}\nOutput: ${{stage.output_model || 'None'}}</div>
        </div>

        <div>
          <h3>Triggers & Upstream</h3>
          <div class="code-block">Triggers: ${{stage.triggers.join(', ') || 'Manual / Orchestrator'}}\nUpstream: ${{stage.upstream.join(', ') || 'None (Genesis)'}}\nDownstream: ${{stage.downstream.join(', ') || 'None (Terminal)'}}</div>
        </div>

        <div>
          <h3>Failure Modes (${{stage.failure_modes.length}})</h3>
          <div class="code-block">${{stage.failure_modes.map(f => `[${{f.origin.toUpperCase()}}] ${{f.exc_type}} at line ${{f.ref.line_start}}`).join('\\n') || 'None declared'}}</div>
        </div>

        <div>
          <h3>Verification Commands</h3>
          <div class="code-block" id="cmd-box">${{stage.verify_cmds.join('\\n') || `python -m orchestrator.run_pipeline --only ${{stage.id}}`}}</div>
          <button class="btn-copy" onclick="copyVerifyCmd()">📋 Copy Verify Command</button>
        </div>
      `;
    }}

    function copyVerifyCmd() {{
      const text = document.getElementById('cmd-box').textContent;
      navigator.clipboard.writeText(text);
      alert('Verification command copied to clipboard!');
    }}

    function switchTab(tab) {{
      activeTab = tab;
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');

      const flow = document.getElementById('flow-panel');
      if (tab === 'flow') {{
        flow.style.display = 'flex';
        renderFlow();
      }} else if (tab === 'lineage') {{
        flow.style.display = 'block';
        renderLineageView();
      }} else if (tab === 'handoffs') {{
        flow.style.display = 'block';
        renderHandoffsView();
      }}
    }}

    function renderLineageView() {{
      const flow = document.getElementById('flow-panel');
      if (!lineage || lineage.length === 0) {{
        flow.innerHTML = `<div style="padding:40px;color:var(--text-muted);text-align:center;">
          <h3>No Lineage Audit Data Recorded for Run</h3>
          <p style="margin-top:8px;">Run a pipeline with <code>record_approval()</code> and <code>run_context()</code> to track data lineage.</p>
        </div>`;
        return;
      }}

      flow.innerHTML = `
        <div style="width:100%;max-width:960px;">
          <h2 style="margin-bottom:16px;">🔍 Data Lineage & Approval Audit</h2>
          ${{lineage.map(rep => `
            <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:20px;">
              <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                <div>
                  <strong>Approval ID:</strong> <code>${{rep.approval_id}}</code> → Target: <code>${{rep.target_stage}}</code>
                </div>
                <span class="badge ${{rep.overall === 'INTACT' ? 'badge-ok' : 'badge-err'}}">${{rep.overall}}</span>
              </div>
              <table class="lineage-table">
                <thead>
                  <tr>
                    <th>Field Pointer</th>
                    <th>Verdict</th>
                    <th>Approved Hash</th>
                    <th>Consumed Hash</th>
                    <th>Diagnostic Note</th>
                  </tr>
                </thead>
                <tbody>
                  ${{rep.fields.map(f => `
                    <tr>
                      <td><code>${{f.path}}</code></td>
                      <td><span class="badge ${{f.verdict === 'CARRIED' ? 'badge-ok' : 'badge-err'}}">${{f.verdict}}</span></td>
                      <td><code>${{f.approved_hash ? f.approved_hash.slice(0, 10) + '...' : '-'}}</code></td>
                      <td><code>${{f.consumed_hash ? f.consumed_hash.slice(0, 10) + '...' : '-'}}</code></td>
                      <td>${{f.note || ''}}</td>
                    </tr>
                  `).join('')}}
                </tbody>
              </table>
            </div>
          `).join('')}}
        </div>
      `;
    }}

    function renderHandoffsView() {{
      const flow = document.getElementById('flow-panel');
      flow.innerHTML = `
        <div style="width:100%;max-width:960px;">
          <h2 style="margin-bottom:16px;">📐 Inter-Stage Boundary Handoffs</h2>
          ${{handoffs.map(h => `
            <div style="background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
              <div>
                <strong>${{h.from_stage}}</strong> ──► <strong>${{h.to_stage}}</strong>
                <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">
                  Producer: ${{h.producer_model || 'None'}} | Consumer: ${{h.consumer_model || 'None'}}
                </div>
                ${{h.issues.length > 0 ? `<div style="color:var(--danger);font-size:12px;margin-top:6px;">Issues: ${{h.issues.map(i => i.detail).join('; ')}}</div>` : ''}}
              </div>
              <span class="badge ${{h.status === 'MATCH' ? 'badge-ok' : (h.status === 'PARTIAL' ? 'badge-warn' : 'badge-err')}}">${{h.status}}</span>
            </div>
          `).join('')}}
        </div>
      `;
    }}

    renderFlow();
    renderDetail();
  </script>
</body>
</html>
"""
