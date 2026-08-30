"""
FinSight AI Scam & Fraud Safety Checker (PROTECT Pillar)
=========================================================

ARCHITECTURAL BOUNDARIES & SAFETY RULES:
-----------------------------------------
1. This is a PATTERN-BASED LLM SAFETY ASSESSMENT, NOT a deterministic fraud verification system.
2. It is NOT a deterministic fraud classifier and CANNOT definitively prove that a sender is fraudulent.
3. It analyzes ONLY the supplied message text. It never accesses accounts, databases, or transactions.
4. It must NEVER invent suspicious content or facts that are not present in the supplied message.
5. All indicators and explanations MUST be strictly grounded in quoted or paraphrased evidence from the text.
6. If evidence is weak or ambiguous, it must explicitly state that confidence is limited.
7. NEVER ask the user to share sensitive credentials:
   - One-Time Passwords (OTP)
   - Personal Identification Numbers (PIN)
   - Card Verification Values (CVV)
   - Passwords
   - Full credit/debit card numbers
   - Online banking credentials
8. The deterministic financial engine is completely untouched by this module.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from openai import OpenAI

load_dotenv()

SCAM_CHECKER_SYSTEM_PROMPT = """You are FinSight's AI Scam and Fraud Safety Checker, part of the PROTECT pillar.
Your role is to analyze pasted SMS, chat, or email messages to identify suspicious characteristics and evaluate potential scam/fraud risk.

CRITICAL ARCHITECTURAL & SAFETY RULES:
1. PATTERN-BASED ASSESSMENT: This is an AI pattern-based safety assessment, NOT a deterministic fraud verification system. You cannot prove whether a sender is genuinely fraudulent.
2. STRICT GROUNDING: Analyze ONLY the supplied message text. Every indicator, piece of evidence, and explanation MUST be directly quoted or paraphrased from the supplied text.
3. NO HALLUCINATIONS: NEVER invent, assume, or extrapolate suspicious facts, links, or phone numbers that do not appear in the text.
4. LIMITED EVIDENCE: If the message has weak or ambiguous indicators, state clearly that confidence is limited.
5. NO CREDENTIAL SOLICITATION: NEVER ask the user to provide their OTP, PIN, CVV, password, card number, or banking credentials.
6. EXPLANATORY FOCUS: Do not simply return a risk label. You MUST explain WHY specific elements are risky and provide actionable protective steps.

PATTERNS TO EVALUATE:
- Urgency / Extreme time pressure (e.g., "within 10 minutes", "immediately", "act now")
- Threats of account suspension, blocking, legal action, or electricity cutoff
- Requests for OTP, PIN, password, CVV, or full card details
- Unusual payment requests or demands for urgent money transfers
- Impersonation of trusted entities (banks like SBI/HDFC, tax authorities, courier services, utility companies)
- Suspicious rewards, lottery wins, refunds, or processing fee demands
- Suspicious links (shortened URLs, bit.ly, lookalike domain names, unverified links)
- Requests to install applications (APK files, remote desktop tools like AnyDesk, TeamViewer, QuickSupport)
- KYC update/verification threats requiring sensitive personal or financial info
- Sender/claim inconsistencies inferable directly from the text
- Emotional manipulation, fear tactics, or excitement manipulation

OUTPUT FORMAT:
You MUST respond with a valid, raw JSON object matching this exact schema:
{
  "risk_level": "low" | "medium" | "high",
  "looks_suspicious": true | false,
  "indicators": [
    {
      "type": "urgency" | "otp_request" | "account_threat" | "credential_request" | "payment_demand" | "fake_reward" | "suspicious_link" | "app_install_request" | "kyc_threat" | "impersonation" | "fear_tactics" | "other",
      "evidence": "Exact quote or close paraphrase from the message"
    }
  ],
  "explanation": "Short, clear, grounded explanation of the findings.",
  "recommended_actions": [
    "Specific actionable recommendation grounded in safety.",
    "Another actionable recommendation."
  ],
  "limitations": "This is an AI pattern-based safety assessment, not a deterministic fraud verification system."
}

