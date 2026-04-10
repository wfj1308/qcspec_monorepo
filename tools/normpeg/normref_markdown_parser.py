from __future__ import annotations

import argparse
from datetime import date
import json
import re
from pathlib import Path
from typing import Any


TITLE_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
SOURCE_RE = re.compile(r"^\*\*规范来源\*\*[：:]\s*(?P<source>.+?)\s*$")
SECTION_RE = re.compile(r"^##\s+(?P<section>.+?)\s*$")
RULE_HEADING_RE = re.compile(r"^###\s*(?:\d+\.\s*)?(?P<title>.+?)\s*$")
BULLET_META_RE = re.compile(r"^-\s*\*\*(?P<key>.+?)\*\*[：:]\s*(?P<value>.*)$")

OPERATOR_MAP = {
    ">=": "gte",
    "<=": "lte",
    ">": "gt",
    "<": "lt",
    "==": "eq",
    "!=": "neq",
}

NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
EXPR_WITH_OP_RE = re.compile(r"^(?P<lhs>.+?)\s*(?P<op>>=|<=|==|!=|>|<)\s*(?P<rhs>.+)$")
EXPR_PREFIX_OP_RE = re.compile(r"^(?P<op>>=|<=|==|!=|>|<)\s*(?P<rhs>.+)$")


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "_", lowered)
    return lowered.strip("_") or "rule"


def parse_literal(raw: str) -> tuple[bool, Any]:
    value = raw.strip()
    if value.lower() == "true":
        return True, True
    if value.lower() == "false":
        return True, False
    if NUMBER_RE.match(value):
        if "." in value:
            return True, float(value)
        return True, int(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return True, value[1:-1]
    return False, value


def parse_rule_expression(rule_expr: str, field: str) -> dict[str, Any]:
    text = (rule_expr or "").strip()
    if not text:
        return {"operator": "eq", "value_expr": ""}

    prefix_match = EXPR_PREFIX_OP_RE.match(text)
    if prefix_match:
        op = prefix_match.group("op")
        rhs = prefix_match.group("rhs").strip()
        return build_condition(op=op, rhs=rhs)

    expr_match = EXPR_WITH_OP_RE.match(text)
    if expr_match:
        lhs = expr_match.group("lhs").strip()
        op = expr_match.group("op")
        rhs = expr_match.group("rhs").strip()
        if not lhs or (field and lhs == field):
            return build_condition(op=op, rhs=rhs)
        return build_condition(op=op, rhs=rhs)

    has_literal, parsed = parse_literal(text)
    if has_literal:
        return {"operator": "eq", "value": parsed}
    return {"operator": "eq", "value_expr": text}


def build_condition(op: str, rhs: str) -> dict[str, Any]:
    result: dict[str, Any] = {"operator": OPERATOR_MAP.get(op, "eq")}
    has_literal, parsed = parse_literal(rhs)
    if has_literal:
        result["value"] = parsed
    else:
        result["value_expr"] = rhs
    return result


def normalize_meta_key(key: str) -> str:
    compact = key.strip().lower().replace(" ", "")
    compact = compact.replace("（", "(").replace("）", ")")
    mapping = {
        "字段": "field",
        "规则": "rule_expr",
        "单位": "unit",
        "严重程度": "severity",
        "失败提示": "fail_message",
        "不通过提示": "fail_message",
        "规则id": "rule_id",
        "规则编号": "rule_id",
    }
    return mapping.get(compact, key.strip())


def parse_markdown(content: str) -> dict[str, Any]:
    title = ""
    source = ""
    in_gate_rules = False
    current_rule: dict[str, Any] | None = None
    raw_rules: list[dict[str, Any]] = []

    for raw_line in content.splitlines():
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue

        title_match = TITLE_RE.match(line)
        if title_match and not title:
            title = title_match.group("title").strip()
            continue

        source_match = SOURCE_RE.match(line)
        if source_match and not source:
            source = source_match.group("source").strip()
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            section_name = section_match.group("section").strip()
            if section_name == "Gate 规则":
                in_gate_rules = True
                continue
            if in_gate_rules:
                in_gate_rules = False
                if current_rule:
                    raw_rules.append(current_rule)
                    current_rule = None
            continue

        if not in_gate_rules:
            continue

        rule_heading = RULE_HEADING_RE.match(line)
        if rule_heading:
            if current_rule:
                raw_rules.append(current_rule)
            current_rule = {"title": rule_heading.group("title").strip()}
            continue

        bullet_match = BULLET_META_RE.match(line)
        if bullet_match and current_rule is not None:
            key = normalize_meta_key(bullet_match.group("key"))
            value = bullet_match.group("value").strip()
            current_rule[key] = value

    if current_rule:
        raw_rules.append(current_rule)

    parsed_rules: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rules, start=1):
        field = str(row.get("field") or "").strip()
        rule_expr = str(row.get("rule_expr") or "").strip()
        condition = parse_rule_expression(rule_expr=rule_expr, field=field)
        rule_id = str(row.get("rule_id") or "").strip()
        if not rule_id:
            rule_id = f"normref.{slugify(field or row.get('title', f'rule_{index}'))}"

        parsed: dict[str, Any] = {
            "rule_id": rule_id,
            "field": field,
            **condition,
        }
        unit = str(row.get("unit") or "").strip()
        if unit:
            parsed["unit"] = unit
        severity = str(row.get("severity") or "").strip()
        if severity:
            parsed["severity"] = severity
        fail_message = str(row.get("fail_message") or "").strip()
        if fail_message:
            parsed["fail_message"] = fail_message
        parsed_rules.append(parsed)

    return {
        "name": title or "未命名规范",
        "source": source,
        "rules": parsed_rules,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse NormRef markdown into executable JSON rules.")
    parser.add_argument("--input", required=True, help="Input markdown path.")
    parser.add_argument("--output", help="Output JSON path. Defaults to input with .json extension.")
    parser.add_argument(
        "--normref-id",
        help="Explicit normref_id, e.g. v://normref.com/std/JTG-F80-1-2017/bridge-casing@v1.0",
    )
    parser.add_argument("--version", default="v1.0", help="Version used when normref-id is auto-generated.")
    parser.add_argument("--namespace", default="v://normref.com/std", help="Namespace for auto-generated normref_id.")
    parser.add_argument("--last-updated", default=date.today().isoformat(), help="last_updated field.")
    return parser.parse_args()


def build_normref_id(parsed: dict[str, Any], args: argparse.Namespace, input_path: Path) -> str:
    if args.normref_id:
        return str(args.normref_id).strip()
    base = slugify(input_path.stem)
    return f"{args.namespace.rstrip('/')}/{base}@{args.version}"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"input markdown not found: {input_path}")

    content = input_path.read_text(encoding="utf-8")
    parsed = parse_markdown(content)
    parsed["normref_id"] = build_normref_id(parsed=parsed, args=args, input_path=input_path)
    parsed["last_updated"] = args.last_updated

    if parsed.get("name"):
        table_name = str(parsed["name"]).split("-")[0].strip()
        if table_name:
            parsed["applicable_tables"] = [table_name]

    output_path = Path(args.output) if args.output else input_path.with_suffix(".json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[normref-parser] wrote: {output_path}")
    print(f"[normref-parser] rules: {len(parsed.get('rules') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
