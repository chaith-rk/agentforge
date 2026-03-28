#!/usr/bin/env python3
"""Trigger a verification call from the command line.

Usage:
    # Call with test data (calls your phone)
    python scripts/make_call.py --to +12029147774

    # Call with custom candidate data
    python scripts/make_call.py --to +15551234567 \
        --name "Jane Doe" \
        --company "Acme Inc" \
        --title "Software Engineer" \
        --start "2022-01-15" \
        --end "" \
        --status "full-time"
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import settings
from src.vapi.client import VapiClient


# Default test candidate — fictional data, no real PII
DEFAULT_CANDIDATE = {
    "name": "Sarah Johnson",
    "company": "TechCorp Solutions",
    "address": "456 Innovation Drive, Austin, TX 78701",
    "title": "Senior Product Manager",
    "start_date": "2021-03-15",
    "end_date": "",
    "status": "full-time",
    "currently_employed": True,
}


async def make_call(
    to_number: str,
    name: str | None = None,
    company: str | None = None,
    title: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    employment_status: str | None = None,
) -> None:
    """Trigger an outbound verification call."""
    candidate_name = name or DEFAULT_CANDIDATE["name"]
    company_name = company or DEFAULT_CANDIDATE["company"]

    print(f"\n{'='*60}")
    print(f"  VETTY VOICE AI — Outbound Verification Call")
    print(f"{'='*60}")
    print(f"  Calling:    {to_number}")
    print(f"  Candidate:  {candidate_name}")
    print(f"  Company:    {company_name}")
    print(f"  Title:      {title or DEFAULT_CANDIDATE['title']}")
    print(f"  Dates:      {start_date or DEFAULT_CANDIDATE['start_date']} → {end_date or DEFAULT_CANDIDATE['end_date'] or 'present'}")
    print(f"  Status:     {employment_status or DEFAULT_CANDIDATE['status']}")
    print(f"{'='*60}\n")

    if not settings.vapi_api_key:
        print("ERROR: VAPI_API_KEY not set in .env")
        return

    if not settings.vapi_assistant_id:
        print("ERROR: VAPI_ASSISTANT_ID not set in .env")
        return

    if not settings.vapi_phone_number_id:
        print("ERROR: VAPI_PHONE_NUMBER_ID not set in .env")
        return

    metadata = {
        "source": "cli_script",
        "agent_config_id": "employment_verification_v1",
        "subject_name": candidate_name,
        "candidate_claims": {
            "employer_company_name": company_name,
            "position": title or DEFAULT_CANDIDATE["title"],
            "start_date": start_date or DEFAULT_CANDIDATE["start_date"],
            "end_date": end_date or DEFAULT_CANDIDATE["end_date"],
            "employment_status": employment_status or DEFAULT_CANDIDATE["status"],
        },
    }

    async with VapiClient() as client:
        try:
            result = await client.create_call(
                to_number=to_number,
                assistant_id=settings.vapi_assistant_id,
                phone_number_id=settings.vapi_phone_number_id,
                metadata=metadata,
            )
            call_id = result.get("id", "unknown")
            call_status = result.get("status", "unknown")

            print(f"  Call triggered successfully!")
            print(f"  Call ID:  {call_id}")
            print(f"  Status:   {call_status}")
            print(f"\n  Answer your phone and play the role of an employer.")
            print(f"  The AI will verify the candidate details listed above.\n")

        except Exception as e:
            print(f"  ERROR: {e}")
            print(f"  Check your Vapi API key and assistant configuration.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger a AgentForge verification call",
    )
    parser.add_argument(
        "--to", required=True, help="Phone number to call (E.164 format, e.g., +12025551234)"
    )
    parser.add_argument("--name", help="Candidate name")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--title", help="Job title")
    parser.add_argument("--start", help="Start date")
    parser.add_argument("--end", help="End date (empty for currently employed)")
    parser.add_argument("--status", help="Employment status (full-time/part-time/contract)")

    args = parser.parse_args()

    asyncio.run(make_call(
        to_number=args.to,
        name=args.name,
        company=args.company,
        title=args.title,
        start_date=args.start,
        end_date=args.end,
        employment_status=args.status,
    ))


if __name__ == "__main__":
    main()
