"""
FinSight AI Interactive Live Terminal Demo
==========================================

Demonstrates the real FinSight pipeline connected to the REAL SQLite financial engine:
  User Input -> Intent Router -> Deterministic Financial Engine -> Grounded Explainer -> Natural Language Answer

Usage:
  .venv/Scripts/python.exe ai/live_demo.py
"""

from datetime import date, datetime
from decimal import Decimal
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

# Reconfigure stdout/stderr for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure workspace root is in sys.path when running directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from ai.explainer import FinancialDataJSONEncoder, explain_result
from ai.intent_router import _parse_amount_value, route_query
from backend.db import SessionLocal
import backend.engine.financial_engine as real_engine
from backend.models.goal import Goal
from backend.models.user import User
from backend.seed.generate_synthetic_data import seed_database

load_dotenv()


def build_dynamic_mock_router(query: str, context: Optional[Dict[str, Any]] = None) -> MagicMock:
    """Dynamically builds mock OpenAI router client when no live API key is set."""
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()

    q_lower = query.lower()
    ctx = context or {}

    # Contextual resolution for awaiting clarification follow-ups
    if ctx.get("status") == "awaiting_clarification":
        prev_intent = ctx.get("intent")
        if prev_intent == "check_affordability":
            amount = _parse_amount_value(query)
            if amount and amount > 0:
                item_desc = ctx.get("parameters", {}).get("item_description", "item")
                mock_tool_call = MagicMock()
                mock_tool_call.function.name = "check_affordability"
                mock_tool_call.function.arguments = json.dumps({"amount": amount, "item_description": item_desc})
                mock_message.tool_calls = [mock_tool_call]
                mock_message.content = None
                mock_choice.message = mock_message
                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_response
                return mock_client

        elif prev_intent == "project_goal_completion":
            if (
                "emergency" in q_lower
                or "saving" in q_lower
                or "vacation" in q_lower
                or "fund" in q_lower
                or "goal" in q_lower
                or "my" in q_lower
            ):
                goal_name = "Emergency Fund"
                if "vacation" in q_lower:
                    goal_name = "Vacation"
                elif "savings goal" in q_lower:
                    goal_name = "Savings Goal"
                mock_tool_call = MagicMock()
                mock_tool_call.function.name = "project_goal_completion"
                mock_tool_call.function.arguments = json.dumps({"goal_name": goal_name})
                mock_message.tool_calls = [mock_tool_call]
                mock_message.content = None
                mock_choice.message = mock_message
                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                mock_client.chat.completions.create.return_value = mock_response
                return mock_client

        elif prev_intent == "check_scam_message":
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "check_scam_message"
            mock_tool_call.function.arguments = json.dumps({"message": query})
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            mock_choice.message = mock_message
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            return mock_client

    # 0. Payment Confirmation / Execute
    if (
        "confirm payment" in q_lower
        or "yes, confirm" in q_lower
        or "confirm transaction" in q_lower
        or "authorize payment" in q_lower
        or "execute payment" in q_lower
        or (q_lower.strip() in ("confirm", "yes", "authorize") and (ctx.get("status") == "awaiting_confirmation" or ctx.get("confirmation_token") or ctx.get("pending_payment_id")))
    ):
        pending_id = ctx.get("confirmation_token") or ctx.get("pending_payment_id") or "1"
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "payment_execute"
        mock_tool_call.function.arguments = json.dumps({"pending_payment_id": str(pending_id), "confirmation_token": str(pending_id)})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 0.5 Payment Preview
    elif (
        "send " in q_lower
        or "pay " in q_lower
        or "transfer " in q_lower
    ) and not ("what did i spend" in q_lower or "how much did i spend" in q_lower or "why did i spend" in q_lower or "spending" in q_lower):
        amount = _parse_amount_value(query)
        recipient = "Recipient"
        to_match = re.search(r"\bto\s+([A-Za-z0-9\s\.\_]+?)(?:\?|$|\.|\,)", query, re.IGNORECASE)
        if to_match:
            recipient = to_match.group(1).strip()
        elif "dr rao" in q_lower:
            recipient = "Dr Rao"
        elif "unknown vendor" in q_lower:
            recipient = "Unknown Vendor"
        elif "rahul" in q_lower:
            recipient = "Rahul"
        elif "merchant" in q_lower:
            recipient = "Merchant"

        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "payment_preview"
        args = {}
        if amount and amount > 0:
            args["amount"] = amount
        if recipient:
            args["recipient_name"] = recipient
        mock_tool_call.function.arguments = json.dumps(args)
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 1. Scam & Fraud Safety Checker (PROTECT)
    elif (
        "scam" in q_lower
        or "fraud" in q_lower
        or "suspicious" in q_lower
        or "phish" in q_lower
        or "check this message" in q_lower
        or "check a message" in q_lower
        or "check this sms" in q_lower
        or ("otp" in q_lower and ("send" in q_lower or "blocked" in q_lower or "share" in q_lower or "immediately" in q_lower))
        or "kyc is suspended" in q_lower
        or "account will be blocked" in q_lower
    ):
        is_generic = q_lower.strip() in (
            "can you check a message for me?",
            "can you check a message for me",
            "can you check a message?",
            "can you check a message",
            "can you check if a message is a scam?",
            "can you check if a message is a scam",
            "can you check if this message is a scam?",
            "can you check if this message is a scam",
            "check a message for me",
            "check a message",
            "is this a scam?",
            "is this a scam",
            "check this message",
            "does this look suspicious?",
            "is this suspicious?",
        )
        if is_generic:
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "check_scam_message"
            mock_tool_call.function.arguments = json.dumps({})
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
        else:
            cleaned_msg = re.sub(
                r"^(?:is this a scam\??|check this message for fraud:?|check this sms for fraud:?|check this message:?|check this:?|is this suspicious\??)\s*",
                "",
                query,
                flags=re.IGNORECASE,
            ).strip()
            msg_to_check = cleaned_msg if cleaned_msg else query
            mock_tool_call = MagicMock()
            mock_tool_call.function.name = "check_scam_message"
            mock_tool_call.function.arguments = json.dumps({"message": msg_to_check})
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None

    # 2. Affordability
    elif (
        "afford" in q_lower
        or "buy" in q_lower
        or "bought" in q_lower
        or "purchas" in q_lower
        or "can i get" in q_lower
        or "can get" in q_lower
        or "getting a" in q_lower
        or "would a " in q_lower
        or "would buying" in q_lower
        or "affect my finances" in q_lower
    ):
        amount = _parse_amount_value(query)
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "check_affordability"
        args = {}
        if amount and amount > 0:
            args["amount"] = amount
            args["item_description"] = "item"
        mock_tool_call.function.arguments = json.dumps(args)
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 3. Goals
    elif (
        "goal" in q_lower
        or "emergency fund" in q_lower
        or "emergency savings" in q_lower
        or "vacation" in q_lower
        or "when will i reach" in q_lower
        or "when will i hit" in q_lower
        or "how long until" in q_lower
        or "finish that" in q_lower
        or "finish my" in q_lower
    ):
        goal_name = "Emergency Fund"
        if "vacation" in q_lower:
            goal_name = "Vacation"
        elif "savings goal" in q_lower:
            goal_name = "Savings Goal"
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "project_goal_completion"
        mock_tool_call.function.arguments = json.dumps({"goal_name": goal_name})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    elif "save" in q_lower and ("how much longer" in q_lower or "how long" in q_lower):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "project_goal_completion"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 4. Insights / Trends / Why / Anomalies
    elif (
        "why" in q_lower
        or "insight" in q_lower
        or "trend" in q_lower
        or "pattern" in q_lower
        or "unusual" in q_lower
        or "what changed" in q_lower
        or "what's changed" in q_lower
        or "weird" in q_lower
        or "spike" in q_lower
        or "noticed about my spending" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_insights"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 5. Spending Summary
    elif (
        "spend" in q_lower
        or "spent" in q_lower
        or "spending" in q_lower
        or "disappear" in q_lower
        or "where did" in q_lower
        or "where is" in q_lower
        or "money go" in q_lower
        or "blown" in q_lower
        or "food" in q_lower
        or "expenses" in q_lower
        or "expense" in q_lower
        or "what have i been" in q_lower
    ):
        category = "Food" if "food" in q_lower else None
        period = "last_month" if "last month" in q_lower else "this_month"
        args = {"period": period}
        if category:
            args["category"] = category
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_spending_summary"
        mock_tool_call.function.arguments = json.dumps(args)
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 6. Balance & Funds
    elif (
        "balance" in q_lower
        or "how much money" in q_lower
        or "money do i have" in q_lower
        or "net worth" in q_lower
        or "is left" in q_lower
        or "i have left" in q_lower
        or "i got left" in q_lower
        or "left in my" in q_lower
        or "sitting in my" in q_lower
        or "mine right now" in q_lower
        or "available" in q_lower
        or "cash" in q_lower
        or "running low" in q_lower
        or "low on money" in q_lower
        or "what i've got" in q_lower
        or "what i got" in q_lower
        or "see in my account" in q_lower
        or "check my funds" in q_lower
        or "check balance" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_balance"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 7. UI Control: sync_bank
    elif (
        "sync" in q_lower
        or "refresh my account" in q_lower
        or "refresh account" in q_lower
        or "update my bank" in q_lower
        or "bank update" in q_lower
        or "bank refresh" in q_lower
        or "sync karo" in q_lower
        or "update kar do" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "sync_bank"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 8. UI Control: read_recent_transactions
    elif (
        ("read" in q_lower and "transaction" in q_lower)
        or "recent transaction" in q_lower
        or "last transaction" in q_lower
        or "transactions kya hai" in q_lower
        or "transaction kya hai" in q_lower
        or "transactions sunao" in q_lower
        or "show my recent transactions" in q_lower
        or "show recent transactions" in q_lower
        or "what did i spend recently" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "read_recent_transactions"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 9. UI Control: read_goals
    elif (
        ("read" in q_lower and "goal" in q_lower)
        or "tell me my goal" in q_lower
        or "tell me my goals" in q_lower
        or "goal progress kya hai" in q_lower
        or "goals sunao" in q_lower
        or "show my goals" in q_lower
        or "show goals" in q_lower
        or "mera goal" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "read_goals"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    # 10. UI Control: upload_document
    elif (
        ("upload" in q_lower and ("document" in q_lower or "statement" in q_lower or "file" in q_lower or "bank statement" in q_lower))
        or ("scan" in q_lower and ("statement" in q_lower or "document" in q_lower))
        or "statement scan karo" in q_lower
        or "statement upload karo" in q_lower
        or "scan karo" in q_lower
    ):
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "upload_document"
        mock_tool_call.function.arguments = json.dumps({})
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None

    else:
        mock_message.tool_calls = None
        mock_message.content = "I am FinSight, your personal finance assistant. I can only assist with personal financial inquiries."

    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


def build_dynamic_mock_explainer(engine_result: Any, query: str) -> MagicMock:
    """
    Dynamically generates grounded explanation client using REAL engine result facts.
    Never hardcodes numbers; strictly narrates values returned by the real financial engine.
    """
    mock_client = MagicMock()
    mock_choice = MagicMock()

    q_lower = query.lower()

    if isinstance(engine_result, dict) and engine_result.get("intent") == "payment_preview":
        amt = engine_result.get("amount", Decimal("0.00"))
        rec = engine_result.get("recipient_name", "Recipient")
        if engine_result.get("fraud_warning") or engine_result.get("risk_level") == "high":
            reasons = engine_result.get("risk_reasons", ["High-risk payment detected"])
            reason_str = "; ".join(reasons) if isinstance(reasons, list) else str(reasons)
            text = f"Warning: High risk payment detected. {reason_str}. Would you like to proceed with sending ₹{amt:,.2f} to {rec}?"
        else:
            text = f"Payment preview prepared. Would you like to send ₹{amt:,.2f} to {rec}?"

    elif isinstance(engine_result, dict) and engine_result.get("intent") == "payment_execute":
        amt = engine_result.get("amount", Decimal("0.00"))
        rec = engine_result.get("recipient_name", "Recipient")
        bal = engine_result.get("new_balance", Decimal("0.00"))
        text = f"Payment of ₹{amt:,.2f} to {rec} was successfully completed. Your new balance is ₹{bal:,.2f}."

    elif isinstance(engine_result, dict) and "balance" in engine_result:
        bal = engine_result["balance"]
        if "running low" in q_lower or "low on money" in q_lower:
            text = f"Your current balance is ₹{bal:,.2f} as of today. I don't have a defined threshold for what counts as running low."
        else:
            text = f"Your authoritative balance is ₹{bal:,.2f}."

    elif isinstance(engine_result, dict) and "by_category" in engine_result:
        by_cat = engine_result["by_category"]
        vs_last = engine_result.get("vs_last_period_pct", {})
        period = engine_result.get("period", "this_month")
        period_label = "last month" if period == "last_month" else "this month"
        if "food" in q_lower or (isinstance(by_cat, dict) and "Food" in by_cat and len(by_cat) == 1):
            food_amt = by_cat.get("Food", Decimal("0.00")) if isinstance(by_cat, dict) else Decimal("0.00")
            text = f"You spent ₹{food_amt:,.2f} on Food {period_label}."
        else:
            tot = engine_result.get("total", Decimal("0.00"))
            text = f"Your total spending {period_label} is ₹{tot:,.2f}."

    elif isinstance(engine_result, dict) and "can_afford" in engine_result:
        can_afford = engine_result["can_afford"]
        bal_after = engine_result["balance_after"]
        upcoming = engine_result["upcoming_bills"]
        if can_afford:
            text = f"Yes, you can afford this purchase. Your remaining balance will be ₹{bal_after:,.2f} with ₹{upcoming:,.2f} reserved for upcoming bills."
        else:
            text = f"No, this purchase exceeds your safe balance after accounting for ₹{upcoming:,.2f} in upcoming bills."

    elif isinstance(engine_result, dict) and "current_months_remaining" in engine_result:
        months = engine_result["current_months_remaining"]
        goal_name = engine_result.get("goal_name", "Emergency Fund")
        text = f"You are on track to complete your {goal_name} in {months} month(s)."

    elif isinstance(engine_result, list) and len(engine_result) > 0:
        first_insight = engine_result[0]
        cat = first_insight.get("category", "spending")
        pct = first_insight.get("pct", "0")
        text = f"Your {cat.lower()} spending increased by {pct}% this month."

    elif isinstance(engine_result, dict) and "insights" in engine_result:
        ins = engine_result["insights"]
        if ins and len(ins) > 0:
            first = ins[0]
            cat = first.get("category", "spending")
            text = f"Your {cat.lower()} spending has shown notable patterns."
        else:
            text = "No unusual spending patterns or anomalies detected."

    else:
        text = "I don't have that information available."

    mock_choice.message.content = text
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client




def process_query(question: str, user_id: int, db: SessionLocal) -> None:
    """Processes a user question through the complete real pipeline and prints formatted output."""
    print("USER:")
    print(question)
    print()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    has_live_key = bool(api_key and api_key not in ("your_api_key_here", "dummy_key_for_mocking"))

    # Resolve context goals from real database
    context_goals = {}
    db_goals = db.query(Goal).filter(Goal.user_id == user_id).all()
    if db_goals:
        context_goals = {g.name.lower(): g.id for g in db_goals}

    router_client = None if has_live_key else build_dynamic_mock_router(question)

    # 1. Intent Routing
    router_result = route_query(
        query=question,
        user_id=str(user_id),
        context={"goals": context_goals},
        client=router_client,
    )

    status = router_result.get("status")

    if status == "clarification_needed":
        clarification_text = router_result.get("question", "Could you please clarify your question?")
        print("INTENT:")
        print("None (Clarification Needed)")
        print()
        print("ARGUMENTS:")
        print("None (No engine call)")
        print()
        print("ENGINE RESULT:")
        print("None (Engine was not invoked)")
        print()
        print("FINSIGHT:")
        print(clarification_text)
        print()
        print("=" * 50)
        print()
        return

    if status != "success":
        error_msg = router_result.get("message", "An error occurred.")
        print("INTENT:")
        print("error")
        print()
        print("ARGUMENTS:")
        print("{}")
        print()
        print("ENGINE RESULT:")
        print(f'{{"status": "error", "message": "{error_msg}"}}')
        print()
        print("FINSIGHT:")
        print("I encountered an issue processing your request.")
        print()
        print("=" * 50)
        print()
        return

    # 2. Extract Intent & Dispatch to Real Financial Engine
    func_name = router_result.get("function_name", "")
    args = router_result.get("arguments", {})

    print("INTENT:")
    print(func_name)
    print()

    # Dispatch to deterministic backend engine via dispatcher
    from backend.engine.dispatcher import dispatch_intent

    engine_result = dispatch_intent(
        user_id=user_id,
        intent_data={"intent": func_name, "arguments": args},
        db=db,
    )
    passed_args = args

    print("ARGUMENTS:")
    print(json.dumps(passed_args, cls=FinancialDataJSONEncoder, indent=2))
    print()

    print("ENGINE RESULT:")
    print(json.dumps(engine_result, cls=FinancialDataJSONEncoder, indent=2, ensure_ascii=False))
    print()

    # 3. Grounded Explanation Generation
    explainer_client = None if has_live_key else build_dynamic_mock_explainer(engine_result, question)
    explanation = explain_result(
        engine_result=engine_result,
        user_question=question,
        client=explainer_client,
    )

    print("FINSIGHT:")
    print(explanation.get("answer_text", ""))
    print()
    print("=" * 50)
    print()


def run_demo() -> None:
    # Ensure database is seeded with real deterministic financial data
    seed_database()

    db = SessionLocal()
    try:
        user = db.query(User).first()
        user_id = user.id if user else 1


        print("==================================================")
        print("FINsight REAL AI DEMO")
        print("==================================================")
        print("Connected to REAL SQLite financial engine")
        print(f"Demo user: {user_id}")
        print()
        print("Type a question or type 'exit' to quit.")
        print("==================================================\n")

        test_questions = [
            "What's my balance?",
            "How much did I spend on food this month?",
            "Can I afford a phone for ₹10,000?",
            "When will I reach my emergency fund?",
            "Why did I spend more this month?",
            "Can I afford it?",
            "Tell me something unrelated like the weather.",
        ]

        # If running in batch/test mode or non-interactive terminal
        if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
            while True:
                try:
                    user_input = input("USER:\n").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit", "q"):
                        print("Goodbye!")
                        break
                    print()
                    process_query(user_input, user_id=user_id, db=db)
                except (KeyboardInterrupt, EOFError):
                    print("\nGoodbye!")
                    break
        else:
            # Run all standard verification test questions
            for q in test_questions:
                process_query(q, user_id=user_id, db=db)

            # If connected to an interactive TTY, also allow user to type additional questions
            if sys.stdin.isatty():
                print("Interactive mode active. Type your question below (or 'exit' to quit):\n")
                while True:
                    try:
                        user_input = input("USER: ").strip()
                        if not user_input:
                            continue
                        if user_input.lower() in ("exit", "quit", "q"):
                            print("Goodbye!")
                            break
                        print()
                        process_query(user_input, user_id=user_id, db=db)
                    except (KeyboardInterrupt, EOFError):
                        print("\nGoodbye!")
                        break

    finally:
        db.close()


if __name__ == "__main__":
    run_demo()
