"""
FinSight AI Pipeline Demo Script
================================
Demonstrates the end-to-end flow with the real financial engine:
  User Query -> Intent Router -> Deterministic Financial Engine -> Grounded Explainer -> Final Answer
"""

from decimal import Decimal
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

# Reconfigure stdout/stderr for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure workspace root is in sys.path when running `python ai/demo.py` directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

from ai.explainer import FinancialDataJSONEncoder
from ai.pipeline import run_finSight_pipeline
from backend.db import SessionLocal
from backend.seed.generate_synthetic_data import seed_database

from backend.models.user import User

load_dotenv()


def build_mock_router_client(tool_name: str, tool_args: Dict[str, Any]) -> MagicMock:
    """Build mock client for intent router when live API key is not configured."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = tool_name
    mock_tool_call.function.arguments = json.dumps(tool_args)
    mock_message.tool_calls = [mock_tool_call]
    mock_message.content = None
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def build_mock_explainer_client(explanation_text: str) -> MagicMock:
    """Build mock client for explainer when live API key is not configured."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = explanation_text
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def run_pipeline_demo(query: str, user_id: int = 1, db: Optional[Any] = None) -> None:
    """Executes and prints the 3-stage AI pipeline for a user query."""
    print("=" * 70)
    print("USER QUERY:")
    print(f'"{query}"')
    print()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    has_live_key = bool(api_key and api_key not in ("your_api_key_here", "dummy_key_for_mocking"))

    # Step 1: Mock clients calibrated to real engine facts if no live key
    router_client = None
    explainer_client = None

    if not has_live_key:
        if "afford" in query.lower():
            router_client = build_mock_router_client(
                "check_affordability",
                {"amount": 10000, "item_description": "phone"},
            )
            explainer_client = build_mock_explainer_client(
                "Yes, you can afford the phone for ₹10,000. Your remaining balance will be ₹128,372.00 with ₹6,529.00 in upcoming bills reserved."
            )
        elif "balance" in query.lower():
            router_client = build_mock_router_client("get_balance", {})
            explainer_client = build_mock_explainer_client(
                "Your current account balance is ₹138,372.00 as of today."
            )
        elif "food" in query.lower():
            router_client = build_mock_router_client(
                "get_spending_summary",
                {"period": "this_month", "category": "food"},
            )
            explainer_client = build_mock_explainer_client(
                "You have spent a total of ₹14,450.00 on Food this month, which is 21.94% higher compared to your last period."
            )

    result = run_finSight_pipeline(
        user_id=user_id,
        query=query,
        db=db,
        router_client=router_client,
        explainer_client=explainer_client,
    )

    print("ENGINE RESULT:")
    print(json.dumps(result.get("structured_data", {}), cls=FinancialDataJSONEncoder, indent=2, ensure_ascii=False))
    print()

    print("FINAL ANSWER:")
    print(result.get("answer_text", ""))
    print()


def main() -> None:
    seed_database()

    queries = [
        "Can I afford a phone for ₹10000?",
        "What's my balance?",
        "How much did I spend on food this month?",
    ]

    print("\n" + "#" * 70)
    print("       FINSIGHT AI PIPELINE DEMO (Intent Router -> Real Engine -> Explainer)")
    print("#" * 70 + "\n")

    db = SessionLocal()
    try:
        user = db.query(User).first()
        user_id = user.id if user else 1
        for q in queries:
            run_pipeline_demo(q, user_id=user_id, db=db)
    finally:
        db.close()

    print("=" * 70)
    print("Demo completed successfully.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

