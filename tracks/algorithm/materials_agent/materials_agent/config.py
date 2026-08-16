from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


_ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")
_PROJECT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_PROJECT_ENV_FILE, override=False)


def _expand_env(value: str) -> str:
    def repl(match: re.Match[str]) -> str:
        key, default = match.group(1), match.group(2)
        return os.environ.get(key, default if default is not None else "")

    return _ENV_PATTERN.sub(repl, value)


def _expand_tree(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _expand_tree(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_expand_tree(v) for v in node]
    if isinstance(node, str):
        return _expand_env(node)
    return node


class RetrievalConfig(BaseModel):
    backend: str = "openalex"
    mailto: str = "team@example.com"
    # OpenAlex freemium API key (https://openalex.org/settings/api); env OPENALEX_API_KEY
    openalex_api_key: str = ""
    # Semantic Scholar API key (https://www.semanticscholar.org/product/api); env S2_API_KEY
    semantic_scholar_api_key: str = ""
    min_cited_by: int = 0
    rewrite_queries: bool = True
    multi_query: bool = True
    fetch_multiplier: int = 3
    min_relevance: float = 0.15
    prefer_oa: bool = True
    fetch_fulltext: bool = True
    mineru_cmd: str = "mineru"
    fulltext_cache_dir: str = "data/fulltext"
    # Save retrieved papers under data/<topic>_<YYYYMMDD_HHMMSS>/
    archive_literature: bool = True
    archive_root: str = "data"
    # Sciverse (https://sciverse.space) — optional competition-recommended backend
    sciverse_api_token: str = ""
    sciverse_base_url: str = "https://api.sciverse.space"
    sciverse_mode: str = "meta"  # meta | semantic | hybrid
    # When false, sciverse/s2 empty-or-unconfigured must fail (no silent OpenAlex).
    allow_backend_fallback: bool = True
    # Hugging Face Sci-Base (opendatalab/Sci-Base) — handbook-required corpus
    scibase_dataset: str = "opendatalab/Sci-Base"
    scibase_config: str = "paper"
    scibase_cache_path: str = "data/scibase/materials_cache.jsonl"
    scibase_prefer_cache: bool = True
    scibase_streaming: bool = False  # enable only when intentionally rebuilding/scanning
    scibase_max_scan: int = 5000
    scibase_category_substrings: list[str] = Field(
        default_factory=lambda: ["Materials", "Chemistry", "Physics", "Energy"]
    )


class UnpaywallConfig(BaseModel):
    enabled: bool = True
    email: str = "team@example.com"
    api_base: str = "https://api.unpaywall.org/v2"


class ParserConfig(BaseModel):
    primary: str = "mineru"  # mineru | none
    secondary: str = "grobid"  # grobid | none
    mineru_mode: str = "cli"  # cli | api
    mineru_api_url: str = ""
    mineru_cmd: str = "mineru"
    grobid_url: str = "http://localhost:8070"
    grobid_timeout_s: float = 120.0
    fail_on_grobid_error: bool = False


class ChunkingConfig(BaseModel):
    strategy: str = "section"  # section | recursive
    max_chars: int = 1200
    overlap_chars: int = 150
    respect_sections: bool = True


class IndexConfig(BaseModel):
    backend: str = "file"  # file | qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    collection: str = "materials_evidence"
    vector_size: int = 64
    upsert_on_parse: bool = True


class FulltextConfig(BaseModel):
    download_oa: bool = False
    max_pdf_mb: int = 25
    pdf_cache_dir: str = "data/fulltext/pdfs"
    parse_cache_dir: str = "data/fulltext/parsed"
    chunk_cache_dir: str = "data/fulltext/chunks"
    # Demo profiles may reuse .txt/.md; production should parse OA PDFs instead.
    allow_text_cache: bool = True
    unpaywall: UnpaywallConfig = Field(default_factory=UnpaywallConfig)
    parsers: ParserConfig = Field(default_factory=ParserConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)


class EvidenceRetrievalConfig(BaseModel):
    enabled: bool = True
    top_k: int = 5
    # Soft floor; 0.0 previously let boilerplate chunks win on weak token overlap.
    min_retrieval_score: float = 0.05
    prefer_same_section: bool = True


class StepLLMConfig(BaseModel):
    model: str = ""
    temperature: float = 0.2


class LLMConfig(BaseModel):
    enabled: bool = True
    provider: str = "openai"  # openai | cursor_sdk
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    cursor_api_key: str = ""
    cursor_model: str = "composer-2.5"
    cursor_workspace: str = "."
    temperature: float = 0.2
    max_tokens: int = 4096
    max_retries: int = 2
    # Per-step overrides (empty model → fall back to llm.model)
    rewrite: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.1))
    extract: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.0))
    gap: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.2))
    review: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.1))
    report: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.3))
    route_a: StepLLMConfig = Field(default_factory=lambda: StepLLMConfig(temperature=0.5))

    @property
    def available(self) -> bool:
        if not self.enabled:
            return False
        # Either primary key or the cross-provider fallback key is enough to attempt calls.
        return bool(self.cursor_api_key.strip() or self.api_key.strip())

    def resolve(self, step: str) -> tuple[str, float]:
        step_cfg: StepLLMConfig = getattr(self, step, None) or StepLLMConfig()
        default_model = (
            self.cursor_model if self.provider == "cursor_sdk" else self.model
        )
        model = step_cfg.model.strip() or default_model
        temp = step_cfg.temperature if step_cfg.temperature is not None else self.temperature
        return model, temp


