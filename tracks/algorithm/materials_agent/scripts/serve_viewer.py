#!/usr/bin/env python
"""Local web app: user black-box UI + debug viewer.

User UI (black-box testing):
  http://127.0.0.1:8765/

Debug viewer (inspect outputs/):
  http://127.0.0.1:8765/debug/?run=production

Usage:
  python scripts/serve_viewer.py
  python scripts/serve_viewer.py --port 8765
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
import threading
import traceback
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

USER_UI = ROOT / "user"
VIEWER = ROOT / "viewer"
OUTPUTS = ROOT / "outputs"
JOBS_DIR = OUTPUTS / "user_jobs"

ALLOWED_SUFFIXES = {
    ".json",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".js",
    ".svg",
    ".png",
    ".ico",
}

# Project docs exposed to the user UI (relative to materials_agent root).
DOC_CATALOG: list[dict[str, str]] = [
    {
        "id": "usage",
        "title": "使用说明",
        "path": "使用说明.md",
        "desc": "安装、配置与运行命令",
    },
    {
        "id": "readme",
        "title": "项目 README",
        "path": "README.md",
        "desc": "功能、架构与风险总览",
    },
    {
        "id": "verify-guide",
        "title": "人工核验指南",
        "path": "docs/人工核验_production_sciverse.md",
        "desc": "用户端/调试端核验步骤与通过标准",
    },
    {
        "id": "libs",
        "title": "文献库获取与缺口",
        "path": "docs/文献库获取与缺口.md",
        "desc": "Sciverse / OpenAlex / 高校库路径",
    },
    {
        "id": "free-libs",
        "title": "免费权威论文库与注册指南",
        "path": "docs/免费权威论文库与注册指南.md",
        "desc": "全球免费/可申请库：注册步骤与 Agent 训练用法",
    },
    {
        "id": "free-libs-table",
        "title": "免费论文库一览表",
        "path": "docs/免费论文库一览表.md",
        "desc": "链接、特色、专注领域、有影响力事件",
    },
    {
        "id": "completion",
        "title": "完成度与优化方向",
        "path": "完成度与优化方向.md",
        "desc": "赛题对照与冲分缺口",
    },
    {
        "id": "reviews",
        "title": "人工抽检说明",
        "path": "experiments/reviews/README.md",
        "desc": "Gap 评审模板与写法",
    },
    {
        "id": "expert-standards",
        "title": "专家级真人核对标准",
        "path": "experiments/reviews/专家级真人核对标准.md",
        "desc": "R/P/G/E/T/A/N/X/D 全量标准与双端入口",
    },
    {
        "id": "science-ai-gate",
        "title": "AI 科学抽检标准",
        "path": "experiments/reviews/科学抽检标准_AI可执行.md",
        "desc": "机器门禁 L0/L1（不替代真人核对）",
    },
    {
        "id": "deps",
        "title": "依赖与降级策略",
        "path": "DEPENDENCIES.md",
        "desc": "服务依赖与缺失时行为",
    },
]

ARTIFACT_LABELS: dict[str, str] = {
    "report.md": "调研报告 (report.md)",
    "gaps.json": "研究空白 (gaps.json)",
    "papers.json": "文献列表 (papers.json)",
    "production_verification.json": "生产验收 (verification)",
    "consistency.json": "一致性检查",
    "science_review.json": "AI 科学抽检",
    "optimization_metrics.json": "优化监控指标",
    "expert_review_pack.json": "专家核对包",
    "queries.json": "检索 Query",
    "known_pairs.json": "Known 对照表",
    "extractions.json": "知识抽取",
    "fulltext_index.json": "全文索引",
    "evidence_chunks.json": "证据切块",
    "audit.json": "审计日志",
    "parse_manifest.json": "解析清单",
    "literature_archive.json": "文献归档指针",
    "bundle.json": "完整 Bundle",
    "user_result.json": "用户端摘要",
    "route_a_spr_candidates.json": "Route A 候选",
    "route_a_external_validation.json": "Route A 外验",
    "route_a_spr_report.md": "Route A 报告",
    "route_a_run_summary.json": "Route A 摘要",
}


def related_docs() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in DOC_CATALOG:
        path = ROOT / item["path"]
        if not path.is_file():
            continue
        rows.append(
            {
                **item,
                "url": f"/api/docs/{item['path']}",
                "download_url": f"/api/docs/{item['path']}?download=1",
                "exists": True,
            }
        )
    return rows


def _outputs_rel(output_dir: str) -> str:
    """Normalize to path relative to outputs/ (supports absolute Windows paths)."""
    rel = (output_dir or "").replace("\\", "/").strip()
    if not rel:
        return ""
    lower = rel.lower()
    marker = "/outputs/"
    idx = lower.rfind(marker)
    if idx >= 0:
        return rel[idx + len(marker) :].strip("/")
    if lower.startswith("outputs/"):
        return rel[len("outputs/") :].strip("/")
    # Already relative to outputs (e.g. "production" or "user_jobs/<id>")
    return rel.lstrip("./").strip("/")


def _resolve_run_dir(run_id: str) -> Path | None:
    """Resolve outputs/<run_id> including nested ids like user_jobs/<job_id>."""
    rel = _outputs_rel(unquote(run_id or ""))
    if not rel or ".." in Path(rel).parts:
        return None
    candidate = _safe_join(OUTPUTS, rel)
    if candidate is None or not candidate.is_dir():
        return None
    return candidate


def artifact_links(output_dir: str) -> list[dict[str, str]]:
    """Hyperlinks to generated files under outputs/<run>/."""
    rel = _outputs_rel(output_dir)
    if not rel:
        return []
    run_dir = _resolve_run_dir(rel)
    if run_dir is None:
        return []
    rows: list[dict[str, str]] = []
    for name, label in ARTIFACT_LABELS.items():
        path = run_dir / name
        if not path.is_file():
            continue
        api = f"/api/run/{rel}/{name}"
        rows.append(
            {
                "name": name,
                "title": label,
                "url": api,
                "download_url": f"{api}?download=1",
                "bytes": path.stat().st_size,
            }
        )
    return rows


def _load_run_gates(run_dir: Path) -> dict[str, Any]:
    """Shared gate statuses for user/debug alignment (not live UI sync)."""
    gates: dict[str, Any] = {}
    verify_path = run_dir / "production_verification.json"
    if verify_path.is_file():
        try:
            payload = json.loads(verify_path.read_text(encoding="utf-8"))
            gates["verify"] = payload.get("status")
        except (OSError, json.JSONDecodeError):
            gates["verify"] = None
    science_path = run_dir / "science_review.json"
    if science_path.is_file():
        try:
            payload = json.loads(science_path.read_text(encoding="utf-8"))
            gates["science_review"] = payload.get("status")
        except (OSError, json.JSONDecodeError):
            gates["science_review"] = None
    consistency_path = run_dir / "consistency.json"
    if consistency_path.is_file():
        try:
            payload = json.loads(consistency_path.read_text(encoding="utf-8"))
            gates["consistency_ok"] = payload.get("ok")
        except (OSError, json.JSONDecodeError):
            gates["consistency_ok"] = None
    return gates


def attach_doc_links(result: dict[str, Any]) -> dict[str, Any]:
    """Ensure public payloads always carry docs + artifact hyperlinks + run align links."""
    from urllib.parse import quote

    out = dict(result)
    out["docs"] = related_docs()
    rel = _outputs_rel(str(out.get("output_dir") or out.get("run_id") or ""))
    out["run_id"] = rel
    out["artifacts"] = artifact_links(rel)
    if rel:
        q = quote(rel, safe="")
        out["debug_url"] = f"/debug/?run={q}"
        out["user_url"] = f"/?run={q}"
        run_dir = _resolve_run_dir(rel)
        if run_dir is not None and not isinstance(out.get("gates"), dict):
            out["gates"] = _load_run_gates(run_dir)
        elif run_dir is not None and isinstance(out.get("gates"), dict):
            # fill missing keys only
            loaded = _load_run_gates(run_dir)
            merged = dict(loaded)
            merged.update({k: v for k, v in out["gates"].items() if v is not None})
            out["gates"] = merged
    else:
        out["debug_url"] = "/debug/"
        out["user_url"] = "/"
    return out


PROFILES = {
    "quick": {
        "label": "快速演示（本地样例，适合黑盒冒烟）",
        "config": "configs/demo_local.yaml",
        "hint": "不联网，约数十秒内完成",
        "estimated": "通常 < 1 分钟",
    },
    "online": {
        "label": "在线检索（OpenAlex 元数据）",
        "config": "configs/default.yaml",
        "hint": "需要网络；全文解析按配置可选",
        "estimated": "约 2–10 分钟",
    },
    "production": {
        "label": "生产全文证据链（OA PDF + 解析）",
        "config": "configs/production.yaml",
        "hint": "需要 GROBID + Qdrant（默认 GROBID 主解析；MinerU 非必须）",
        "estimated": "约 15–60 分钟",
    },
    "sciverse": {
        "label": "Sciverse 检索 + 生产全文证据链",
        "config": "configs/production_sciverse.yaml",
        "hint": "需 SCIVERSE_API_TOKEN；失败回退 OpenAlex；Route A 需 MP_API_KEY（禁 offline 冒充）",
        "estimated": "约 15–60 分钟",
    },
    "semantic_scholar": {
        "label": "Semantic Scholar 检索 + 生产全文证据链",
        "config": "configs/production_semantic_scholar.yaml",
        "hint": "建议填写 S2_API_KEY；无 Key 时易 429，将自动回退 OpenAlex；需 GROBID/Qdrant",
        "estimated": "约 15–60 分钟",
    },
}

_JOBS: dict[str, dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()
_RUN_LOCK = threading.Lock()


def _safe_join(base: Path, relative: str) -> Path | None:
    rel = Path(unquote(relative).lstrip("/\\"))
    if ".." in rel.parts:
        return None
    candidate = (base / rel).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError:
        return None
    return candidate


def _list_runs() -> list[dict]:
    if not OUTPUTS.is_dir():
        return []
    rows: list[dict] = []

    def _append_run(path: Path, run_id: str) -> None:
        files = sorted(p.name for p in path.iterdir() if p.is_file())
        meta: dict[str, Any] = {
            "id": run_id,
            "files": files,
            "has_gaps": "gaps.json" in files,
            "has_papers": "papers.json" in files,
            "has_verify": "production_verification.json" in files,
            "has_route_a": "route_a_spr_candidates.json" in files,
        }
        verify_path = path / "production_verification.json"
        if verify_path.is_file():
            try:
                payload = json.loads(verify_path.read_text(encoding="utf-8"))
                meta["verify_status"] = payload.get("status")
            except (OSError, json.JSONDecodeError):
                meta["verify_status"] = None
        bundle_path = path / "bundle.json"
        if bundle_path.is_file():
            try:
                bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                meta["topic"] = bundle.get("topic")
                meta["papers"] = len(bundle.get("papers") or [])
                meta["gaps"] = len(bundle.get("gaps") or [])
            except (OSError, json.JSONDecodeError, TypeError):
                pass
        rows.append(meta)

    for path in sorted(OUTPUTS.iterdir()):
        if not path.is_dir():
            continue
        if path.name == "user_jobs":
            for job_dir in sorted(path.iterdir()):
                if job_dir.is_dir() and (job_dir / "gaps.json").is_file():
                    _append_run(job_dir, f"user_jobs/{job_dir.name}")
            continue
        _append_run(path, path.name)
    return rows


def sanitize_user_result(
    bundle: Any,
    *,
    output_dir: str,
    route_a: list[dict] | None = None,
    metrics: dict | None = None,
) -> dict:
    """Public-facing payload for black-box testing (no audit / parser internals)."""
    papers = []
    for paper in getattr(bundle, "papers", []) or []:
        abstract = (getattr(paper, "abstract", None) or "").strip()
        papers.append(
            {
                "id": paper.id,
                "title": paper.title,
                "year": paper.year,
                "doi": paper.doi,
                "venue": paper.venue,
                "cited_by": paper.cited_by,
                "abstract_preview": abstract[:280] + ("…" if len(abstract) > 280 else ""),
                "has_fulltext": bool(getattr(paper, "full_text", None)),
            }
        )

    gaps = []
    for gap in getattr(bundle, "gaps", []) or []:
        evidence = []
        for span in gap.evidence_chain or []:
            evidence.append(
                {
                    "paper_id": span.paper_id,
                    "claim": span.claim,
                    "quote": span.quote_or_basis,
                    "confidence": span.confidence,
                    "location": span.location,
                }
            )
        gaps.append(
            {
                "id": gap.id,
                "title": gap.title,
                "description": gap.description,
                "type": gap.gap_type,
                "novelty": gap.novelty,
                "actionability": gap.actionability,
                "review_status": gap.review_status,
                "supporting_paper_ids": gap.supporting_paper_ids,
                "contradicting_paper_ids": gap.contradicting_paper_ids,
                "suggested_next_step": gap.suggested_next_step,
                "falsification_test": gap.falsification_test,
                "evidence": evidence,
            }
        )

    consistency = None
    if getattr(bundle, "consistency", None) is not None:
        consistency = {
            "ok": bool(bundle.consistency.ok),
            "issue_count": len(bundle.consistency.issues or []),
        }

    route_rows = []
    for cand in route_a or []:
        ext = cand.get("external_validation") or {}
        route_rows.append(
            {
                "hypothesis": cand.get("hypothesis"),
                "material": cand.get("material_motif"),
                "property": cand.get("property_target"),
                "score": cand.get("score"),
                "novelty": cand.get("novelty_label"),
                "validation": ext.get("verdict"),
            }
        )

    return attach_doc_links(
        {
            "topic": bundle.topic,
            "subfield": bundle.subfield,
            "queries": bundle.query_variants,
            "summary": {
                "papers": len(papers),
                "gaps": len(gaps),
                "fulltext_papers": sum(1 for p in papers if p["has_fulltext"]),
                "consistency_ok": None if consistency is None else consistency["ok"],
            },
            "metrics": metrics,
            "papers": papers,
            "gaps": gaps,
            "consistency": consistency,
            "report_markdown": bundle.report_markdown or "",
            "route_a": route_rows,
            "output_dir": output_dir,
        }
    )


def _job_public(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result")
    if isinstance(result, dict):
        result = attach_doc_links(result)
    return {
        "id": job["id"],
        "status": job["status"],
        "profile": job["profile"],
        "topic": job["topic"],
        "route_a": job["route_a"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "message": job.get("message", ""),
        "error": job.get("error"),
        "result": result,
    }


def _run_survey_job(job_id: str) -> None:
    with _JOBS_LOCK:
        job = _JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = datetime.now(timezone.utc).isoformat()
        job["message"] = "正在检索与分析文献…"
        profile = job["profile"]
        topic = job["topic"]
        route_a = job["route_a"]
        max_papers = job.get("max_papers")

    acquired = _RUN_LOCK.acquire(blocking=False)
    if not acquired:
        with _JOBS_LOCK:
            job = _JOBS[job_id]
            job["status"] = "failed"
            job["error"] = "已有任务在运行，请稍后再试"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            job["message"] = "排队冲突"
        return

    try:
        from materials_agent.config import load_config
        from materials_agent.pipeline import LiteratureSurveyAgent
        from materials_agent.routes.route_a import RouteASearcher

        cfg_path = ROOT / PROFILES[profile]["config"]
        cfg = load_config(cfg_path)
        cfg.topic = topic
        if max_papers:
            cfg.max_papers = int(max_papers)
        out_dir = JOBS_DIR / job_id
        cfg.output_dir = str(out_dir.relative_to(ROOT)).replace("\\", "/")
        if route_a:
            cfg.route_a.enabled = True

        with _JOBS_LOCK:
            _JOBS[job_id]["message"] = f"配置 {profile} · 开始 pipeline…"

        agent = LiteratureSurveyAgent(cfg)
        bundle = agent.run()
        saved = agent.save(bundle)

        route_rows: list[dict] = []
        if cfg.route_a.enabled:
            from dataclasses import asdict, is_dataclass

            with _JOBS_LOCK:
                _JOBS[job_id]["message"] = "正在运行 Route A…"
            searcher = RouteASearcher(cfg, bundle)
            cands = searcher.run()
            searcher.save(cands, saved)
            route_rows = [asdict(c) if is_dataclass(c) else dict(c) for c in cands]

        metrics_payload = _load_run_metrics(Path(saved))
        rel_out = str(Path(saved).resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        result = sanitize_user_result(
            bundle, output_dir=rel_out, route_a=route_rows, metrics=metrics_payload
        )
        (saved / "user_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with _JOBS_LOCK:
            job = _JOBS[job_id]
            job["status"] = "done"
            job["result"] = result
            job["message"] = "完成"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        with _JOBS_LOCK:
            job = _JOBS[job_id]
            job["status"] = "failed"
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["message"] = "失败"
            job["finished_at"] = datetime.now(timezone.utc).isoformat()
            job["traceback"] = traceback.format_exc()[-2000:]
    finally:
        _RUN_LOCK.release()


def create_job(payload: dict[str, Any]) -> dict[str, Any]:
    topic = str(payload.get("topic") or "").strip()
    if len(topic) < 3:
        raise ValueError("请输入至少 3 个字符的研究主题")
    if len(topic) > 300:
        raise ValueError("主题过长（最多 300 字符）")
    profile = str(payload.get("profile") or "quick").strip().lower()
    if profile not in PROFILES:
        raise ValueError(f"未知模式: {profile}")
    route_a = bool(payload.get("route_a") or False)
    max_papers = payload.get("max_papers")
    if max_papers is not None:
        max_papers = int(max_papers)
        if max_papers < 1 or max_papers > 30:
            raise ValueError("max_papers 需在 1–30")

    with _JOBS_LOCK:
        running = any(j["status"] in {"queued", "running"} for j in _JOBS.values())
        if running:
            raise RuntimeError("已有任务在运行，请等待完成后再提交")
        job_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        job = {
            "id": job_id,
            "status": "queued",
            "profile": profile,
            "topic": topic,
            "route_a": route_a,
            "max_papers": max_papers,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "message": "已入队",
            "error": None,
            "result": None,
        }
        _JOBS[job_id] = job

    thread = threading.Thread(target=_run_survey_job, args=(job_id,), daemon=True)
    thread.start()
    return _job_public(job)


def _load_run_metrics(run_dir: Path) -> dict | None:
    metrics_path = run_dir / "optimization_metrics.json"
    if metrics_path.is_file():
        try:
            data = json.loads(metrics_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None
    audit_path = run_dir / "audit.json"
    if audit_path.is_file():
        try:
            rows = json.loads(audit_path.read_text(encoding="utf-8"))
            for row in rows or []:
                if row.get("step") == "optimization_metrics" and isinstance(row.get("meta"), dict):
                    return row["meta"]
        except (OSError, json.JSONDecodeError, TypeError):
            return None
    return None


def _run_content_fingerprint(run_dir: Path) -> str:
    """Hash core artifacts so title/evidence edits invalidate user_result cache."""
    digest = hashlib.sha256()
    for name in ("gaps.json", "papers.json", "optimization_metrics.json"):
        path = run_dir / name
        digest.update(name.encode("utf-8"))
        if path.is_file():
            digest.update(path.read_bytes())
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def _public_from_run(run_id: str) -> dict[str, Any]:
    """Build black-box payload from an existing outputs/<run_id> directory."""
    run_dir = _resolve_run_dir(run_id)
    if run_dir is None:
        raise FileNotFoundError(f"run not found: {run_id}")
    rel = _outputs_rel(str(run_dir.relative_to(ROOT)))
    fingerprint = _run_content_fingerprint(run_dir)

    cached = run_dir / "user_result.json"
    if cached.is_file():
        try:
            payload = json.loads(cached.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("_cache_key") == fingerprint:
                payload["output_dir"] = f"outputs/{rel}"
                metrics = _load_run_metrics(run_dir)
                if metrics is not None:
                    payload["metrics"] = metrics
                return attach_doc_links(payload)
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    bundle_path = run_dir / "bundle.json"
    if not bundle_path.is_file():
        raise FileNotFoundError(f"bundle.json missing in {run_id}")

    from materials_agent.models import SurveyBundle

    bundle = SurveyBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
    route_rows: list[dict] = []
    route_path = run_dir / "route_a_spr_candidates.json"
    if route_path.is_file():
        try:
            payload = json.loads(route_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                route_rows = payload
            elif isinstance(payload, dict):
                route_rows = payload.get("candidates") or []
        except (OSError, json.JSONDecodeError, TypeError):
            route_rows = []
    result = sanitize_user_result(
        bundle,
        output_dir=f"outputs/{rel}",
        route_a=route_rows,
        metrics=_load_run_metrics(run_dir),
    )
    result["_cache_key"] = fingerprint
    try:
        cached.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    return result


def _mime_for(path: Path) -> str:
    suffix = path.suffix.lower()
    mapping = {
        ".json": "application/json; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".svg": "image/svg+xml",
    }
    if suffix in mapping:
        return mapping[suffix]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    if length > 50_000:
        raise ValueError("请求体过大")
    raw = handler.rfile.read(length)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 必须为对象")
    return data


class AppHandler(BaseHTTPRequestHandler):
    server_version = "MaterialsAgentApp/0.2"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(
        self,
        code: int,
        body: bytes,
        content_type: str,
        *,
        download_name: str | None = None,
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if download_name:
            safe = download_name.replace('"', "")
            self.send_header("Content-Disposition", f'attachment; filename="{safe}"')
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _want_download(self, query: str) -> bool:
        from urllib.parse import parse_qs

        values = parse_qs(query or "").get("download") or []
        return any(v in {"1", "true", "yes"} for v in values)

    def _serve_static(self, root: Path, rel: str) -> bool:
        if rel in {"", "/"}:
            target = root / "index.html"
        else:
            target = _safe_join(root, rel)
        if target is None or not target.is_file() or target.suffix.lower() not in ALLOWED_SUFFIXES:
            return False
        self._send(200, target.read_bytes(), _mime_for(target))
        return True

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path or "/"
        if path == "/api/jobs":
            try:
                payload = _read_json_body(self)
                job = create_job(payload)
                self._send_json(202, job)
            except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
            return
        self._send_json(404, {"error": "not found", "path": path})

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path or "/"

        if path == "/api/profiles":
            self._send_json(
                200,
                {
                    "profiles": [
                        {"id": key, **{k: v for k, v in meta.items() if k != "config"}}
                        for key, meta in PROFILES.items()
                    ]
                },
            )
            return

        if path == "/api/topic-presets":
            preset_path = ROOT / "configs" / "topic_presets.json"
            if not preset_path.is_file():
                self._send_json(404, {"error": "topic_presets.json missing"})
                return
            try:
                payload = json.loads(preset_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self._send_json(500, {"error": f"invalid topic_presets.json: {exc}"})
                return
            self._send_json(200, payload)
            return

        if path == "/api/jobs":
            with _JOBS_LOCK:
                rows = [_job_public(j) for j in sorted(_JOBS.values(), key=lambda x: x["created_at"], reverse=True)]
            self._send_json(200, {"jobs": rows[:50]})
            return

        job_match = re.fullmatch(r"/api/jobs/([^/]+)", path)
        if job_match:
            job_id = job_match.group(1)
            with _JOBS_LOCK:
                job = _JOBS.get(job_id)
            if not job:
                # try persisted user_result
                persisted = JOBS_DIR / job_id / "user_result.json"
                if persisted.is_file():
                    try:
                        payload = _public_from_run(f"user_jobs/{job_id}")
                    except FileNotFoundError:
                        payload = attach_doc_links(
                            json.loads(persisted.read_text(encoding="utf-8"))
                        )
                    self._send_json(
                        200,
                        {
                            "id": job_id,
                            "status": "done",
                            "result": payload,
                            "message": "从磁盘恢复",
                        },
                    )
                    return
                self._send_json(404, {"error": "job not found"})
                return
            self._send_json(200, _job_public(job))
            return

        if path == "/api/runs":
            self._send_json(200, {"runs": _list_runs()})
            return

        if path == "/api/docs":
            self._send_json(200, {"docs": related_docs()})
            return

        if path.startswith("/api/docs/"):
            rel = unquote(path[len("/api/docs/") :])
            allowed = {item["path"] for item in DOC_CATALOG}
            if rel not in allowed:
                self._send_json(404, {"error": "doc not in catalog", "path": rel})
                return
            target = _safe_join(ROOT, rel)
            if target is None or not target.is_file() or target.suffix.lower() not in {".md", ".txt"}:
                self._send_json(404, {"error": "not found", "path": rel})
                return
            download_name = target.name if self._want_download(parsed.query) else None
            self._send(200, target.read_bytes(), _mime_for(target), download_name=download_name)
            return

        public_match = re.fullmatch(r"/api/runs/(.+)/public", path)
        if public_match:
            run_id = unquote(public_match.group(1))
            try:
                self._send_json(200, _public_from_run(run_id))
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except Exception as exc:  # noqa: BLE001 — surface load errors to UI
                self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})
            return

        expert_match = re.fullmatch(r"/api/runs/(.+)/expert-review", path)
        if expert_match:
            run_id = unquote(expert_match.group(1))
            run_dir = _resolve_run_dir(run_id)
            if run_dir is None:
                self._send_json(404, {"error": f"run not found: {run_id}"})
                return
            try:
                from materials_agent.expert_review_pack import (
                    build_expert_review_pack,
                    write_expert_review_pack,
                )

                pack = build_expert_review_pack(run_dir, run_id=_outputs_rel(run_id))
                persist_error = None
                try:
                    write_expert_review_pack(run_dir, run_id=_outputs_rel(run_id))
                    pack["persisted"] = True
                except OSError as exc:
                    persist_error = str(exc)
                    pack["persisted"] = False
                    pack["persist_error"] = persist_error
                self._send_json(200, pack)
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"error": f"expert-review build failed: {exc}"})
            return

        if path == "/api/expert-standards":
            std_path = ROOT / "configs" / "expert_human_review_standards.json"
            if not std_path.is_file():
                self._send_json(404, {"error": "standards missing"})
                return
            try:
                self._send_json(200, json.loads(std_path.read_text(encoding="utf-8")))
            except json.JSONDecodeError as exc:
                self._send_json(500, {"error": str(exc)})
            return

        if path.startswith("/api/run/"):
            rel = unquote(path[len("/api/run/") :])
            target = _safe_join(OUTPUTS, rel)
            if target is None or not target.is_file() or target.suffix.lower() not in ALLOWED_SUFFIXES:
                self._send_json(404, {"error": "not found", "path": rel})
                return
            download_name = target.name if self._want_download(parsed.query) else None
            self._send(200, target.read_bytes(), _mime_for(target), download_name=download_name)
            return

        # User black-box UI
        if path in {"/", "/index.html", "/user", "/user/"}:
            index = USER_UI / "index.html"
            self._send(200, index.read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/user/"):
            if self._serve_static(USER_UI, path[len("/user") :]):
                return

        # Debug viewer
        if path in {"/debug", "/debug/"}:
            index = VIEWER / "index.html"
            self._send(200, index.read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/debug/"):
            if self._serve_static(VIEWER, path[len("/debug") :]):
                return

        # Fallback for topic presets when /api/topic-presets is unavailable
        if path == "/configs/topic_presets.json":
            preset_path = ROOT / "configs" / "topic_presets.json"
            if preset_path.is_file():
                self._send(200, preset_path.read_bytes(), "application/json; charset=utf-8")
                return

        # Convenience: /styles.css used by absolute paths in user UI
        if path.startswith("/assets/user/"):
            if self._serve_static(USER_UI, path[len("/assets/user") :]):
                return
        if self._serve_static(USER_UI, path):
            return

        self._send_json(404, {"error": "not found", "path": path})


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve Materials Agent user + debug UIs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--run",
        default="production",
        help="Default run id for debug viewer query string",
    )
    args = parser.parse_args()
    if not USER_UI.is_dir():
        print(f"Missing user UI directory: {USER_UI}", file=sys.stderr)
        return 1
    if not VIEWER.is_dir():
        print(f"Missing debug viewer directory: {VIEWER}", file=sys.stderr)
        return 1
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    httpd = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"用户界面（黑盒） → http://{args.host}:{args.port}/")
    print(f"调试界面         → http://{args.host}:{args.port}/debug/?run={args.run}")
    print(f"Outputs root: {OUTPUTS}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
