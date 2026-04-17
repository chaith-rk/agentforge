"""Tests for the post-call summary generator.

Summary generation must never block or fail the call-completion path, so
most tests assert graceful-degrade behavior on error/misconfiguration.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.engine import summary_generator
from src.engine.summary_generator import generate_summary


@pytest.fixture
def sample_report() -> dict:
    return {
        "subject_name": "Jane Doe",
        "outcome": "completed",
        "overall_status": "verified",
        "confirmed_facts_count": 2,
        "contradictions_count": 0,
        "items_to_clarify_count": 0,
        "fields": [
            {
                "field_name": "title",
                "display_name": "Job Title",
                "candidate_value": "Engineer",
                "employer_value": "Engineer",
                "status": "verified",
            },
        ],
    }


@pytest.fixture
def sample_transcript() -> list[dict]:
    return [
        {"role": "agent", "content": "Can you confirm the title?"},
        {"role": "employer", "content": "Yes, Engineer."},
    ]


async def test_returns_empty_when_api_key_missing(sample_report, sample_transcript, monkeypatch):
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "")
    result = await generate_summary(sample_transcript, sample_report)
    assert result == ""


async def test_returns_empty_when_no_content(monkeypatch):
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "sk-test")
    result = await generate_summary(transcript=[], report={"fields": []})
    assert result == ""


async def test_returns_summary_on_success(sample_report, sample_transcript, monkeypatch):
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "sk-test")

    mock_response = httpx.Response(
        200,
        json={
            "content": [
                {"type": "text", "text": "The HR rep confirmed employment. No discrepancies found."},
            ],
        },
        request=httpx.Request("POST", summary_generator.ANTHROPIC_API_URL),
    )

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)):
        result = await generate_summary(sample_transcript, sample_report)

    assert "HR rep confirmed" in result


async def test_returns_empty_on_http_error(sample_report, sample_transcript, monkeypatch):
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "sk-test")

    with patch.object(
        httpx.AsyncClient,
        "post",
        new=AsyncMock(side_effect=httpx.ConnectError("boom")),
    ):
        result = await generate_summary(sample_transcript, sample_report)

    assert result == ""


async def test_returns_empty_on_non_2xx(sample_report, sample_transcript, monkeypatch):
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "sk-test")

    mock_response = httpx.Response(
        500,
        text="server error",
        request=httpx.Request("POST", summary_generator.ANTHROPIC_API_URL),
    )

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=mock_response)):
        result = await generate_summary(sample_transcript, sample_report)

    assert result == ""


async def test_redacts_phone_numbers_in_prompt(sample_report, monkeypatch):
    """Defense-in-depth: any PII in the transcript should be redacted before
    being sent to the Anthropic API."""
    monkeypatch.setattr(summary_generator.settings, "anthropic_api_key", "sk-test")
    transcript = [
        {"role": "employer", "content": "My number is 555-123-4567"},
    ]

    captured: dict = {}

    async def fake_post(self, url, json, headers):
        captured["payload"] = json
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "ok"}]},
            request=httpx.Request("POST", url),
        )

    with patch.object(httpx.AsyncClient, "post", new=fake_post):
        await generate_summary(transcript, sample_report)

    prompt_text = captured["payload"]["messages"][0]["content"]
    assert "555-123-4567" not in prompt_text
    assert "[PHONE_REDACTED]" in prompt_text