class QualityConfig(BaseModel):
    require_evidence: bool = True
    min_quote_chars: int = 12
    min_evidence_confidence: float = 0.3
    require_next_step: bool = True
    require_falsification: bool = True
    drop_gaps_without_evidence: bool = True
    min_gap_actionability: float = 0.35
    require_quote_substring: bool = False
    require_fulltext_gap_evidence: bool = False
    min_fulltext_paper_ratio: float = 0.0
    reject_evidence_without_provenance: bool = False
    allow_abstract_fallback: bool = True


class PipelineConfig(BaseModel):
    extract: bool = True
    identify_gaps: bool = True
    review_gaps: bool = True
    build_known_table: bool = True
    check_consistency: bool = True
    write_report: bool = True
    audit_log: bool = True


class RouteAConfig(BaseModel):
    enabled: bool = False
    n_iterations: int = 8
    population_size: int = 6
    seed: int = 42
    min_plausibility: float = 0.25
    label_known_vs_new: bool = True
    external_validate: bool = True
    validate_top_k: int = 5
    materials_db: str = "offline"  # offline | materials_project | oqmd | mp_oqmd


class MaterialsDBConfig(BaseModel):
    """External materials database for Route A verification."""

    provider: str = "offline"
    mp_api_key: str = ""
    mp_api_base: str = "https://api.materialsproject.org"
    oqmd_api_base: str = "https://oqmd.org/oqmdapi"
    timeout_s: float = 30.0
    cache_path: str = "data/materials_db_cache.json"
    allow_offline_fallback: bool = True


class AppConfig(BaseModel):
    model_config = {"extra": "ignore"}

    topic: str
    subfield: str = "materials"
    max_papers: int = 20
    year_from: int = 2018
    open_access_only: bool = False
    ontology_path: str = "configs/ontologies/thermoelectrics.yaml"
    seed: int = 42
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    fulltext: FulltextConfig = Field(default_factory=FulltextConfig)
    evidence_retrieval: EvidenceRetrievalConfig = Field(
        default_factory=EvidenceRetrievalConfig
    )
    llm: LLMConfig = Field(default_factory=LLMConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    route_a: RouteAConfig = Field(default_factory=RouteAConfig)
    materials_db: MaterialsDBConfig = Field(default_factory=MaterialsDBConfig)
    output_dir: str = "outputs"
    cache_dir: str = "data/cache"


def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    raw = _expand_tree(raw)
    return AppConfig.model_validate(raw)


def load_ontology(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        # allow relative to materials_agent package root
        alt = Path(__file__).resolve().parents[1] / path
        p = alt if alt.is_file() else p
    if not p.is_file():
        return {}
    with p.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
