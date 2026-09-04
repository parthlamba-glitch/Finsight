"""
FinSight AI Orchestration Pipeline
==================================

Orchestrates the 3-stage conversational AI flow:
  1. Intent Router: Natural language understanding -> tool selection + raw parameter extraction.
  2. Backend Dispatcher: Intent validation and execution via deterministic engine (backend.engine.dispatcher).
  3. Grounded Explainer: Translating engine structured facts into concise voice-friendly response.

NON-NEGOTIABLE ARCHITECTURAL RULES:
- The AI layer NEVER calculates financial numbers, percentages, or balances.
- The AI layer NEVER queries SQLite directly or modifies engine outputs.
- The AI layer NEVER determines authoritative user_id.
- All financial execution delegates exclusively to backend.engine.dispatcher.dispatch_intent.
"""

from datetime import date, datetime
from decimal import Decimal
import logging
import os
import re
from typing import Any, Callable, Dict, Optional, Union
import uuid
from openai import OpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.db import SessionLocal
from backend.models.user import User
from backend.models.goal import Goal
from backend.engine.dispatcher import dispatch_intent
from ai.conversation import conversation_manager
from ai.intent_router import _parse_amount_value
from ai.scam_checker import assess_scam_message, format_scam_conversational_response
from ai.llm_client import LLMClient


def serialize_data_boundary(obj: Any) -> Any:
    """
    Safe serialization boundary for structured facts.
    Preserves exact numeric precision and dates without rounding or arithmetic.
    """
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize_data_boundary(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_data_boundary(item) for item in obj]
    return obj


def resolve_goal_id_from_db(
    user_id: int,
    goal_name_or_id: str,
    db: Session,
) -> Optional[int]:
    """
    Safely resolves a goal name to a genuine database goal_id for the given user.
    Never invents a goal ID.
    """
    if not goal_name_or_id or not db:
        return None

    # Check direct numeric ID match
    if str(goal_name_or_id).isdigit():
        goal_by_id = (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.id == int(goal_name_or_id))
            .first()
        )
        if goal_by_id:
            return goal_by_id.id

    # Check case-insensitive name match / substring match
    goals = db.query(Goal).filter(Goal.user_id == user_id).all()
    query_name = str(goal_name_or_id).lower().strip()

    for g in goals:
        g_name = g.name.lower()
        if g_name == query_name or query_name in g_name or g_name in query_name:
            return g.id

    # If user has only one goal and refers to it generically (e.g. "savings goal", "my savings")
    if len(goals) == 1 and ("saving" in query_name or "goal" in query_name):
        return goals[0].id

    return None


