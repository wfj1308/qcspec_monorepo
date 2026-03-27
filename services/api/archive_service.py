"""
Data Sovereignty Package (DSP) archive builder.
services/api/archive_service.py
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib import request as urlrequest
import zipfile

try:
    from reportlab.lib.colors import Color
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    _HAS_REPORTLAB = True
except Exception:
    _HAS_REPORTLAB = False


SOVEREIGN_BLOCK_HEIGHT = 8847001


def _to_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return str(value)


def _pdf_escape(text: str) -> str:
    return _to_text(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _safe_file_name(name: str, fallback: str) -> str:
    text = _to_text(name).strip() or fallback
    text = re.sub(r"[^\w.\-]+", "_", text, flags=re.ASCII)
    return text[:180] or fallback


def _clean_no_qmark(value: Any, fallback: str = "-") -> str:
    text = _to_text(value).strip()
    if not text:
        return fallback
    text = text.replace("???", "").replace("??", "")
    text = text.replace("?", "□")
    text = text.strip()
    return text or fallback


def _result_cn_from_summary(summary: dict[str, Any]) -> str:
    token = _to_text(summary.get("result") or "").strip().upper()
    raw_cn = _to_text(summary.get("result_cn") or "").strip()
    if token == "PASS":
        return "合格"
    if token == "FAIL":
        return "未合格"
    if "不合格" in raw_cn or "未合格" in raw_cn:
        return "未合格"
    if "合格" in raw_cn and "不" not in raw_cn and "未" not in raw_cn:
        return "合格"
    if raw_cn:
        return _clean_no_qmark(raw_cn, fallback="待判定")
    return "待判定"


def _signer_from_payload(sovereignty: dict[str, Any], person: dict[str, Any]) -> str:
    # Mandatory mapping preference: sovereignty.signed_by
    primary = _to_text(sovereignty.get("signed_by")).strip()
    if primary:
        return _clean_no_qmark(primary, fallback="未知执行体")
    fallback = _to_text(person.get("name")).strip()
    return _clean_no_qmark(fallback, fallback="未知执行体")


def _first_rule_spec_excerpt(verify_detail: dict[str, Any]) -> str:
    qcgate = verify_detail.get("qcgate") if isinstance(verify_detail.get("qcgate"), dict) else {}
    rules = qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []
    if rules and isinstance(rules[0], dict):
        text = _to_text(rules[0].get("spec_excerpt")).strip()
        if text:
            return _clean_no_qmark(text, fallback="无可用规范摘要")
    return ""


def _pdf_report_bytes_legacy(lines: list[str], *, watermark: str, trust_ok: bool) -> bytes:
    """
    Minimal single-page PDF with:
    - primary report text block
    - top-right watermark
    """
    body = ["BT", "/F1 12 Tf", "50 780 Td"]
    first = True
    for raw in lines[:42]:
        line = _pdf_escape(raw)
        if not first:
            body.append("0 -16 Td")
        body.append(f"({line}) Tj")
        first = False
    body.append("ET")

    wm_color = "0.15 0.62 0.37 rg" if trust_ok else "0.78 0.18 0.24 rg"
    wm = [
        "BT",
        "/F1 10 Tf",
        wm_color,
        "360 812 Td",
        f"({_pdf_escape(watermark)}) Tj",
        "ET",
    ]
    stream = "\n".join(body + wm).encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
    )
    objects.append(b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    objects.append(
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
        + stream
        + b"\nendstream endobj\n"
    )

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(out.tell())
        out.write(obj)
    xref_pos = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))
    out.write(
        (
            "trailer << /Size {size} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".format(
                size=len(objects) + 1,
                xref=xref_pos,
            )
        ).encode("ascii")
    )
    return out.getvalue()


def _candidate_cjk_font_paths() -> list[Path]:
    return [
        # Windows
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyh.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        # macOS
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        # Linux common
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]


def _register_pdf_font() -> str:
    if not _HAS_REPORTLAB:
        raise RuntimeError("reportlab unavailable")

    for path in _candidate_cjk_font_paths():
        if not path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("QCSpecCJK", str(path)))
            return "QCSpecCJK"
        except Exception:
            continue
    # CID fallback can render Chinese on most readers, even without local TTF registration.
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        return "STSong-Light"
    except Exception as exc:
        raise RuntimeError(f"no_cjk_font: {exc}") from exc


def _wrap_line(text: str, *, font_name: str, font_size: int, max_width: float) -> list[str]:
    src = _to_text(text)
    if not src:
        return [""]
    out: list[str] = []
    current = ""
    for ch in src:
        probe = f"{current}{ch}"
        width = pdfmetrics.stringWidth(probe, font_name, font_size)
        if width <= max_width:
            current = probe
            continue
        if current:
            out.append(current)
            current = ch
        else:
            out.append(ch)
            current = ""
    if current:
        out.append(current)
    return out or [src]


def _pdf_report_bytes(lines: list[str], *, watermark: str, trust_ok: bool) -> bytes:
    if not _HAS_REPORTLAB:
        return _pdf_report_bytes_legacy(lines, watermark=watermark, trust_ok=trust_ok)

    try:
        font_name = _register_pdf_font()
    except Exception:
        return _pdf_report_bytes_legacy(lines, watermark=watermark, trust_ok=trust_ok)

    buf = io.BytesIO()
    w, h = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("QCSpec Data Sovereignty Report")

    # top-right watermark
    c.setFont(font_name, 11)
    c.setFillColor(Color(0.15, 0.62, 0.37) if trust_ok else Color(0.78, 0.18, 0.24))
    c.drawRightString(w - 36, h - 36, watermark)

    c.setFillColor(Color(0, 0, 0))
    text_font_size = 16
    body_font_size = 11
    left = 48
    top = h - 78
    max_width = w - 2 * left

    c.setFont(font_name, text_font_size)
    c.drawString(left, top, _to_text(lines[0] if lines else "QCSpec Data Sovereignty Report"))

    y = top - 30
    c.setFont(font_name, body_font_size)
    for line in lines[1:]:
        wrapped = _wrap_line(line, font_name=font_name, font_size=body_font_size, max_width=max_width)
        for sub in wrapped:
            if y < 50:
                c.showPage()
                c.setFont(font_name, body_font_size)
                y = h - 56
            c.drawString(left, y, _to_text(sub))
            y -= 20

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


def _spec_snapshot_bundle(verify_detail: dict[str, Any]) -> dict[str, Any]:
    summary = verify_detail.get("summary") if isinstance(verify_detail.get("summary"), dict) else {}
    timeline = verify_detail.get("timeline") if isinstance(verify_detail.get("timeline"), list) else []
    qcgate = verify_detail.get("qcgate") if isinstance(verify_detail.get("qcgate"), dict) else {}

    specs: list[dict[str, str]] = []
    seen: set[str] = set()

    def push(uri: Any, excerpt: Any):
        u = _to_text(uri).strip()
        e = _clean_no_qmark(excerpt, fallback="")
        key = f"{u}|{e}"
        if not u and not e:
            return
        if key in seen:
            return
        seen.add(key)
        specs.append({"spec_uri": u, "snapshot_text": e})

    push(summary.get("spec_uri"), _first_rule_spec_excerpt(verify_detail) or summary.get("spec_snapshot"))
    for node in timeline:
        if isinstance(node, dict):
            push(node.get("spec_uri"), node.get("spec_excerpt"))
    for rule in qcgate.get("rules") if isinstance(qcgate.get("rules"), list) else []:
        if isinstance(rule, dict):
            push(rule.get("spec_uri"), rule.get("spec_excerpt"))

    primary_text = _first_rule_spec_excerpt(verify_detail) or _to_text(summary.get("spec_snapshot"))
    primary_text = _clean_no_qmark(primary_text, fallback="无可用规范摘要")
    return {
        "primary_spec_uri": _to_text(summary.get("spec_uri")),
        "primary_snapshot_text": primary_text,
        "spec_snapshots": specs,
    }


def _fetch_binary(url: str, timeout: float = 10.0) -> bytes | None:
    target = _to_text(url).strip()
    if not target or not (target.startswith("http://") or target.startswith("https://")):
        return None
    req = urlrequest.Request(
        target,
        method="GET",
        headers={"User-Agent": "QCSpec-DSP/1.0"},
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def _offline_snapshot_html(dsp_payload: dict[str, Any]) -> str:
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
      <div class="title">QCSpec DSP 离线验证</div>
      <button id="theme-btn" class="toggle" type="button">切换亮/暗</button>
    </div>
    <div class="card">
      <div class="status">
        <span id="hash-badge" class="badge warn">Hash 校验中...</span>
        <span id="trust-badge" class="badge warn">主权状态待判定</span>
      </div>
    </div>
    <div class="card grid">
      <div class="k">Proof ID</div><div class="v" id="proof-id">-</div>
      <div class="k">业务结论</div><div class="v" id="result-cn">-</div>
      <div class="k">签署人</div><div class="v" id="signed-by">-</div>
      <div class="k">签署时间</div><div class="v" id="signed-at">-</div>
      <div class="k">归档时间</div><div class="v" id="archive-at">-</div>
      <div class="k">规范地址</div><div class="v" id="spec-uri">-</div>
      <div class="k">规范摘要</div><div class="v" id="spec-snapshot">-</div>
      <div class="k">提供哈希</div><div class="v" id="provided-hash">-</div>
      <div class="k">重算哈希</div><div class="v" id="computed-hash">-</div>
    </div>
    <div class="card">
      <div class="k" style="margin-bottom:8px;">证据清单</div>
      <table>
        <thead><tr><th>#</th><th>文件</th><th>SHA-256</th><th>状态</th></tr></thead>
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
        tbody.innerHTML = '<tr><td colspan=\"4\">无关联证据</td></tr>';
      }} else {{
        tbody.innerHTML = evidence.map((it, idx) => `<tr><td>${{idx+1}}</td><td>${{it.file_name || '-'}}</td><td>${{it.evidence_hash || it.downloaded_sha256 || '-'}}</td><td>${{it.status || '-'}}</td></tr>`).join('');
      }}

      const hashBadge = document.getElementById('hash-badge');
      if (!expected || !source || !window.crypto?.subtle) {{
        hashBadge.textContent = 'Hash 校验不可用';
        hashBadge.className = 'badge warn';
      }} else {{
        try {{
          const computed = await sha256Hex(source);
          document.getElementById('computed-hash').textContent = computed;
          const ok = computed.toLowerCase() === expected;
          hashBadge.textContent = ok ? 'Hash 校验通过' : 'Hash 校验失败';
          hashBadge.className = 'badge ' + (ok ? 'ok' : 'bad');
        }} catch (err) {{
          hashBadge.textContent = 'Hash 校验异常';
          hashBadge.className = 'badge bad';
        }}
      }}

      const trust = document.getElementById('trust-badge');
      const trustOk = Boolean(hv.matches);
      trust.textContent = trustOk ? '可信来源' : '疑似篡改';
      trust.className = 'badge ' + (trustOk ? 'ok' : 'bad');
    }})();
  </script>
</body>
</html>"""


