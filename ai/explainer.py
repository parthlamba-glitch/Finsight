"""
FinSight Grounded AI Explainer
==============================

ARCHITECTURAL BOUNDARY & SAFETY RULES:
-------------------------------------
1. The explainer receives ONLY structured facts returned by the financial engine.
2. The financial engine is the single source of truth.
3. The explainer must NEVER:
   - access databases
   - access transactions
   - calculate numbers
   - estimate values
   - infer missing information
   - perform financial reasoning
4. The explainer's ONLY job is to convert structured engine output into a short,
   accessible, voice-friendly human response.
5. Every number, date, percentage, category, and financial claim MUST exist
   directly inside `engine_result`.
6. Post-generation validation strictly verifies that all numbers and periods generated
   by the LLM exist in and match the authoritative engine data.
"""

from datetime import date, datetime
from decimal import Decimal
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Union
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from openai import OpenAI

load_dotenv()

EXPLAINER_SYSTEM_PROMPT = """You are FinSight's AI Financial Explainer.
Your ONLY role is to translate structured JSON financial data into a clear, concise, natural-sounding voice response for the user.

CRITICAL GROUNDING & SAFETY RULES:
1. You are only a narrator. The JSON provided is authoritative. Do not add facts.
2. Copy numerical values exactly from JSON.
3. NEVER calculate, estimate, extrapolate, or perform arithmetic on any numbers.
4. Do NOT round numbers.
5. Do NOT convert units or currencies.
6. Do NOT infer missing values.
7. Every number, date, percentage, category, and financial claim MUST exist directly in the provided JSON.
8. If a requested piece of information is missing, do NOT guess. State: "I don't have that information available."
9. If the JSON is empty or contains no relevant data, respond: "I don't have that information available."
10. Temporal & Period Grounding:
    - Strictly observe the `period` attribute in the JSON (e.g. 'last_month', 'this_month', 'this_week', 'last_week').
    - If the JSON specifies 'last_month', you MUST state 'last month' (e.g. "Your food spending last month was ₹10,168.95").
    - NEVER say 'this month' when reporting last month's numbers or facts.
11. Tone & Accessibility:
    - Keep answers concise (1 to 3 clear sentences).
    - Use warm, natural phrasing optimized to be read aloud and easily understood by visually impaired users.
    - Avoid markdown formatting, tables, bullet points, asterisks, or complex jargon.
"""

SAFE_FALLBACK_TEXT = "I don't have that information available."


