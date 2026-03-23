"""
QCSpec · v:// 主权报告引擎
Version Control for the Physical World

三层闭环：
  1. 从 v:// 节点拉配置（PegConfig协议）
  2. 渲染报告时嵌入 v:// 信息 + Proof Hash
  3. 生成后自动注册为 v:// 子节点（ProofIR闭环）

用法：
  python3 report_engine.py --uri v://cn.中北/project/G312/ --demo
  python3 report_engine.py --uri v://cn.中北/project/G312/ --data data.json
"""

import os
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────
# docxtpl渲染（核心依赖）
# ─────────────────────────────────────────────
try:
    from docxtpl import DocxTemplate, RichText
    DOCXTPL_OK = True
except ImportError:
    DOCXTPL_OK = False
    print("⚠ docxtpl未安装，将生成CSV格式报告（降级模式）")

# ─────────────────────────────────────────────
# v:// 节点注册表（本地模拟，后期替换为Supabase）
# ─────────────────────────────────────────────
V_NODE_REGISTRY_PATH = Path("/home/claude/qcspec/v_nodes/registry.json")

def load_registry() -> dict:
    if V_NODE_REGISTRY_PATH.exists():
        return json.loads(V_NODE_REGISTRY_PATH.read_text(encoding='utf-8'))
    return {"nodes": {}, "proofs": []}

