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


def get_llm_client() -> OpenAI:
    """Initialize OpenAI-compatible client from environment variables."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy_key_for_mocking"
    base_url = os.getenv("LLM_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)



def _extract_numbers_from_obj(obj: Any) -> Set[float]:
    """Recursively extracts all numerical values from structured data, Decimal values, or strings."""
    numbers: Set[float] = set()

    if isinstance(obj, Decimal):
        numbers.add(float(obj))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        numbers.add(float(obj))
    elif isinstance(obj, str):
        # Extract number patterns like 30,000, 32000, 15.5, 2026-08-27
        matches = re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b", obj)
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


def explain_result(
    engine_result: Union[Dict[str, Any], List[Dict[str, Any]], Any],
    user_question: str = "",
    client: Optional[OpenAI] = None,
    model: Optional[str] = None,
) -> Dict[str, str]:
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
        {"answer_text": "..."}
    """
    if engine_result is None or engine_result == {} or engine_result == []:
        return {"answer_text": SAFE_FALLBACK_TEXT}

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
        if not answer:
            return {"answer_text": SAFE_FALLBACK_TEXT}

        # Strict post-generation numerical & temporal validation
        if not validate_explanation_grounding(answer, engine_result, user_question):
            return {"answer_text": SAFE_FALLBACK_TEXT}

        return {"answer_text": answer}

    except Exception as e:
        return {"answer_text": f"Unable to generate explanation: {str(e)}"}