class FinancialDataJSONEncoder(json.JSONEncoder):
    """Encodes Decimal and datetime objects for safe LLM prompt transmission without precision loss."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


_cached_explainer_client: Optional[OpenAI] = None


def get_llm_client() -> OpenAI:
    """Initialize or reuse OpenAI-compatible client with connection pooling."""
    global _cached_explainer_client
    if _cached_explainer_client is None:
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy_key_for_mocking"
        base_url = os.getenv("LLM_BASE_URL") or None
        _cached_explainer_client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
    return _cached_explainer_client



def _extract_numbers_from_obj(obj: Any) -> Set[float]:
    """Recursively extracts all numerical values from structured data, Decimal values, or strings."""
    numbers: Set[float] = set()

    if isinstance(obj, Decimal):
        numbers.add(float(obj))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.add(float(obj))
    elif isinstance(obj, (datetime, date)):
        numbers.add(float(obj.year))
        numbers.add(float(obj.month))
        numbers.add(float(obj.day))
        if isinstance(obj, datetime):
            numbers.add(float(obj.hour))
            numbers.add(float(obj.minute))
            numbers.add(float(obj.second))
    elif isinstance(obj, str):
        # Extract number patterns like 30,000, 32000, 15.5, 2026-08-27 (replace T for ISO timestamps)
        clean_str = obj.replace("T", " ")
        matches = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", clean_str)
        for m in matches:
            try:
                numbers.add(float(m.replace(",", "")))
            except ValueError:
                pass
        # Also extract conversational amount patterns like '50 thousand', '8k', '20 grand'
        from ai.intent_router import _parse_amount_value
        parsed_amt = _parse_amount_value(obj)
        if parsed_amt is not None:
            numbers.add(parsed_amt)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            numbers.update(_extract_numbers_from_obj(k))
            numbers.update(_extract_numbers_from_obj(v))
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            numbers.update(_extract_numbers_from_obj(item))

    return numbers


def _extract_numbers_from_text(text: str) -> List[float]:
    """Extracts all numerical values from free-form text."""
    numbers: List[float] = []
    matches = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", text)
    for m in matches:
        try:
            numbers.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return numbers


def validate_explanation_grounding(
    answer_text: str,
    engine_result: Any,
    user_question: str = "",
) -> bool:
    """
    Validates that every numerical value in answer_text exists in engine_result (or user_question),
    and that temporal periods (e.g. 'last month') are not contradicted.
    Returns True if valid, False if hallucinated/unsupported numbers or period contradictions are found.
    """
    allowed_numbers = _extract_numbers_from_obj(engine_result)
    if user_question:
        allowed_numbers.update(_extract_numbers_from_obj(user_question))

    answer_numbers = _extract_numbers_from_text(answer_text)

    for num in answer_numbers:
        if num not in allowed_numbers:
            return False

    # Check temporal period consistency if specified in engine result
    if isinstance(engine_result, dict) and engine_result.get("period") == "last_month":
        ans_lower = answer_text.lower()
        if "this month" in ans_lower and "last month" not in ans_lower:
            return False

    return True


def _fast_grounded_explain(engine_result: Any, user_question: str = "") -> Optional[str]:
    """
    Fast-path deterministic narration for authoritative engine results.
    Strictly uses exact numbers from engine_result and passes validate_explanation_grounding.
    Returns generated narration if valid, or None to fall through to LLM explainer.
    """
    if not isinstance(engine_result, dict):
        return None

    q_lower = user_question.lower()

    # 1. Balance
    if "balance" in engine_result and not ("by_category" in engine_result or "can_afford" in engine_result):
        bal = engine_result["balance"]
        if "running low" in q_lower or "low on money" in q_lower:
            text = f"Your current balance is ₹{bal:,.2f} as of today. I don't have a defined threshold for what counts as running low."
        else:
            text = f"Your current account balance is ₹{bal:,.2f} as of today."
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    # 2. Spending Summary
    if "by_category" in engine_result and "total" in engine_result:
        by_cat = engine_result["by_category"]
        period = engine_result.get("period", "this_month")
        period_label = "last month" if period == "last_month" else "this month"
        if "food" in q_lower:
            food_amt = by_cat.get("Food", Decimal("0.00"))
            vs_last = engine_result.get("vs_last_period_pct", {})
            food_pct = vs_last.get("Food") if isinstance(vs_last, dict) else None
            if period == "last_month":
                text = f"Your Food spending last month was ₹{food_amt:,.2f}."
            elif food_pct is not None and food_pct > 0:
                text = f"Your Food spending this month is ₹{food_amt:,.2f}, which is {food_pct}% higher compared to your last period."
            else:
                text = f"Your Food spending this month was ₹{food_amt:,.2f}."
        else:
            tot = engine_result["total"]
            text = f"Your total spending {period_label} is ₹{tot:,.2f}."
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    # 3. Affordability
    if "can_afford" in engine_result and "balance_after" in engine_result and "upcoming_bills" in engine_result:
        can_afford = engine_result["can_afford"]
        bal_after = engine_result["balance_after"]
        upcoming = engine_result["upcoming_bills"]
        if can_afford:
            text = f"Yes, you can afford this purchase. Your remaining balance will be ₹{bal_after:,.2f} with ₹{upcoming:,.2f} reserved for upcoming bills."
        else:
            text = f"No, this purchase exceeds your safe balance after accounting for ₹{upcoming:,.2f} in upcoming bills."
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    # 4. Goals Projection
    if "current_months_remaining" in engine_result:
        months = engine_result["current_months_remaining"]
        goal_name = engine_result.get("goal_name", "Emergency Fund")
        text = f"You are on track to complete your {goal_name} in {months} month(s)."
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    # 5. Payment Preview
    if engine_result.get("intent") == "payment_preview" or ("recipient_name" in engine_result and "amount" in engine_result and "current_balance" in engine_result):
        amt = engine_result.get("amount", Decimal("0.00"))
        rec = engine_result.get("recipient_name", "Recipient")
        if engine_result.get("fraud_warning") or engine_result.get("risk_level") == "high":
            reasons = engine_result.get("risk_reasons", ["High-risk payment detected"])
            reason_str = "; ".join(reasons) if isinstance(reasons, list) else str(reasons)
            text = f"Warning: High risk payment detected. {reason_str}. Would you like to proceed with sending ₹{amt:,.2f} to {rec}?"
        else:
            text = f"Payment preview prepared. Would you like to send ₹{amt:,.2f} to {rec}?"
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    # 6. Payment Execute
    if engine_result.get("intent") == "payment_execute" or engine_result.get("status") == "executed":
        amt = engine_result.get("amount", Decimal("0.00"))
        rec = engine_result.get("recipient_name", "Recipient")
        bal = engine_result.get("new_balance", Decimal("0.00"))
        text = f"Payment of ₹{amt:,.2f} to {rec} was successfully completed. Your new balance is ₹{bal:,.2f}."
        if validate_explanation_grounding(text, engine_result, user_question):
            return text

    return None


def explain_result(
    engine_result: Union[Dict[str, Any], List[Dict[str, Any]], Any],
    user_question: str = "",
    client: Optional[OpenAI] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Converts structured engine output into a grounded, accessible human response.

    Parameters:
    -----------
    engine_result : dict | list | any
        The authoritative structured output returned by the financial engine.
    user_question : str
        The user's natural language question.
    client : OpenAI, optional
        Custom or mocked OpenAI client.
    model : str, optional
        Model override (defaults to LLM_MODEL env var or 'gpt-4o-mini').

    Returns:
    --------
    dict:
        {"answer_text": "...", "timing_ms": float, "explainer_mode": str}
    """
    if engine_result is None or engine_result == {} or engine_result == []:
        return {"answer_text": SAFE_FALLBACK_TEXT, "timing_ms": 0.0, "explainer_mode": "FALLBACK"}

    t0 = time.perf_counter()

    # Fast-path deterministic grounded narration when no custom client mock is provided
    if client is None:
        fast_text = _fast_grounded_explain(engine_result, user_question)
        if fast_text is not None:
            return {
                "answer_text": fast_text,
                "timing_ms": round((time.perf_counter() - t0) * 1000, 2),
                "explainer_mode": "FAST_PATH",
            }

    serialized_data = json.dumps(
        engine_result,
        cls=FinancialDataJSONEncoder,
        indent=2,
        ensure_ascii=False,
    )

    user_prompt = f"""User Question: {user_question or 'Please explain this financial summary.'}

Financial Engine Data (Authoritative):
{serialized_data}

Narrate the response clearly adhering strictly to the grounding rules."""

    llm_model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        llm_client = client or get_llm_client()
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content or ""
        answer = content.strip()
        dt_ms = round((time.perf_counter() - t0) * 1000, 2)

        if not answer:
            return {"answer_text": SAFE_FALLBACK_TEXT, "timing_ms": dt_ms, "explainer_mode": "REAL_LLM"}

        # Strict post-generation numerical & temporal validation
        if not validate_explanation_grounding(answer, engine_result, user_question):
            return {"answer_text": SAFE_FALLBACK_TEXT, "timing_ms": dt_ms, "explainer_mode": "REAL_LLM"}

        return {"answer_text": answer, "timing_ms": dt_ms, "explainer_mode": "REAL_LLM"}

    except Exception as e:
        dt_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"answer_text": f"Unable to generate explanation: {str(e)}", "timing_ms": dt_ms, "explainer_mode": "ERROR"}