Do not include any introductory or concluding conversational text outside the JSON object.
"""

DEFAULT_LIMITATIONS = (
    "This is an AI pattern-based safety assessment, not a deterministic fraud verification system."
)


def get_llm_client() -> OpenAI:
    """Initializes OpenAI-compatible client configured from environment variables."""
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "dummy_key_for_mocking"
    base_url = os.getenv("LLM_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)


def _clean_json_text(raw_text: str) -> str:
    """Extracts JSON object substring from raw LLM output, removing markdown fences if present."""
    text = raw_text.strip()
    # Strip markdown code blocks
    if "```json" in text:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
    elif "```" in text:
        text = re.sub(r"```\s*", "", text)

    text = text.strip()
    # Locate first '{' and last '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1]
    return text


def _build_safe_error_response(error_reason: str) -> Dict[str, Any]:
    """Generates a transparent fallback response when the LLM service fails or returns invalid data."""
    return {
        "risk_level": "medium",
        "looks_suspicious": False,
        "indicators": [],
        "explanation": f"Unable to complete safety assessment: {error_reason}. Please exercise caution with unsolicited messages.",
        "recommended_actions": [
            "Do not share OTP, PIN, password, or sensitive details with anyone.",
            "Contact the official institution directly through verified contact numbers or official mobile apps.",
            "Do not click on links or install applications from unverified messages.",
        ],
        "limitations": f"{DEFAULT_LIMITATIONS} Note: Assessment was incomplete due to a service error.",
    }


def _validate_and_sanitize_result(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures the parsed JSON conforms strictly to the FinSight Scam Safety contract."""
    # 1. Sanitize risk_level
    raw_risk = str(parsed.get("risk_level", "medium")).lower().strip()
    if raw_risk not in ("low", "medium", "high"):
        raw_risk = "medium"

    # 2. Sanitize looks_suspicious
    looks_suspicious = bool(parsed.get("looks_suspicious", raw_risk in ("medium", "high")))

    # 3. Sanitize indicators list
    raw_indicators = parsed.get("indicators")
    sanitized_indicators: List[Dict[str, str]] = []
    if isinstance(raw_indicators, list):
        for ind in raw_indicators:
            if isinstance(ind, dict) and "type" in ind and "evidence" in ind:
                sanitized_indicators.append({
                    "type": str(ind["type"]).strip(),
                    "evidence": str(ind["evidence"]).strip(),
                })

    # 4. Sanitize explanation
    explanation = str(parsed.get("explanation", "")).strip()
    if not explanation:
        explanation = "Safety evaluation completed based on detected message patterns."

    # 5. Sanitize recommended_actions
    raw_actions = parsed.get("recommended_actions")
    sanitized_actions: List[str] = []
    if isinstance(raw_actions, list):
        for act in raw_actions:
            if isinstance(act, str) and act.strip():
                sanitized_actions.append(act.strip())

    if not sanitized_actions:
        sanitized_actions = [
            "Verify any suspicious requests through the organization's official app or verified contact number.",
            "Never share your OTP, PIN, CVV, or passwords under any circumstance.",
        ]

    # 6. Ensure limitations statement is always explicit
    limitations = parsed.get("limitations")
    if not limitations or not isinstance(limitations, str) or "pattern-based" not in limitations.lower():
        limitations = DEFAULT_LIMITATIONS

    return {
        "risk_level": raw_risk,
        "looks_suspicious": looks_suspicious,
        "indicators": sanitized_indicators,
        "explanation": explanation,
        "recommended_actions": sanitized_actions,
        "limitations": limitations,
    }


