"""
Offline snapshot and HTML template helpers for DSP archive packaging.
"""

from __future__ import annotations

import json
from typing import Any


def offline_snapshot_html(dsp_payload: dict[str, Any]) -> str:
    data_json = json.dumps(dsp_payload, ensure_ascii=False, sort_keys=True, indent=2, default=str).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QCSpec DSP Offline Verify</title>
  <style>
    :root {{
      --mono: 'JetBrains Mono', monospace;
      --sans: 'Noto Sans SC', sans-serif;
      --ok: #00b894;
      --bad: #ff4d6a;
      --warn: #f39c12;
    }}
    :root[data-theme="light"] {{
      --bg: #eef4ff; --card: #ffffff; --line: #d5e1f4; --text: #112a42; --muted: #5f7690;
      --chip: #eaf1ff;
    }}
    :root[data-theme="dark"] {{
      --bg: #0b1524; --card: #0f1c30; --line: #21354f; --text: #d9e8ff; --muted: #90aac6;
      --chip: #14253e;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:var(--sans); background:var(--bg); color:var(--text); }}
    .wrap {{ max-width: 1080px; margin: 0 auto; padding: 20px; }}
    .top {{ display:flex; gap:12px; align-items:center; justify-content:space-between; }}
    .title {{ font-size:20px; font-weight:800; }}
    .toggle {{ border:1px solid var(--line); background:var(--chip); color:var(--text); border-radius:10px; padding:8px 12px; cursor:pointer; }}
    .card {{ margin-top:12px; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }}
    .status {{ display:flex; gap:8px; align-items:center; }}
    .badge {{ border-radius:999px; padding:3px 10px; font-size:11px; font-weight:700; }}
    .ok {{ color:var(--ok); background:rgba(0,184,148,.14); }}
    .bad {{ color:var(--bad); background:rgba(255,77,106,.14); }}
    .warn {{ color:var(--warn); background:rgba(243,156,18,.15); }}
    .grid {{ display:grid; grid-template-columns: 220px 1fr; gap:10px; }}
    .k {{ color:var(--muted); font-size:12px; }}
    .v {{ font-family:var(--mono); font-size:12px; word-break:break-all; }}
    .row {{ padding:6px 0; border-bottom:1px solid var(--line); }}
    .row:last-child {{ border-bottom:none; }}
    table {{ width:100%; border-collapse: collapse; font-size:12px; }}
    th, td {{ border-bottom:1px solid var(--line); padding:8px; text-align:left; }}
    th {{ color:var(--muted); font-weight:700; }}
    pre {{ margin:0; padding:10px; border-radius:8px; border:1px solid var(--line); background:var(--chip); overflow:auto; font-family:var(--mono); font-size:11px; }}
    @media (max-width: 700px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div class="title">QCSpec DSP 离线核验报告</div>
      <button id="theme-btn" class="toggle" type="button">切换主题</button>
    </div>
    <div class="card">
      <div class="status">
        <span id="hash-badge" class="badge warn">Hash 计算中...</span>
        <span id="trust-badge" class="badge warn">主权链可信状态待确认</span>
      </div>
    </div>
    <div class="card grid">
      <div class="k">Proof ID</div><div class="v" id="proof-id">-</div>
      <div class="k">业务结论</div><div class="v" id="result-cn">-</div>
      <div class="k">签署人</div><div class="v" id="signed-by">-</div>
      <div class="k">签署时间</div><div class="v" id="signed-at">-</div>
      <div class="k">归档时间</div><div class="v" id="archive-at">-</div>
      <div class="k">规范 URI</div><div class="v" id="spec-uri">-</div>
      <div class="k">规范快照</div><div class="v" id="spec-snapshot">-</div>
      <div class="k">提供哈希</div><div class="v" id="provided-hash">-</div>
      <div class="k">计算哈希</div><div class="v" id="computed-hash">-</div>
    </div>
    <div class="card">
      <div class="k" style="margin-bottom:8px;">证据列表</div>
      <table>
        <thead><tr><th>#</th><th>证据文件</th><th>SHA-256</th><th>状态</th></tr></thead>
        <tbody id="evidence-tbody"></tbody>
      </table>
    </div>
    <div class="card">
      <div class="k" style="margin-bottom:8px;">原始 JSON</div>
      <pre id="payload"></pre>
    </div>
  </div>
  <script id="embedded-dsp-json" type="application/json">{data_json}</script>
  <script>
    function stableStringify(value) {{
      if (value === null || value === undefined) return 'null';
      if (typeof value !== 'object') return JSON.stringify(value);
      if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']';
      const keys = Object.keys(value).sort();
      return '{{' + keys.map(k => JSON.stringify(k) + ':' + stableStringify(value[k])).join(',') + '}}';
    }}
    async function sha256Hex(text) {{
      const data = new TextEncoder().encode(text);
      const digest = await crypto.subtle.digest('SHA-256', data);
      return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
    }}
    function setTheme(next) {{
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('dsp_theme', next);
    }}
    async function loadDsp() {{
      try {{
        const res = await fetch('./provenance_chain.json', {{ cache: 'no-store' }});
        if (res.ok) return await res.json();
      }} catch (err) {{}}
      const raw = document.getElementById('embedded-dsp-json').textContent || '{{}}';
      return JSON.parse(raw);
    }}
    (async function () {{
      const saved = localStorage.getItem('dsp_theme') || 'light';
      setTheme(saved === 'dark' ? 'dark' : 'light');
      document.getElementById('theme-btn').addEventListener('click', () => {{
        const cur = document.documentElement.getAttribute('data-theme') || 'light';
        setTheme(cur === 'dark' ? 'light' : 'dark');
      }});

      const dsp = await loadDsp();
      const detail = (dsp && dsp.verify_detail) || {{}};
      const summary = detail.summary || {{}};
      const sovereignty = detail.sovereignty || {{}};
      const person = detail.person || {{}};
      const hv = detail.hash_verification || {{}};
      const source = String(hv.source_json || stableStringify(detail.hash_payload || {{}}));
      const expected = String(hv.provided_hash || sovereignty.proof_hash || '').trim().toLowerCase();

      document.getElementById('proof-id').textContent = detail.proof_id || dsp.proof_id || '-';
      document.getElementById('result-cn').textContent = summary.result_cn || summary.result || '-';
      document.getElementById('signed-by').textContent = sovereignty.signed_by || person.name || '-';
      document.getElementById('signed-at').textContent = sovereignty.signed_at || person.time || '-';
      document.getElementById('archive-at').textContent = dsp.generated_at || '-';
      document.getElementById('spec-uri').textContent = summary.spec_uri || '-';
      const specBundle = dsp.spec_snapshot_bundle || {{}};
      document.getElementById('spec-snapshot').textContent = specBundle.primary_snapshot_text || summary.spec_snapshot || '-';
      document.getElementById('provided-hash').textContent = expected || '-';
      document.getElementById('payload').textContent = JSON.stringify(dsp, null, 2);

      const evidence = (dsp.evidence || {{}}).items || [];
      const tbody = document.getElementById('evidence-tbody');
      if (!evidence.length) {{
        tbody.innerHTML = '<tr><td colspan="4">无证据文件</td></tr>';
      }} else {{
        tbody.innerHTML = evidence.map((it, idx) => `<tr><td>${{idx+1}}</td><td>${{it.file_name || '-'}}</td><td>${{it.evidence_hash || it.downloaded_sha256 || '-'}}</td><td>${{it.status || '-'}}</td></tr>`).join('');
      }}

      const hashBadge = document.getElementById('hash-badge');
      if (!expected || !source || !window.crypto?.subtle) {{
        hashBadge.textContent = 'Hash 暂不可用';
        hashBadge.className = 'badge warn';
      }} else {{
        try {{
          const computed = await sha256Hex(source);
          document.getElementById('computed-hash').textContent = computed;
          const ok = computed.toLowerCase() === expected;
          hashBadge.textContent = ok ? 'Hash 校验通过' : 'Hash 校验失败';
          hashBadge.className = 'badge ' + (ok ? 'ok' : 'bad');
        }} catch (err) {{
          hashBadge.textContent = 'Hash 计算异常';
          hashBadge.className = 'badge bad';
        }}
      }}

      const trust = document.getElementById('trust-badge');
      const trustOk = Boolean(hv.matches);
      trust.textContent = trustOk ? '主权链可信' : '主权链不可信';
      trust.className = 'badge ' + (trustOk ? 'ok' : 'bad');
    }})();
  </script>
</body>
</html>"""


def pdf_html_template() -> str:
    """
    HTML template reference for PDF variable mapping.
    Paths are aligned to VerifyPayload structure.
    """
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>QCSpec DSP Report Template</title>
  <style>
    body { font-family: 'Noto Sans SC', sans-serif; color: #0f2942; padding: 24px; }
    .title { font-size: 24px; font-weight: 800; margin-bottom: 10px; }
    .ok { color: #0f9d7a; } .bad { color: #e53958; }
    .row { margin: 6px 0; }
    .k { display:inline-block; width:180px; color:#5f7690; }
    .v { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body>
  <div class="title">
    QCSpec Data Sovereignty Report
    {% if verify_detail.hash_verification.matches %}<span class="ok">主权链可信</span>{% else %}<span class="bad">主权链不可信</span>{% endif %}
  </div>
  <div class="row"><span class="k">Proof ID</span><span class="v">{{ verify_detail.proof_id }}</span></div>
  <div class="row"><span class="k">Business Result</span><span class="v">{{ verify_detail.summary.result_cn }}</span></div>
  <div class="row"><span class="k">Signer</span><span class="v">{{ verify_detail.sovereignty.signed_by }}</span></div>
  <div class="row"><span class="k">Signed At</span><span class="v">{{ verify_detail.sovereignty.signed_at }}</span></div>
  <div class="row"><span class="k">Archive At</span><span class="v">{{ generated_at }}</span></div>
  <div class="row"><span class="k">Spec URI</span><span class="v">{{ verify_detail.summary.spec_uri }}</span></div>
  <div class="row"><span class="k">Spec Snapshot</span><span class="v">{{ verify_detail.qcgate.rules[0].spec_excerpt }}</span></div>
  <div class="row"><span class="k">Proof Hash</span><span class="v">{{ verify_detail.sovereignty.proof_hash }}</span></div>
  <div class="row"><span class="k">Hash Matches</span><span class="v">{{ verify_detail.hash_verification.matches }}</span></div>
</body>
</html>
"""
