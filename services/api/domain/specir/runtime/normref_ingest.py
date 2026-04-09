"""NormRef ingest parser runtime (P0).

Upload PDF/markdown/text standards, parse section hints and generate
rule candidates for manual review and publish.
"""

from __future__ import annotations

from datetime import UTC, datetime
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _txt(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _safe_slug(value: str) -> str:
    token = re.sub(r"[^0-9a-zA-Z._\-]+", "-", _txt(value).strip().lower()).strip("-")
    return token or "rule"


def _deep_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class NormRefSection(BaseModel):
    section_no: str = ""
    section_title: str = ""
    line_no: int = 0
    raw_line: str = ""


class NormRefRuleCandidate(BaseModel):
    candidate_id: str
    job_id: str
    rule_id: str
    category: str
    field_key: str = ""
    operator: str = "eq"
    threshold_value: str = ""
    unit: str = ""
    severity: str = "mandatory"
    norm_ref: str = ""
    source_line: str = ""
    confidence: float = 0.0
    status: Literal["pending", "approved", "rejected"] = "pending"
    notes: str = ""


class NormRefCandidatePatch(BaseModel):
    rule_id: str | None = None
    category: str | None = None
    field_key: str | None = None
    operator: str | None = None
    threshold_value: str | None = None
    unit: str | None = None
    severity: str | None = None
    norm_ref: str | None = None
    source_line: str | None = None
    notes: str | None = None


class NormRefIngestJob(BaseModel):
    job_id: str
    std_code: str
    title: str = ""
    level: str = "industry"
    file_name: str
    file_hash: str
    status: Literal["queued", "running", "review_required", "failed", "completed"] = "queued"
    created_at: str
    updated_at: str
    completed_at: str = ""
    warnings: list[str] = Field(default_factory=list)
    sections: list[NormRefSection] = Field(default_factory=list)
    candidates: list[NormRefRuleCandidate] = Field(default_factory=list)
    source_text_preview: str = ""


class NormRefIngestPublishResult(BaseModel):
    ok: bool = True
    job_id: str
    version_tag: str
    published_count: int
    snapshot_hash: str
    rules: list[dict[str, Any]] = Field(default_factory=list)
    write_to_docs: bool = False


class NormRefIngestEngine:
    """In-memory ingest engine with optional docs writeback."""

    _SECTION_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)+)\s*([^\n]*)$")
    _NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")
    _UNIT_PATTERN = re.compile(r"(mm|cm|m|MPa|kPa|kg|t|%|‰|℃)")
    _COMPARATOR_PATTERN = re.compile(r"(<=|>=|<|>|±|\+/-|~|～|≤|≥)")
    _DEFAULT_OCR_MAX_PAGES = 20
    _WORKER_POOL = ThreadPoolExecutor(max_workers=max(1, int(os.getenv("NORMREF_INGEST_WORKERS", "2"))))

    def __init__(self, *, ocr_max_pages: int | None = None) -> None:
        self._jobs: dict[str, NormRefIngestJob] = {}
        self._job_sources: dict[str, dict[str, Any]] = {}
        self._lock = RLock()
        env_pages = int(os.getenv("NORMREF_OCR_MAX_PAGES", str(self._DEFAULT_OCR_MAX_PAGES)))
        selected = int(ocr_max_pages) if ocr_max_pages is not None else env_pages
        self._ocr_max_pages = max(10, selected)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _quality_score(text: str) -> float:
        cleaned = re.sub(r"\s+", "", _txt(text))
        if not cleaned:
            return 0.0
        cjk = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
        digits = len(re.findall(r"\d", cleaned))
        return float(len(cleaned)) + (cjk * 1.5) + (digits * 0.3)

    @staticmethod
    def _looks_low_quality(text: str) -> bool:
        cleaned = re.sub(r"\s+", "", _txt(text))
        if len(cleaned) < 800:
            return True
        cjk = len(re.findall(r"[\u4e00-\u9fff]", cleaned))
        return cjk < 120

    @staticmethod
    def _extract_pdf_text_via_ocr(content: bytes, *, max_pages: int = 120) -> tuple[str, list[str]]:
        warnings: list[str] = []
        try:
            import numpy as np  # type: ignore
            import pypdfium2 as pdfium  # type: ignore
            from rapidocr_onnxruntime import RapidOCR  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            warnings.append(f"ocr_dependencies_unavailable: {exc}")
            return "", warnings

        try:
            doc = pdfium.PdfDocument(content)
        except Exception as exc:  # pragma: no cover - optional dependency
            warnings.append(f"ocr_open_pdf_failed: {exc}")
            return "", warnings

        total_pages = len(doc)
        page_limit = min(max(1, int(max_pages)), total_pages)
        if page_limit < total_pages:
            warnings.append(f"ocr_page_limit_applied:{page_limit}/{total_pages}")

        ocr = RapidOCR()
        lines: list[str] = []

        for index in range(page_limit):
            page = None
            try:
                page = doc.get_page(index)
                bitmap = page.render(scale=2)
                image = np.asarray(bitmap.to_pil())
                result, _ = ocr(image)
                if result:
                    for row in result:
                        if len(row) >= 2:
                            text = _txt(row[1]).strip()
                            if text:
                                lines.append(text)
            except Exception:
                continue
            finally:
                if page is not None:
                    try:
                        page.close()
                    except Exception:
                        pass

        text = "\n".join(lines)
        if not text:
            warnings.append("ocr_text_empty")
        return text, warnings

    def _extract_pdf_text(self, content: bytes) -> tuple[str, list[str]]:
        warnings: list[str] = []
        native_text = ""
        try:
            import pdfplumber  # type: ignore

            texts: list[str] = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = _txt(page.extract_text()).strip()
                    if text:
                        texts.append(text)
            if texts:
                native_text = "\n".join(texts)
        except Exception as exc:  # pragma: no cover - env dependent
            warnings.append(f"pdfplumber_unavailable_or_failed: {exc}")

        if native_text and not NormRefIngestEngine._looks_low_quality(native_text):
            return native_text, warnings

        if native_text:
            warnings.append("pdf_text_quality_low_try_ocr")

        ocr_text, ocr_warnings = NormRefIngestEngine._extract_pdf_text_via_ocr(
            content=content,
            max_pages=self._ocr_max_pages,
        )
        warnings.extend(ocr_warnings)
        if ocr_text and NormRefIngestEngine._quality_score(ocr_text) >= NormRefIngestEngine._quality_score(native_text):
            warnings.append("ocr_selected")
            return ocr_text, warnings

        if native_text:
            return native_text, warnings
        return _txt(content), warnings

    def _extract_text(self, file_name: str, content: bytes) -> tuple[str, list[str]]:
        lower = _txt(file_name).strip().lower()
        if lower.endswith(".pdf"):
            return self._extract_pdf_text(content)
        return _txt(content), []

    def _infer_category(self, std_code: str, line: str) -> str:
        blob = f"{_txt(std_code).lower()} {_txt(line).lower()}"
        if "机电" in line or "electro" in blob or "2182" in blob:
            return "electromechanical/general-check"
        if "养护" in line or "5220" in blob:
            return "maintenance/civil-check"
        if any(token in line for token in ["桩", "成孔", "钻孔", "灌注"]) or "pile" in blob:
            return "bridge/pile-hole-check"
        return "civil/general-check"

    def _infer_field_key(self, line: str) -> str:
        mapping: list[tuple[str, str]] = [
            ("孔径", "hole_diameter"),
            ("垂直度", "hole_verticality"),
            ("倾斜", "inclination"),
            ("强度", "strength"),
            ("坍落度", "slump"),
            ("钢筋", "rebar"),
            ("厚度", "thickness"),
            ("宽度", "width"),
            ("长度", "length"),
            ("平整度", "flatness"),
            ("高程", "elevation"),
            ("标高", "elevation"),
        ]
        for token, key in mapping:
            if token in line:
                return key
        return "measured_value"

    def _infer_operator(self, line: str) -> str:
        text = _txt(line)
        if any(token in text for token in ["不小于", "不得小于", ">=", "≥"]):
            return "gte"
        if any(token in text for token in ["不大于", "不得大于", "<=", "≤"]):
            return "lte"
        if any(token in text for token in ["±", "+/-", "允许偏差"]):
            return "tolerance"
        if "~" in text or "～" in text:
            return "range"
        return "eq"

    def _looks_like_rule_line(self, text: str) -> bool:
        line = _txt(text).strip()
        if not line:
            return False
        if self._COMPARATOR_PATTERN.search(line):
            return True
        if any(token in line for token in ["允许偏差", "偏差", "不小于", "不大于", "不得", "应符合", "应满足", "检验", "强度", "坍落度", "压实度"]):
            return True
        has_number = bool(self._NUMBER_PATTERN.search(line))
        has_unit = bool(self._UNIT_PATTERN.search(line))
        return has_number and has_unit

    def _extract_sections(self, lines: list[str]) -> list[NormRefSection]:
        out: list[NormRefSection] = []
        for index, line in enumerate(lines, start=1):
            match = self._SECTION_PATTERN.match(line)
            if not match:
                continue
            out.append(
                NormRefSection(
                    section_no=_txt(match.group(1)).strip(),
                    section_title=_txt(match.group(2)).strip(),
                    line_no=index,
                    raw_line=line,
                )
            )
        return out

    def _extract_candidates(self, *, job_id: str, std_code: str, lines: list[str]) -> list[NormRefRuleCandidate]:
        out: list[NormRefRuleCandidate] = []
        section_hint = ""
        for line in lines:
            text = _txt(line).strip()
            if not text:
                continue
            sec = self._SECTION_PATTERN.match(text)
            if sec:
                section_hint = _txt(sec.group(1)).strip()
                continue

            if not self._looks_like_rule_line(text):
                continue

            number_match = self._NUMBER_PATTERN.search(text)
            threshold = _txt(number_match.group(0)).strip() if number_match else ""
            unit_match = self._UNIT_PATTERN.search(text)
            unit = _txt(unit_match.group(1)).strip() if unit_match else ""
            operator = self._infer_operator(text)
            field_key = self._infer_field_key(text)
            category = self._infer_category(std_code, text)
            base_id = ".".join(
                token for token in [category.replace("/", "."), field_key, _safe_slug(section_hint or "rule")] if token
            )
            candidate_id = f"cand-{uuid4().hex[:12]}"
            out.append(
                NormRefRuleCandidate(
                    candidate_id=candidate_id,
                    job_id=job_id,
                    rule_id=base_id,
                    category=category,
                    field_key=field_key,
                    operator=operator,
                    threshold_value=threshold,
                    unit=unit,
                    severity="mandatory",
                    norm_ref=section_hint,
                    source_line=text[:500],
                    confidence=0.82 if threshold else 0.58,
                    status="pending",
                )
            )

        if out:
            return out

        fallback = [
            ("bridge/pile-hole-check", "hole_diameter", "tolerance", "%"),
            ("bridge/pile-hole-check", "hole_verticality", "lte", "%"),
            ("civil/general-check", "strength", "gte", "MPa"),
        ]
        for category, field_key, operator, unit in fallback:
            out.append(
                NormRefRuleCandidate(
                    candidate_id=f"cand-{uuid4().hex[:12]}",
                    job_id=job_id,
                    rule_id=f"{category.replace('/', '.')}.{field_key}.fallback",
                    category=category,
                    field_key=field_key,
                    operator=operator,
                    threshold_value="",
                    unit=unit,
                    severity="mandatory",
                    norm_ref="",
                    source_line="parser_fallback_scaffold",
                    confidence=0.25,
                    status="pending",
                    notes="auto fallback due to low text extraction quality",
                )
            )
        return out

    def _parse_job_payload(
        self,
        *,
        job_id: str,
        file_name: str,
        content: bytes,
        std_code: str,
    ) -> tuple[str, list[str], list[NormRefSection], list[NormRefRuleCandidate], Literal["review_required", "failed"]]:
        text, warnings = self._extract_text(file_name=file_name, content=content)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        sections = self._extract_sections(lines)
        candidates = self._extract_candidates(job_id=job_id, std_code=std_code, lines=lines)
        status: Literal["review_required", "failed"] = "review_required"
        if not text.strip():
            status = "failed"
            warnings.append("empty_text_after_parse")
        return text, warnings, sections[:3000], candidates[:5000], status

    def _run_parse_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            source = self._job_sources.get(job_id)
            if job is None or source is None:
                return
            job.status = "running"
            job.updated_at = self._now()

        file_name = _txt(source.get("file_name")).strip() or "standard.pdf"
        std_code = _txt(source.get("std_code")).strip()
        content = source.get("content")
        if not isinstance(content, (bytes, bytearray)):
            with self._lock:
                cached = self._jobs.get(job_id)
                if cached is not None:
                    cached.status = "failed"
                    cached.updated_at = self._now()
                    cached.completed_at = self._now()
                    cached.warnings = list(cached.warnings) + ["invalid_content_payload"]
                self._job_sources.pop(job_id, None)
            return

        try:
            text, warnings, sections, candidates, status = self._parse_job_payload(
                job_id=job_id,
                file_name=file_name,
                content=bytes(content),
                std_code=std_code,
            )
            with self._lock:
                cached = self._jobs.get(job_id)
                if cached is None:
                    return
                cached.status = status
                cached.updated_at = self._now()
                cached.completed_at = self._now()
                cached.warnings = warnings
                cached.sections = sections
                cached.candidates = candidates
                cached.source_text_preview = text[:3000]
                self._job_sources.pop(job_id, None)
        except Exception as exc:  # pragma: no cover - defensive
            with self._lock:
                cached = self._jobs.get(job_id)
                if cached is not None:
                    cached.status = "failed"
                    cached.updated_at = self._now()
                    cached.completed_at = self._now()
                    cached.warnings = list(cached.warnings) + [f"parse_exception:{_txt(exc)}"]
                self._job_sources.pop(job_id, None)

    def create_job(
        self,
        *,
        file_name: str,
        content: bytes,
        std_code: str,
        title: str = "",
        level: str = "industry",
        defer_parse: bool = False,
    ) -> dict[str, Any]:
        now = self._now()
        job_id = f"ingest-{uuid4().hex[:16]}"
        file_hash = "sha256:" + hashlib.sha256(content).hexdigest()
        text = ""
        warnings: list[str] = []
        sections: list[NormRefSection] = []
        candidates: list[NormRefRuleCandidate] = []
        status: Literal["queued", "running", "review_required", "failed", "completed"] = "queued" if defer_parse else "review_required"

        if not defer_parse:
            parsed_text, parsed_warnings, parsed_sections, parsed_candidates, parsed_status = self._parse_job_payload(
                job_id=job_id,
                file_name=file_name,
                content=content,
                std_code=std_code,
            )
            text = parsed_text
            warnings = parsed_warnings
            sections = parsed_sections
            candidates = parsed_candidates
            status = parsed_status

        job = NormRefIngestJob(
            job_id=job_id,
            std_code=_txt(std_code).strip(),
            title=_txt(title).strip(),
            level=_txt(level).strip() or "industry",
            file_name=_txt(file_name).strip() or "standard.pdf",
            file_hash=file_hash,
            status=status,
            created_at=now,
            updated_at=now,
            completed_at=now if not defer_parse else "",
            warnings=warnings,
            sections=sections,
            candidates=candidates,
            source_text_preview=text[:3000],
        )
        with self._lock:
            self._jobs[job_id] = job
            if defer_parse:
                self._job_sources[job_id] = {
                    "file_name": file_name,
                    "content": bytes(content),
                    "std_code": std_code,
                }
        if defer_parse:
            self._WORKER_POOL.submit(self._run_parse_job, job_id)
        return {"ok": True, "job": _deep_copy(job.model_dump(mode="json"))}

    def get_job(self, *, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}
        return {"ok": True, "job": _deep_copy(job.model_dump(mode="json"))}

    def list_candidates(self, *, job_id: str, status: str = "") -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}
        rows = list(job.candidates)
        want = _txt(status).strip().lower()
        if want:
            rows = [x for x in rows if _txt(x.status).lower() == want]
        return {
            "ok": True,
            "job_id": job_id,
            "count": len(rows),
            "candidates": _deep_copy([x.model_dump(mode="json") for x in rows]),
        }

    def update_candidate_status(self, *, job_id: str, candidate_id: str, status: Literal["approved", "rejected"]) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"ok": False, "error": "job_not_found", "job_id": job_id}
            hit = None
            for cand in job.candidates:
                if cand.candidate_id == candidate_id:
                    cand.status = status
                    hit = cand
                    break
            if hit is None:
                return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}
            job.updated_at = self._now()
            return {"ok": True, "candidate": _deep_copy(hit.model_dump(mode="json"))}

    def patch_candidate(self, *, job_id: str, candidate_id: str, patch: NormRefCandidatePatch) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"ok": False, "error": "job_not_found", "job_id": job_id}
            hit: NormRefRuleCandidate | None = None
            for cand in job.candidates:
                if cand.candidate_id == candidate_id:
                    hit = cand
                    break
            if hit is None:
                return {"ok": False, "error": "candidate_not_found", "candidate_id": candidate_id}

            payload = patch.model_dump(exclude_none=True)
            for key in (
                "rule_id",
                "category",
                "field_key",
                "operator",
                "threshold_value",
                "unit",
                "severity",
                "norm_ref",
                "source_line",
                "notes",
            ):
                if key in payload:
                    setattr(hit, key, _txt(payload.get(key)).strip())
            job.updated_at = self._now()
            return {"ok": True, "candidate": _deep_copy(hit.model_dump(mode="json"))}

    @staticmethod
    def _docs_rule_root() -> Path:
        return (Path(__file__).resolve().parents[5] / "docs" / "normref" / "rule" / "imported").resolve()

    def publish(
        self,
        *,
        job_id: str,
        candidate_ids: list[str] | None = None,
        version_tag: str = "latest",
        write_to_docs: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        selected = [x for x in job.candidates if x.status == "approved"]
        if candidate_ids:
            wanted = {x for x in candidate_ids if _txt(x).strip()}
            selected = [x for x in selected if x.candidate_id in wanted]
        if not selected:
            return {"ok": False, "error": "no_approved_candidates", "job_id": job_id}

        tag = _txt(version_tag).strip() or "latest"
        rules: list[dict[str, Any]] = []
        for cand in selected:
            uri = f"v://normref.com/rule/{cand.category}/{_safe_slug(cand.field_key)}@{tag}"
            payload = {
                "rule_id": cand.rule_id,
                "version": tag,
                "uri": uri,
                "category": cand.category,
                "field_key": cand.field_key,
                "operator": cand.operator,
                "threshold_value": cand.threshold_value,
                "unit": cand.unit,
                "severity": cand.severity,
                "norm_ref": cand.norm_ref,
                "source_line": cand.source_line,
                "confidence": cand.confidence,
                "ingest_job_id": job_id,
                "candidate_id": cand.candidate_id,
                "source_std_code": job.std_code,
                "source_level": job.level,
                "scope": job.level,
            }
            payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
            payload["hash"] = "sha256:" + hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            rules.append(payload)

        snapshot_hash = "sha256:" + hashlib.sha256(
            json.dumps(sorted(rules, key=lambda x: x.get("rule_id", "")), ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

        if write_to_docs:
            root = self._docs_rule_root()
            root.mkdir(parents=True, exist_ok=True)
            for rule in rules:
                category = _txt(rule.get("category")).strip().strip("/")
                target_dir = root / category if category else root
                target_dir.mkdir(parents=True, exist_ok=True)
                rid = _safe_slug(_txt(rule.get("rule_id")))
                hash_suffix = _safe_slug(_txt(rule.get("hash")).replace("sha256:", ""))[:10] or uuid4().hex[:10]
                fp = target_dir / f"{rid}@{_safe_slug(tag)}-{hash_suffix}.json"
                fp.write_text(json.dumps(rule, ensure_ascii=False, indent=2), encoding="utf-8")

        with self._lock:
            cached_job = self._jobs.get(job_id)
            if cached_job is not None:
                cached_job.status = "completed"
                cached_job.updated_at = self._now()
                cached_job.completed_at = self._now()

        out = NormRefIngestPublishResult(
            ok=True,
            job_id=job_id,
            version_tag=tag,
            published_count=len(rules),
            snapshot_hash=snapshot_hash,
            rules=rules,
            write_to_docs=bool(write_to_docs),
        )
        return out.model_dump(mode="json")


__all__ = ["NormRefIngestEngine", "NormRefCandidatePatch"]