def assess_scam_message(
    message: str,
    client: Optional[Any] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs a pattern-based LLM safety assessment on a user-submitted message/SMS.

    Parameters:
    -----------
    message : str
        The raw text of the message, SMS, or email to evaluate.
    client : OpenAI, optional
        Custom or mocked OpenAI client.
    model : str, optional
        Model identifier override.

    Returns:
    --------
    dict:
        {
            "risk_level": "low" | "medium" | "high",
            "looks_suspicious": bool,
            "indicators": [{"type": str, "evidence": str}],
            "explanation": str,
            "recommended_actions": [str],
            "limitations": str
        }
    """
    # Defensive handling for empty or whitespace-only inputs
    if message is None or not isinstance(message, str) or not message.strip():
        return {
            "risk_level": "low",
            "looks_suspicious": False,
            "indicators": [],
            "explanation": "No message text was provided to analyze.",
            "recommended_actions": [
                "Paste the suspicious message or SMS text you wish to check.",
                "Never share OTPs, passwords, or banking PINs with anyone.",
            ],
            "limitations": DEFAULT_LIMITATIONS,
        }

    clean_message = message.strip()

    # User prompt
    user_prompt = f"Please analyze the following message for scam, phishing, and fraud indicators:\n\n---\n{clean_message}\n---"

    llm_model = model or os.getenv("LLM_MODEL", "gemini-3.5-flash-lite")

    try:
        llm_client = client if client is not None else get_llm_client()
        response = llm_client.chat.completions.create(
            model=llm_model,
            messages=[
                {"role": "system", "content": SCAM_CHECKER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content or ""
        cleaned_json = _clean_json_text(content)

        if not cleaned_json:
            return _build_safe_error_response("empty response from AI model")

        parsed_result = json.loads(cleaned_json)
        if not isinstance(parsed_result, dict):
            return _build_safe_error_response("malformed model output structure")

        return _validate_and_sanitize_result(parsed_result)

    except json.JSONDecodeError:
        return _build_safe_error_response("model output could not be parsed as valid JSON")
    except Exception as e:
        return _build_safe_error_response(f"AI service error ({str(e)})")


def format_scam_conversational_response(scam_result: Dict[str, Any]) -> str:
    """
    Translates structured scam assessment into a natural, voice-friendly, and accessible response.
    Includes risk level, grounded indicators (why), actionable protective steps, and limitations disclaimer.
    """
    risk_level = str(scam_result.get("risk_level", "medium")).upper().strip()
    looks_suspicious = bool(scam_result.get("looks_suspicious", False))
    indicators = scam_result.get("indicators", [])
    explanation = scam_result.get("explanation", "")
    actions = scam_result.get("recommended_actions", [])
    limitations = scam_result.get(
        "limitations",
        DEFAULT_LIMITATIONS,
    )

    lines: List[str] = []

    # 1. Headline
    if risk_level == "HIGH":
        lines.append("⚠️ This message looks highly suspicious.")
    elif risk_level == "MEDIUM" or looks_suspicious:
        lines.append("⚠️ This message looks suspicious or ambiguous.")
    else:
        lines.append("✅ This message does not show obvious scam patterns.")

    # 2. Risk Level
    lines.append(f"\nRisk Level: {risk_level}")

    # 3. Why / Grounded Indicators
    if indicators:
        lines.append("\nWhy:")
        for ind in indicators:
            ind_type = str(ind.get("type", "pattern")).replace("_", " ")
            evidence = str(ind.get("evidence", "")).strip()
            if evidence:
                lines.append(f"• {ind_type.title()}: \"{evidence}\"")
            else:
                lines.append(f"• {ind_type.title()} pattern detected.")
    elif explanation:
        lines.append(f"\nWhy:\n• {explanation}")

    # 4. What you should do
    if actions:
        lines.append("\nWhat you should do:")
        for act in actions:
            lines.append(f"• {act}")

    # 5. Limitations disclaimer
    lines.append(f"\nImportant: {limitations}")

    return "\n".join(lines)
