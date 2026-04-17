"""Post-call narrative summary generation via Anthropic's API.

Produces a short factual summary of a completed verification call for
display in the post-call report. Fails gracefully — if the Anthropic
API is unreachable or unconfigured, we return an empty string rather
than fail the call.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.config.settings import settings
from src.middleware.security import redact_pii

logger = structlog.get_logger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SUMMARY_PROMPT = """You are summarizing a completed employment/education verification call for a \
background screening report.

Write a neutral, factual 2-4 sentence summary covering:
1. Who answered and their role (if stated)
2. What was confirmed vs. what differed from the candidate's claims
3. Any items the employer couldn't or wouldn't verify
4. The overall outcome (clean verification, discrepancies found, redirected to third party, etc.)

Be precise. Do not speculate. Do not include PII like full phone numbers or SSNs. Do not include \
any narration, preamble, or sign-off — output the summary sentences only.

--- VERIFICATION RESULTS ---
{results}

--- TRANSCRIPT ---
{transcript}
"""


def _format_results(report: dict[str, Any]) -> str:
    """Render the verification results dict as a compact string for the prompt."""
    lines = [
        f"Subject: {report.get('subject_name', 'unknown')}",
        f"Outcome: {report.get('outcome', 'unknown')}",
        f"Overall status: {report.get('overall_status', 'unknown')}",
        f"Confirmed facts: {report.get('confirmed_facts_count', 0)}",
        f"Contradictions: {report.get('contradictions_count', 0)}",
        f"Items to clarify: {report.get('items_to_clarify_count', 0)}",
        "",
        "Per-field:",
    ]
    for fv in report.get("fields", []):
        lines.append(
            f"- {fv.get('display_name') or fv.get('field_name')}: "
            f"candidate claimed {fv.get('candidate_value')!r}, "
            f"employer said {fv.get('employer_value')!r} "
            f"[{fv.get('status')}]"
        )
    return "\n".join(lines)


def _format_transcript(transcript: list[dict[str, Any]]) -> str:
    """Render transcript entries as 'role: content' lines."""
    return "\n".join(
        f"{entry.get('role', 'unknown')}: {entry.get('content', '')}"
        for entry in transcript
        if entry.get("content")
    )


async def generate_summary(
    transcript: list[dict[str, Any]],
    report: dict[str, Any],
) -> str:
    """Generate a post-call narrative summary via Claude.

    Returns an empty string on any failure — summary generation must never
    block or fail the call-completion path.
    """
    if not settings.anthropic_api_key:
        logger.info("summary_skipped_no_api_key")
        return ""

    if not transcript and not report.get("fields"):
        logger.info("summary_skipped_no_content")
        return ""

    prompt_body = SUMMARY_PROMPT.format(
        results=redact_pii(_format_results(report)),
        transcript=redact_pii(_format_transcript(transcript)),
    )

    payload = {
        "model": settings.summary_model,
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt_body}],
    }

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("summary_generation_failed", error=str(exc))
        return ""

    try:
        blocks = data.get("content", [])
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        ).strip()
    except (AttributeError, TypeError) as exc:
        logger.warning("summary_parse_failed", error=str(exc))
        return ""

    logger.info("summary_generated", length=len(text))
    return text
