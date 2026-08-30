"""
FinSight LLM Client Wrapper.
Provides high-level routing and explanation methods, delegating to intent_router and explainer.

ARCHITECTURAL PRINCIPLES:
- Never calculates financial values or accesses database directly.
- The LLM is only used for semantic parsing (routing) and grounded narration (explaining).
"""

import os
from typing import Dict, Any, Optional, Tuple
from ai.intent_router import route_query
from ai.explainer import explain_result


class LLMClient:
    """Wrapper for LLM tool routing and grounded explanation."""

    @staticmethod
    def call_tool_router(
        query: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Routes natural language query to structured intent.
        Returns (intent_data, error_or_clarification_question).
        """
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        has_live_key = bool(
            api_key
            and api_key not in ("your_api_key_here", "dummy_key_for_mocking", "mock-gemini-live-key", "")
        )

        router_client = None
        if not has_live_key:
            from ai.live_demo import build_dynamic_mock_router

            router_client = build_dynamic_mock_router(query, context=context)

        result = route_query(query=query, user_id=user_id, context=context, client=router_client)
        status = result.get("status")

        if status == "success":
            intent_data = {
                "intent": result.get("function_name"),
                "arguments": result.get("arguments", {}),
            }
            return intent_data, None
        elif status == "clarification_needed":
            question = result.get("question", "Could you please clarify?")
            return {
                "status": "clarification_needed",
                "question": question,
                "intent": result.get("intent", "clarification_needed"),
                "extracted_parameters": result.get("extracted_parameters", {}),
            }, question
        else:
            err = result.get("message", "Routing failed.")
            return {"status": "error", "message": err}, err

    @staticmethod
    def explain_facts(
        engine_facts: Any,
        user_query: str = "",
    ) -> Tuple[str, str, Optional[str]]:
        """
        Explains authoritative engine facts using grounded LLM explanation.
        Returns (answer_text, aria_priority, error).
        """
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        has_live_key = bool(
            api_key
            and api_key not in ("your_api_key_here", "dummy_key_for_mocking", "mock-gemini-live-key", "")
        )

        explainer_client = None
        if not has_live_key:
            from ai.live_demo import build_dynamic_mock_explainer

            explainer_client = build_dynamic_mock_explainer(engine_facts, user_query)

        exp_res = explain_result(engine_result=engine_facts, user_question=user_query, client=explainer_client)
        answer_text = exp_res.get("answer_text", "I don't have that information available.")

        aria_priority = "polite"
        if isinstance(engine_facts, dict) and (
            engine_facts.get("fraud_warning") or engine_facts.get("risk_level") == "high"
        ):
            aria_priority = "assertive"

        return answer_text, aria_priority, None