def _pdf_html_template() -> str:
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
    {% if verify_detail.hash_verification.matches %}<span class="ok">可信来源</span>{% else %}<span class="bad">疑似篡改</span>{% endif %}
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


def create_dsp_package(
    *,
    proof_id: str,
    verify_detail: dict[str, Any],
    chain_fingerprints: list[dict[str, Any]],
    signer_certificate: dict[str, str],
) -> bytes:
    summary = verify_detail.get("summary") if isinstance(verify_detail.get("summary"), dict) else {}
    sovereignty = verify_detail.get("sovereignty") if isinstance(verify_detail.get("sovereignty"), dict) else {}
    person = verify_detail.get("person") if isinstance(verify_detail.get("person"), dict) else {}
    evidence = verify_detail.get("evidence") if isinstance(verify_detail.get("evidence"), list) else []
    evidence_manifest: list[dict[str, Any]] = []
    evidence_files: list[tuple[str, bytes]] = []
    for idx, item in enumerate(evidence):
        if not isinstance(item, dict):
            continue
        url = _to_text(item.get("url")).strip()
        file_name = _safe_file_name(_to_text(item.get("file_name")), f"evidence_{idx + 1}.bin")
        blob = _fetch_binary(url)
        if blob is None:
            evidence_manifest.append(
                {
                    "index": idx + 1,
                    "file_name": file_name,
                    "source_url": url,
                    "status": "unavailable",
                    "reason": "download_failed_or_non_http_url",
                    "evidence_hash": _to_text(item.get("evidence_hash")),
                }
            )
            continue
        ext = ""
        guessed = mimetypes.guess_extension(_to_text(item.get("content_type")))
        if guessed:
            ext = guessed
        if "." not in file_name and ext:
            file_name = f"{file_name}{ext}"
        evidence_manifest.append(
            {
                "index": idx + 1,
                "file_name": file_name,
                "source_url": url,
                "status": "ok",
                "downloaded_sha256": hashlib.sha256(blob).hexdigest(),
                "size": len(blob),
                "evidence_hash": _to_text(item.get("evidence_hash")) or hashlib.sha256(blob).hexdigest(),
                "proof_id": _to_text(item.get("proof_id")),
            }
        )
        evidence_files.append((f"evidence/{file_name}", blob))

    result_cn = _result_cn_from_summary(summary)
    signed_by = _signer_from_payload(sovereignty, person)
    signed_at = _clean_no_qmark(_to_text(sovereignty.get("signed_at") or person.get("time")), fallback="-")
    spec_bundle = _spec_snapshot_bundle(verify_detail)
    spec_snapshot = _clean_no_qmark(spec_bundle.get("primary_snapshot_text"), fallback="无可用规范摘要")
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    matches = bool((verify_detail.get("hash_verification") or {}).get("matches"))
    trust_label = "可信来源" if matches else "疑似篡改"
    evidence_count = len(evidence_manifest) if evidence_manifest else len(evidence)

    report_lines = [
        f"QCSpec Data Sovereignty Report [{trust_label}]",
        f"Proof ID: {_to_text(verify_detail.get('proof_id') or proof_id)}",
        f"Proof Hash: {_to_text(sovereignty.get('proof_hash') or '-')}",
        f"Business Result (CN): {_clean_no_qmark(result_cn, fallback='待判定')}",
        f"Signer: {signed_by}",
        f"Signed At: {signed_at}",
        f"Archive At: {generated_at}",
        f"Spec URI: {_to_text(summary.get('spec_uri') or '-')}",
        f"Spec Snapshot: {spec_snapshot}",
        f"GitPeg Anchor: {_to_text(sovereignty.get('gitpeg_anchor') or '-')}",
        f"Block Height: {SOVEREIGN_BLOCK_HEIGHT}",
        f"Evidence Count: {evidence_count}",
        "Issued by verify.qcspec.com",
    ]
    pdf_bytes = _pdf_report_bytes(
        report_lines,
        watermark=f"{trust_label} | block {SOVEREIGN_BLOCK_HEIGHT}",
        trust_ok=matches,
    )

    verify_detail_aligned = json.loads(json.dumps(verify_detail, ensure_ascii=False, default=str))
    if not isinstance(verify_detail_aligned.get("summary"), dict):
        verify_detail_aligned["summary"] = {}
    if not isinstance(verify_detail_aligned.get("sovereignty"), dict):
        verify_detail_aligned["sovereignty"] = {}
    if not isinstance(verify_detail_aligned.get("qcgate"), dict):
        verify_detail_aligned["qcgate"] = {}
    if not isinstance(verify_detail_aligned.get("qcgate").get("rules"), list):
        verify_detail_aligned["qcgate"]["rules"] = []
    if not verify_detail_aligned["qcgate"]["rules"]:
        verify_detail_aligned["qcgate"]["rules"].append({})
    if not isinstance(verify_detail_aligned["qcgate"]["rules"][0], dict):
        verify_detail_aligned["qcgate"]["rules"][0] = {}

    verify_detail_aligned["summary"]["result_cn"] = _clean_no_qmark(result_cn, fallback="待判定")
    verify_detail_aligned["summary"]["spec_snapshot"] = spec_snapshot
    verify_detail_aligned["sovereignty"]["signed_by"] = signed_by
    verify_detail_aligned["sovereignty"]["signed_at"] = signed_at
    verify_detail_aligned["qcgate"]["rules"][0]["spec_excerpt"] = spec_snapshot

    dsp_json = {
        "proof_id": _to_text(verify_detail.get("proof_id") or proof_id),
        "generated_at": generated_at,
        "verify_detail": verify_detail_aligned,
        "proof_chain": chain_fingerprints,
        "spec_snapshot_bundle": spec_bundle,
        "signer_certificate": signer_certificate,
        "sovereign_watermark": {
            "label": trust_label,
            "block_height": SOVEREIGN_BLOCK_HEIGHT,
            "hash_matches": matches,
        },
        "evidence": {
            "count": evidence_count,
            "items": evidence_manifest,
        },
    }
    dsp_json["package_hash"] = hashlib.sha256(
        json.dumps(dsp_json, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    verify_snapshot_html = _offline_snapshot_html(dsp_json)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.pdf", pdf_bytes)
        # Backward-compatible alias for legacy consumers.
        zf.writestr("verify_snapshot.pdf", pdf_bytes)
        payload_json = json.dumps(dsp_json, ensure_ascii=False, sort_keys=True, indent=2, default=str)
        zf.writestr("provenance_chain.json", payload_json)
        # Compatibility alias for old consumers.
        zf.writestr("proof_chain.json", payload_json)
        zf.writestr("index.html", verify_snapshot_html)
        zf.writestr("verify_snapshot.html", verify_snapshot_html)
        # Backward-compatible alias for legacy consumers.
        zf.writestr("verify_offline.html", verify_snapshot_html)
        zf.writestr("templates/report_template.html", _pdf_html_template())
        zf.writestr("signer_certificate.pem", _to_text(signer_certificate.get("public_key_pem")))
        zf.writestr(
            "evidence/manifest.json",
            json.dumps(evidence_manifest, ensure_ascii=False, sort_keys=True, indent=2, default=str),
        )
        for path, blob in evidence_files:
            zf.writestr(path, blob)
        zf.writestr(
            "README.txt",
            "DSP includes report.pdf, provenance_chain.json, verify_snapshot.html, signer_certificate.pem, evidence/.\n",
        )

    buf.seek(0)
    return buf.read()