class AIPipeline:
    """
    Unified AI Pipeline for FinSight.
    Connects conversational natural language queries to the Backend Dispatcher and Explainer.
    """

    @classmethod
    def process_query(
        cls,
        user_id: int,
        query: str,
        db: Session,
        confirmation_token: Optional[str] = None,
        conversation_id: Optional[str] = None,
        voice: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end processing for a user query:
        1. Context retrieval from conversation_manager.
        2. Semantic intent parsing via LLM / Intent Router.
        3. Delegation to backend.engine.dispatcher.dispatch_intent.
        4. Grounded voice narration via AI Explainer.
        """
        if not user_id:
            raise ValueError("user_id must be provided by authenticated context.")

        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        if not query or not query.strip():
            return {
                "intent": "unknown",
                "answer_text": "How can I assist you with your finances today?",
                "aria_priority": "polite",
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": {},
                "structured_data": {},
                "execution_mode": "MOCK_FALLBACK",
                "conversation_status": "completed",
                "conversation_id": conversation_id,
            }

        # 1. Retrieve multi-turn context
        conv_context = conversation_manager.get_context(conversation_id)
        if confirmation_token and not conv_context.get("confirmation_token"):
            conv_context["confirmation_token"] = confirmation_token

        # 2. Check Execution Mode
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        has_live_key = bool(api_key and api_key not in ("your_api_key_here", "dummy_key_for_mocking", ""))
        execution_mode = "REAL_LLM" if has_live_key else "MOCK_FALLBACK"

        if not has_live_key:
            logger.warning(
                "[AI Pipeline] LLM_API_KEY is not configured or is a placeholder. "
                "Operating in MOCK_FALLBACK mode (local regex/keyword routing)."
            )

        # 3. Intent Routing via LLMClient
        intent_info, route_err = LLMClient.call_tool_router(
            query=query,
            user_id=str(user_id),
            context=conv_context,
        )

        status = intent_info.get("status")

        # 4. Handle Clarification Requests
        if status == "clarification_needed":
            clarification_question = intent_info.get("question", "Could you please clarify your request?")
            intent_name = intent_info.get("intent", "clarification_needed")
            extracted_params = intent_info.get("extracted_parameters", {})

            conversation_manager.update_context(
                conversation_id,
                {
                    "status": "awaiting_clarification",
                    "intent": intent_name,
                    "last_user_query": query,
                    "last_clarification_question": clarification_question,
                    "parameters": extracted_params,
                },
            )

            facts = {
                "status": "clarification_needed",
                "question": clarification_question,
                "intent": intent_name,
            }

            return {
                "intent": intent_name,
                "answer_text": clarification_question,
                "aria_priority": "polite",
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": facts,
                "structured_data": facts,
                "execution_mode": execution_mode,
                "conversation_status": "clarification_needed",
                "conversation_id": conversation_id,
            }

        # 5. Handle Router Errors
        if status == "error":
            error_msg = intent_info.get("message", "An error occurred while analyzing your request.")
            return {
                "intent": "error",
                "answer_text": "I encountered an issue processing your request. Please try again.",
                "aria_priority": "polite",
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": {"status": "error", "message": error_msg},
                "structured_data": {"status": "error", "message": error_msg},
                "execution_mode": execution_mode,
                "conversation_status": "completed",
                "conversation_id": conversation_id,
            }

        func_name = intent_info.get("intent", "")
        args = intent_info.get("arguments", {})

        # 6. Handle PROTECT Scam Checker
        if func_name == "check_scam_message":
            msg_text = (args.get("message") or "").strip()
            if not msg_text and conv_context.get("status") == "awaiting_clarification":
                msg_text = query.strip()

            if not msg_text:
                clarification_msg = "Sure — please paste the message or SMS you'd like me to check."
                conversation_manager.update_context(
                    conversation_id,
                    {
                        "status": "awaiting_clarification",
                        "intent": "check_scam_message",
                        "last_user_query": query,
                        "last_clarification_question": clarification_msg,
                    },
                )
                return {
                    "intent": "check_scam_message",
                    "answer_text": clarification_msg,
                    "aria_priority": "polite",
                    "requires_confirmation": False,
                    "confirmation_token": None,
                    "pending_payment_id": None,
                    "structured_facts": {"status": "clarification_needed", "question": clarification_msg},
                    "structured_data": {"status": "clarification_needed", "question": clarification_msg},
                    "execution_mode": execution_mode,
                    "conversation_status": "clarification_needed",
                    "conversation_id": conversation_id,
                }

            if not has_live_key:
                from ai.live_demo import _evaluate_mock_scam_message
                scam_result = _evaluate_mock_scam_message(msg_text)
            else:
                scam_result = assess_scam_message(message=msg_text)
            answer_text = format_scam_conversational_response(scam_result)
            conversation_manager.clear(conversation_id)

            aria_priority = "assertive" if scam_result.get("looks_suspicious") else "polite"
            return {
                "intent": "check_scam_message",
                "answer_text": answer_text,
                "aria_priority": aria_priority,
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": scam_result,
                "structured_data": scam_result,
                "execution_mode": execution_mode,
                "conversation_status": "completed",
                "conversation_id": conversation_id,
            }

        # 7. Handle UI Control & Accessibility Intents
        UI_CONTROL_INTENTS = {
            "sync_bank": "Syncing your bank accounts now to refresh your latest transactions.",
            "read_recent_transactions": "Reading your recent transactions.",
            "read_goals": "Reading your active financial goals and savings progress.",
            "upload_document": "Opening document upload to scan and import your statement.",
        }

        if func_name in UI_CONTROL_INTENTS:
            answer_text = UI_CONTROL_INTENTS[func_name]
            structured_data = {
                "action": func_name,
                "intent": func_name,
                "status": "success",
            }
            conversation_manager.clear(conversation_id)
            return {
                "intent": func_name,
                "answer_text": answer_text,
                "aria_priority": "polite",
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": structured_data,
                "structured_data": structured_data,
                "execution_mode": execution_mode,
                "conversation_status": "completed",
                "conversation_id": conversation_id,
            }

        # 8. Delegate Financial Intents Strictly to Backend Dispatcher
        intent_data = {
            "intent": func_name,
            "arguments": args,
        }

        token_to_pass = (
            confirmation_token
            or conv_context.get("confirmation_token")
            or args.get("confirmation_token")
            or args.get("pending_payment_id")
        )

        dispatcher_result = dispatch_intent(
            user_id=user_id,
            intent_data=intent_data,
            db=db,
            confirmation_token=str(token_to_pass) if token_to_pass is not None else None,
        )

        # 9. Handle Clarifications Returned by Backend Dispatcher
        if dispatcher_result.get("status") == "clarification_needed":
            clarification_question = dispatcher_result.get("question", "Could you please clarify?")
            conversation_manager.update_context(
                conversation_id,
                {
                    "status": "awaiting_clarification",
                    "intent": func_name,
                    "last_user_query": query,
                    "last_clarification_question": clarification_question,
                    "parameters": args,
                },
            )
            return {
                "intent": func_name,
                "answer_text": clarification_question,
                "aria_priority": "polite",
                "requires_confirmation": False,
                "confirmation_token": None,
                "pending_payment_id": None,
                "structured_facts": dispatcher_result,
                "structured_data": dispatcher_result,
                "execution_mode": execution_mode,
                "conversation_status": "clarification_needed",
                "conversation_id": conversation_id,
            }

        # 10. Generate Grounded Explanation from Authoritative Facts
        answer_text, aria_priority, exp_err = LLMClient.explain_facts(
            engine_facts=dispatcher_result,
            user_query=query,
        )

        # Ensure payment execute narration explicitly contains completion confirmation
        if func_name == "payment_execute" and dispatcher_result.get("status") == "executed":
            if "successfully" not in answer_text.lower() and "completed" not in answer_text.lower():
                amt = dispatcher_result.get("amount", "0.00")
                rec = dispatcher_result.get("recipient_name", "Recipient")
                bal = dispatcher_result.get("new_balance", "0.00")
                answer_text = f"Payment of ₹{amt} to {rec} was successfully completed. Your new balance is ₹{bal}."

        requires_confirmation = bool(dispatcher_result.get("requires_confirmation", False))
        pending_payment_id = dispatcher_result.get("pending_payment_id")
        conf_token = dispatcher_result.get("confirmation_token")

        if requires_confirmation:
            conv_status = "awaiting_confirmation"
            conversation_manager.update_context(
                conversation_id,
                {
                    "status": "awaiting_confirmation",
                    "intent": func_name,
                    "pending_payment_id": pending_payment_id,
                    "confirmation_token": conf_token,
                },
            )
        else:
            conv_status = "completed"
            conversation_manager.clear(conversation_id)

        if dispatcher_result.get("fraud_warning") or dispatcher_result.get("risk_level") == "high":
            aria_priority = "assertive"

        return {
            "intent": func_name,
            "answer_text": answer_text,
            "aria_priority": aria_priority,
            "requires_confirmation": requires_confirmation,
            "confirmation_token": conf_token,
            "pending_payment_id": pending_payment_id,
            "structured_facts": dispatcher_result,
            "structured_data": dispatcher_result,
            "execution_mode": execution_mode,
            "conversation_status": conv_status,
            "conversation_id": conversation_id,
        }


def run_finSight_pipeline(
    user_id: Union[int, str],
    query: str,
    db: Optional[Session] = None,
    context: Optional[Dict[str, Any]] = None,
    engine_registry: Optional[Dict[str, Callable[..., Any]]] = None,
    router_client: Optional[OpenAI] = None,
    explainer_client: Optional[OpenAI] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible wrapper for legacy test scripts and terminal demos.
    """
    own_session = False
    active_db = db
    if active_db is None:
        try:
            active_db = SessionLocal()
            own_session = True
        except Exception:
            active_db = None

    try:
        resolved_user_id = 1
        if isinstance(user_id, int):
            resolved_user_id = user_id
        elif isinstance(user_id, str):
            if user_id.isdigit():
                resolved_user_id = int(user_id)
            elif active_db:
                demo_user = active_db.query(User).filter((User.email == user_id) | (User.full_name == user_id)).first()
                if not demo_user and user_id.lower() == "demo_user":
                    demo_user = active_db.query(User).first()
                if demo_user:
                    resolved_user_id = demo_user.id
        elif active_db:
            u = active_db.query(User).first()
            if u:
                resolved_user_id = u.id

        if active_db is not None:
            conv_id = context.get("conversation_id") if isinstance(context, dict) else None
            conf_token = context.get("confirmation_token") if isinstance(context, dict) else None
            res = AIPipeline.process_query(
                user_id=resolved_user_id,
                query=query,
                db=active_db,
                conversation_id=conv_id,
                confirmation_token=conf_token,
            )
            facts = res.get("structured_facts") or res.get("structured_data") or {}
            return {
                "answer_text": res.get("answer_text", ""),
                "structured_data": facts,
                "structured_facts": facts,
                "intent": res.get("intent", "unknown"),
                "conversation_status": res.get("conversation_status", "completed"),
                "conversation_id": res.get("conversation_id", conv_id),
                "execution_mode": res.get("execution_mode", "MOCK_FALLBACK"),
                "requires_confirmation": res.get("requires_confirmation", False),
                "confirmation_token": res.get("confirmation_token"),
                "pending_payment_id": res.get("pending_payment_id"),
            }
        else:
            return {
                "answer_text": "Database session not available.",
                "structured_data": {},
                "structured_facts": {},
                "intent": "unknown",
                "conversation_status": "completed",
                "execution_mode": "MOCK_FALLBACK",
            }
    finally:
        if own_session and active_db is not None:
            active_db.close()
