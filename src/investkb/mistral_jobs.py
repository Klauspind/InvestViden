"""Persistent, explicitly confirmed Mistral extraction jobs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .mistral_api import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_SECONDS,
    run_mistral_extractions,
)
from .openai_api import OpenAITask, plan_openai_extractions
from .repository import KnowledgeBase
from .validation import ValidationError


PRICING_VERSION = "mistral-standard-2026-09-14"
INPUT_USD_PER_MILLION_TOKENS = 0.50
OUTPUT_USD_PER_MILLION_TOKENS = 1.50
DEFAULT_COST_LIMIT_USD = 0.10
PROMPT_OVERHEAD_TOKENS = 4_000

Transport = Callable[[dict[str, Any], str, int], dict[str, Any]]


def estimate_task_cost(task: OpenAITask, max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> float:
    if max_output_tokens != DEFAULT_MAX_OUTPUT_TOKENS:
        raise ValidationError("Jobkøens første version bruger fast 16.000 max output-tokens")
    buffered_input = int(task.estimated_input_tokens * 1.25) + PROMPT_OVERHEAD_TOKENS
    return (
        buffered_input * INPUT_USD_PER_MILLION_TOKENS
        + max_output_tokens * OUTPUT_USD_PER_MILLION_TOKENS
    ) / 1_000_000


def create_mistral_job(
    kb: KnowledgeBase,
    incoming_dir: Path,
    *,
    limit: int = 1,
    model: str = DEFAULT_MODEL,
    cost_limit_usd: float = DEFAULT_COST_LIMIT_USD,
    approvals: dict[str, str] | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    if source_ids is not None:
        limit = len(source_ids)
    tasks = plan_openai_extractions(kb, incoming_dir, limit, approvals, source_ids)
    if not tasks:
        raise ValidationError("Ingen kilder er klar til et Mistral-job")
    estimated = sum(estimate_task_cost(task) for task in tasks)
    job_id = kb.create_ai_job(
        "mistral", model, [task.source_id for task in tasks], estimated, cost_limit_usd
    )
    result = kb.ai_job(job_id)
    result.update({
        "pricing_version": PRICING_VERSION,
        "input_usd_per_million_tokens": INPUT_USD_PER_MILLION_TOKENS,
        "output_usd_per_million_tokens": OUTPUT_USD_PER_MILLION_TOKENS,
    })
    return result


def execute_mistral_job(
    kb: KnowledgeBase,
    job_id: str,
    schema_path: Path,
    incoming_dir: Path,
    audit_dir: Path,
    *,
    preferences: dict[str, Any] | None = None,
    api_key: str | None = None,
    transport: Transport | None = None,
    retry_source_ids: list[str] | None = None,
) -> dict[str, Any]:
    job = kb.ai_job(job_id)
    if job["provider"] != "mistral":
        raise ValidationError("Jobbet er ikke et Mistral-job")
    selected = kb.start_ai_job(job_id, retry_source_ids)
    for item in selected:
        source_id = str(item["source_version_id"])
        approval = {source_id: str(item["sha256"])}
        try:
            result = run_mistral_extractions(
                kb,
                schema_path,
                incoming_dir,
                audit_dir,
                preferences,
                str(job["model"] or DEFAULT_MODEL),
                DEFAULT_MAX_OUTPUT_TOKENS,
                DEFAULT_TIMEOUT_SECONDS,
                DEFAULT_TEMPERATURE,
                1,
                api_key=api_key,
                transport=transport,
                approvals=approval,
                source_ids=[source_id],
            )
            if result["errors"] or result["sent"] != 1:
                error = result["errors"][0]["error"] if result["errors"] else "Kilden gav intet valideret svar"
                kb.finish_ai_job_item(str(item["id"]), success=False, error=error)
                continue
            usage = result["usage"]
            prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
            completion_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
            actual_cost = None
            if isinstance(prompt_tokens, int) and isinstance(completion_tokens, int):
                actual_cost = (
                    prompt_tokens * INPUT_USD_PER_MILLION_TOKENS
                    + completion_tokens * OUTPUT_USD_PER_MILLION_TOKENS
                ) / 1_000_000
            response_id = None
            if result["audits"]:
                audit = json.loads(Path(result["audits"][0]).read_text(encoding="utf-8"))
                response_id = audit.get("response_id")
            kb.finish_ai_job_item(
                str(item["id"]), success=True, response_id=response_id,
                prompt_tokens=prompt_tokens if isinstance(prompt_tokens, int) else None,
                completion_tokens=completion_tokens if isinstance(completion_tokens, int) else None,
                actual_cost_usd=actual_cost,
            )
        except (ValidationError, RuntimeError, OSError, ValueError) as exc:
            kb.finish_ai_job_item(str(item["id"]), success=False, error=str(exc))
    kb.finish_ai_job(job_id)
    return kb.ai_job(job_id)