def save_registry(reg: dict):
    V_NODE_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    V_NODE_REGISTRY_PATH.write_text(
        json.dumps(reg, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

# ─────────────────────────────────────────────
# STEP 1: 从 v:// 节点拉取配置（PegConfig协议）
# ─────────────────────────────────────────────
def fetch_v_config(v_uri: str) -> dict:
    """
    从 v:// 节点拉取配置。
    生产环境替换为：
        requests.get(f"https://api.gitpeg.dev/v1/config/{encode(v_uri)}", ...)
    当前为本地注册表模拟。
    """
    reg = load_registry()
    node = reg["nodes"].get(v_uri, {})

    # 如果节点不存在，返回默认配置（首次使用时自动初始化）
    if not node:
        print(f"  ℹ 节点 {v_uri} 未注册，使用默认配置（首次使用自动初始化）")
        node = _default_node_config(v_uri)
        reg["nodes"][v_uri] = node
        save_registry(reg)

    print(f"  ✓ 已从 {v_uri} 拉取配置：{len(node)} 个字段")
    return node


def _default_node_config(v_uri: str) -> dict:
    """根据v://地址自动推断默认配置"""
    parts = v_uri.replace("v://", "").strip("/").split("/")
    org   = parts[0] if parts else "cn.企业"
    proj  = parts[2] if len(parts) > 2 else "未命名项目"
    return {
        "uri":              v_uri,
        "org":              org,
        "project_name":     proj,
        "inspector_name":   "待填写",
        "project_manager":  "待填写",
        "supervisor_name":  "中北工程设计咨询有限公司",
        "supervisor_engineer": "待填写",
        "contract_no":      "待填写",
        "template_path":    "templates/qc_report_template.docx",
        "output_dir":       "reports",
        "dto_role":         "AI",
        "permissions": {
            "can_write_proof": True,
            "can_seal":        False,
            "can_settle":      False,
        },
        "registered_at":    datetime.now().isoformat(),
    }


def register_node(v_uri: str, config: dict):
    """注册或更新 v:// 节点配置"""
    reg = load_registry()
    reg["nodes"][v_uri] = {**config, "uri": v_uri, "updated_at": datetime.now().isoformat()}
    save_registry(reg)
    print(f"  ✓ 节点已注册/更新：{v_uri}")


# ─────────────────────────────────────────────
# STEP 2: 生成 Proof Hash（ProofIR协议）
# ─────────────────────────────────────────────
def generate_proof(v_uri: str, content: dict) -> str:
    """
    生成 Proof Hash，模拟 GitPeg ProofIR 协议。
    生产环境替换为：
        POST https://api.gitpeg.dev/v1/proof/commit
    """
    payload = json.dumps({
        "uri":       v_uri,
        "content":   content,
        "timestamp": datetime.now().isoformat(),
    }, ensure_ascii=False, sort_keys=True)
    hash_val = hashlib.sha256(payload.encode()).hexdigest()[:16].upper()
    proof_id = f"GP-PROOF-{hash_val}"

    # 写入本地Proof链
    reg = load_registry()
    reg["proofs"].append({
        "proof_id":  proof_id,
        "uri":       v_uri,
        "hash":      hash_val,
        "timestamp": datetime.now().isoformat(),
        "summary":   f"质检报告生成 · {content.get('report_no','?')}",
    })
    save_registry(reg)
    print(f"  ✓ Proof已生成：{proof_id}")
    return proof_id


# ─────────────────────────────────────────────
# 辅助：构造报告上下文
# ─────────────────────────────────────────────
RESULT_LABELS = {"pass": "✓ 合格", "warn": "⚠ 观察", "fail": "✗ 不合格"}
TYPE_NAMES = {
    "flatness":      "路面平整度",
    "crack":         "裂缝宽度",
    "rut":           "车辙深度",
    "slope":         "横坡坡度",
    "settlement":    "路基沉降",
    "bearing":       "路基承载力",
    "compaction":    "压实度",
    "bridge_crack":  "桥梁裂缝",
    "bridge_deflect":"挠度",
    "bridge_erosion":"混凝土碳化",
}


def build_context(gate_data: dict, v_config: dict, proof_id: str) -> dict:
    records = gate_data.get("records", [])
    photos  = gate_data.get("photos", [])

    # 统计
    total   = len(records)
    passed  = sum(1 for r in records if r.get("result") == "pass")
    failed  = sum(1 for r in records if r.get("result") == "fail")
    warned  = sum(1 for r in records if r.get("result") == "warn")
    rate    = round(passed / total * 100, 1) if total else 0

    # 结论文本
    if failed == 0 and warned == 0:
        conclusion = "✓ 全部合格 — 本次检测所有项目均符合规范要求"
    elif failed == 0:
        conclusion = f"⚠ 基本合格 — {warned}项需持续观察，建议跟踪复测"
    else:
        conclusion = f"✗ 存在不合格项 — {failed}项不合格，必须整改后复测"

    fail_items = "；".join(
        f"{r.get('type_name', TYPE_NAMES.get(r.get('type',''),'?'))}（{r.get('location','?')}）"
        for r in records if r.get("result") == "fail"
    ) or "无"

    suggestions = gate_data.get("suggestions", "请按照相关规范要求及时整改不合格项，完成整改后申请复测。")

    # 照片列表（最多6张，3×2布局）
    photo_ctx = []
    for i, p in enumerate(photos[:6]):
        photo_ctx.append({
            "index":   i + 1,
            "caption": f"照片{i+1}·{p.get('location','?')}·{p.get('time','?')}",
            "path":    p.get("path", ""),
        })

    # 检测数据行
    items_ctx = []
    for i, r in enumerate(records):
        items_ctx.append({
            "index":        i + 1,
            "location":     r.get("location", "?"),
            "type_name":    r.get("type_name", TYPE_NAMES.get(r.get("type",""), r.get("type","?"))),
            "value":        str(r.get("value", "?")),
            "standard":     str(r.get("standard", "?")),
            "unit":         r.get("unit", ""),
            "result":       r.get("result", "?"),
            "result_text":  RESULT_LABELS.get(r.get("result",""), r.get("result","?")),
            "person":       r.get("person", ""),
            "remark":       r.get("remark", ""),
        })

    now = datetime.now()
    report_no = f"QC-{now.strftime('%Y%m%d%H%M%S')}"

    return {
        # 报告元数据
        "report_no":      report_no,
        "report_date":    now.strftime("%Y年%m月%d日"),
        "generated_at":   now.strftime("%Y-%m-%d %H:%M:%S"),

        # 项目信息（来自 v:// 节点配置）
        "project_name":        v_config.get("project_name", "?"),
        "contract_no":         v_config.get("contract_no", "?"),
        "inspector":           v_config.get("inspector_name", "?"),
        "project_manager":     v_config.get("project_manager", "?"),
        "supervisor":          v_config.get("supervisor_name", "?"),
        "supervisor_engineer": v_config.get("supervisor_engineer", "?"),

        # 检测范围
        "location":         gate_data.get("location", "?"),
        "inspection_type":  "、".join(set(
            TYPE_NAMES.get(r.get("type",""), r.get("type","?")) for r in records
        )) or "综合检测",

        # v:// 主权标识（核心！）
        "v_identity":  v_config.get("uri", "?"),
        "proof_hash":  proof_id,
        "seal_status": "✓ 已由 v:// 节点授权" if v_config.get("permissions", {}).get("can_seal") else "⏳ 待监理Seal签署",

        # 数据统计
        "total_records": total,
        "pass_count":    passed,
        "fail_count":    failed,
        "warn_count":    warned,
        "pass_rate":     rate,

        # 数据明细（docxtpl循环）
        "items":       items_ctx,
        "loop":        items_ctx,  # 兼容 {{loop.index}}

        # 照片
        "photos":      photo_ctx,
        "photo_count": len(photos),
        "photo_path":  f"{v_config.get('uri','?')}/photos/",
        "photo_location": gate_data.get("location", "?"),

        # 结论
        "conclusion":   conclusion,
        "fail_items":   fail_items,
        "suggestions":  suggestions,
    }


# ─────────────────────────────────────────────
# STEP 2: 渲染报告（docxtpl）
# ─────────────────────────────────────────────
def render_report(context: dict, v_config: dict) -> str:
    """渲染Word报告，返回输出路径"""
    tpl_path = v_config.get("template_path", "templates/qc_report_template.docx")
    out_dir  = Path(v_config.get("output_dir", "reports"))
    out_dir.mkdir(parents=True, exist_ok=True)

    report_no = context["report_no"]
    location  = context["location"].replace("+", "").replace("/", "_")
    out_name  = f"质检报告_{location}_{report_no}.docx"
    out_path  = out_dir / out_name

    if DOCXTPL_OK and Path(tpl_path).exists():
        doc = DocxTemplate(tpl_path)

        # 处理 items 循环（docxtpl jinja2语法）
        # 重新构造context，用标准jinja2格式
        render_ctx = dict(context)

        # Rich text for result_text（带颜色）
        colored_items = []
        for item in context.get("items", []):
            item = dict(item)
            result = item.get("result", "pass")
            rt = RichText()
            if result == "pass":
                rt.add(item["result_text"], color="#059669", bold=True)
            elif result == "fail":
                rt.add(item["result_text"], color="#DC2626", bold=True)
            else:
                rt.add(item["result_text"], color="#D97706", bold=True)
            item["result_rt"] = rt
            colored_items.append(item)
        render_ctx["items"] = colored_items

        doc.render(render_ctx)
        doc.save(str(out_path))
        print(f"  ✓ Word报告已生成：{out_path}")
    else:
        # 降级：生成CSV + TXT摘要
        out_path = out_dir / out_name.replace(".docx", "_summary.txt")
        _render_txt_fallback(context, out_path)
        print(f"  ✓ TXT摘要已生成（降级模式）：{out_path}")

    return str(out_path)


def _render_txt_fallback(ctx: dict, out_path: Path):
    """无Word模板时的降级输出"""
    lines = [
        "=" * 60,
        "QCSpec 工程质量检验内页报告",
        f"v:// 主权存证 · {ctx['v_identity']}",
        "=" * 60,
        f"报告编号：{ctx['report_no']}",
        f"报告日期：{ctx['report_date']}",
        f"项目名称：{ctx['project_name']}",
        f"合同编号：{ctx['contract_no']}",
        f"检测桩号：{ctx['location']}",
        f"检测人员：{ctx['inspector']}",
        f"监理单位：{ctx['supervisor']}",
        "",
        f"v:// 节点：{ctx['v_identity']}",
        f"Proof Hash：{ctx['proof_hash']}",
        f"Seal状态：{ctx['seal_status']}",
        "",
        "─" * 60,
        "检测数据明细",
        "─" * 60,
        f"{'序号':<4} {'位置':<12} {'项目':<12} {'实测值':<10} {'标准值':<10} {'结果':<8}",
        "─" * 60,
    ]
    for item in ctx.get("items", []):
        lines.append(
            f"{item['index']:<4} {item['location']:<12} {item['type_name']:<12} "
            f"{item['value']}{item['unit']:<10} {item['standard']}{item['unit']:<10} {item['result_text']:<8}"
        )
    lines += [
        "─" * 60,
        f"合计：{ctx['total_records']}条  合格率：{ctx['pass_rate']}%  "
        f"合格:{ctx['pass_count']} 观察:{ctx['warn_count']} 不合格:{ctx['fail_count']}",
        "",
        "检测结论",
        "─" * 60,
        ctx['conclusion'],
        f"不合格项：{ctx['fail_items']}",
        f"整改建议：{ctx['suggestions']}",
        "",
        "─" * 60,
        f"生成时间：{ctx['generated_at']}",
        f"QCSpec · qcspec.com · v:// Proof: {ctx['proof_hash']}",
        "=" * 60,
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─────────────────────────────────────────────
# STEP 3: 报告注册为 v:// 子节点（ProofIR闭环）
# ─────────────────────────────────────────────
def register_report_node(parent_uri: str, report_path: str, context: dict, proof_id: str):
    """
    将生成的报告注册为 v:// 子节点。
    生产环境替换为：
        POST https://api.gitpeg.dev/v1/nodes/register
    """
    report_uri = f"{parent_uri.rstrip('/')}/reports/{context['report_no']}/"
    node = {
        "uri":         report_uri,
        "parent_uri":  parent_uri,
        "type":        "QCReport",
        "report_no":   context["report_no"],
        "report_date": context["report_date"],
        "file_path":   report_path,
        "proof_id":    proof_id,
        "location":    context.get("location", "?"),
        "pass_rate":   context.get("pass_rate", 0),
        "total":       context.get("total_records", 0),
        "created_at":  datetime.now().isoformat(),
        "status":      "active",
        "peg_version": "v1.0",
    }
    reg = load_registry()
    reg["nodes"][report_uri] = node
    save_registry(reg)
    print(f"  ✓ 报告已注册为v://子节点：{report_uri}")
    return report_uri


# ─────────────────────────────────────────────
# 主入口：完整三层闭环
# ─────────────────────────────────────────────
def generate_report(v_uri: str, gate_data: dict, verbose: bool = True) -> dict:
    """
    v:// 驱动的报告生成完整闭环。

    Args:
        v_uri:      项目的 v:// 主权地址，例如 v://cn.中北/project/G312/
        gate_data:  质检数据，结构见 demo_gate_data()
        verbose:    是否打印详细日志

    Returns:
        {
            report_uri:   生成的报告v://地址,
            report_path:  本地文件路径,
            proof_id:     Proof Hash,
            context:      完整渲染上下文,
        }
    """
    sep = "─" * 50
    print(f"\n{sep}")
    print(f"🚀 QCSpec v:// 报告引擎启动")
    print(f"   节点：{v_uri}")
    print(sep)

    # ── Step 1：拉取 v:// 节点配置 ──
    print("\n[1/3] 从 v:// 节点拉取配置（PegConfig协议）")
    v_config = fetch_v_config(v_uri)

    # ── Step 2：生成 Proof ──
    print("\n[2/3] 生成 Proof Hash（ProofIR协议）")
    proof_id = generate_proof(v_uri, gate_data)

    # ── Step 2b：构造渲染上下文 ──
    context = build_context(gate_data, v_config, proof_id)

    # ── Step 2c：渲染报告 ──
    print("\n[2/3] 渲染报告（docxtpl引擎）")
    report_path = render_report(context, v_config)

    # ── Step 3：注册为 v:// 子节点 ──
    print("\n[3/3] 注册报告为 v:// 子节点（ProofIR闭环）")
    report_uri = register_report_node(v_uri, report_path, context, proof_id)

    print(f"\n{sep}")
    print(f"✅ 三层闭环完成")
    print(f"   📄 报告文件：{report_path}")
    print(f"   🔗 v:// 节点：{report_uri}")
    print(f"   🔒 Proof：{proof_id}")
    print(f"   📊 合格率：{context['pass_rate']}%  "
          f"({context['pass_count']}合格 / {context['warn_count']}观察 / {context['fail_count']}不合格)")
    print(sep)

    return {
        "report_uri":  report_uri,
        "report_path": report_path,
        "proof_id":    proof_id,
        "context":     context,
    }


# ─────────────────────────────────────────────
# 演示数据（真实结构）
# ─────────────────────────────────────────────
def demo_gate_data() -> dict:
    return {
        "location":    "K50+200",
        "suggestions": "K49+200处裂缝宽度0.25mm超标，建议采用灌缝材料进行修补处理，修补后复测。",
        "records": [
            {"type":"flatness",   "location":"K48+500", "value":1.8,  "standard":2.0, "unit":"m/km", "result":"pass",  "person":"张工", "remark":"状况良好"},
            {"type":"crack",      "location":"K49+200", "value":0.25, "standard":0.2, "unit":"mm",   "result":"warn",  "person":"李工", "remark":"细微裂缝，需观察"},
            {"type":"compaction", "location":"K50+100", "value":97.2, "standard":96,  "unit":"%",    "result":"pass",  "person":"王工", "remark":""},
            {"type":"settlement", "location":"K50+200", "value":35,   "standard":30,  "unit":"mm",   "result":"fail",  "person":"张工", "remark":"沉降超标，建议立即处理"},
            {"type":"rut",        "location":"K51+000", "value":12,   "standard":20,  "unit":"mm",   "result":"pass",  "person":"李工", "remark":""},
            {"type":"crack",      "location":"K52+300", "value":0.15, "standard":0.2, "unit":"mm",   "result":"pass",  "person":"王工", "remark":""},
        ],
        "photos": [
            {"path":"photos/K48500_001.jpg", "location":"K48+500", "time":"09:30"},
            {"path":"photos/K49200_crack.jpg","location":"K49+200","time":"10:15"},
            {"path":"photos/K50200_settle.jpg","location":"K50+200","time":"14:30"},
        ],
    }


# ─────────────────────────────────────────────
# v:// 节点查看器
# ─────────────────────────────────────────────
def show_node_tree():
    reg = load_registry()
    print("\n📊 v:// 节点注册表")
    print("─" * 60)
    nodes = reg.get("nodes", {})
    proofs = reg.get("proofs", [])
    if not nodes:
        print("  （空）")
    else:
        for uri, node in nodes.items():
            node_type = node.get("type", "Config")
            status = "●" if node.get("status","active") == "active" else "○"
            print(f"  {status} {uri}")
            if node_type == "QCReport":
                print(f"    └─ 报告编号: {node.get('report_no')}  "
                      f"合格率: {node.get('pass_rate')}%  "
                      f"Proof: {node.get('proof_id')}")
    print(f"\n📋 Proof链：{len(proofs)}条记录")
    for p in proofs[-5:]:
        print(f"  {p['proof_id']}  {p['timestamp'][:16]}  {p['summary']}")
    print("─" * 60)


# ─────────────────────────────────────────────
# CLI入口
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="QCSpec v:// 主权报告引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 report_engine.py --demo
  python3 report_engine.py --uri v://cn.中北/project/G312/ --demo
  python3 report_engine.py --uri v://cn.中北/project/G312/ --data records.json
  python3 report_engine.py --tree
  python3 report_engine.py --register v://cn.中北/project/G312/ --config '{"inspector_name":"张工"}'
        """
    )
    parser.add_argument('--uri',      default="v://cn.中北/project/G312/", help="v:// 项目节点地址")
    parser.add_argument('--demo',     action='store_true', help="使用演示数据生成报告")
    parser.add_argument('--data',     help="质检数据JSON文件路径")
    parser.add_argument('--tree',     action='store_true', help="显示 v:// 节点树")
    parser.add_argument('--register', help="注册/更新节点配置")
    parser.add_argument('--config',   help="节点配置JSON（配合--register使用）")
    args = parser.parse_args()

    os.chdir("/home/claude/qcspec")

    if args.tree:
        show_node_tree()
        return

    if args.register:
        config = json.loads(args.config) if args.config else {}
        register_node(args.register, config)
        return

    if args.demo:
        gate_data = demo_gate_data()
    elif args.data:
        gate_data = json.loads(Path(args.data).read_text(encoding='utf-8'))
    else:
        print("请使用 --demo 或 --data <file> 提供质检数据")
        print("示例：python3 report_engine.py --demo")
        return

    result = generate_report(args.uri, gate_data)
    return result


if __name__ == "__main__":
    main()
