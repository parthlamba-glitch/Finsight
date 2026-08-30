"""
FinSight AI Orchestration Pipeline
==================================

Orchestrates the 3-stage conversational AI flow:
  1. Intent Router: Natural language understanding -> tool selection + raw parameter extraction.
  2. Financial Engine: Deterministic execution of financial logic (backend.engine.financial_engine).
  3. Grounded Explainer: Translating engine structured facts into concise voice-friendly response.

ARCHITECTURAL RULES:
- The AI layer NEVER calculates financial numbers.
- The AI layer NEVER modifies engine outputs.
- The AI layer NEVER applies business/financial calculation rules.
- The deterministic financial engine is the ONLY source of financial truth.
"""

from datetime import date, datetime
from decimal import Decimal
import inspect
import os
from typing import Any, Callable, Dict, Optional, Union
# pyrefly: ignore [missing-import]
from openai import OpenAI
from sqlalchemy.orm import Session

from backend.db import SessionLocal
import backend.engine.financial_engine as real_engine
from backend.models.goal import Goal
from backend.models.user import User
from ai.explainer import explain_result
from ai.intent_router import route_query
from ai.scam_checker import assess_scam_message, format_scam_conversational_response

PRODUCTION_ENGINE_REGISTRY: Dict[str, Callable[..., Any]] = {
    "get_balance": real_engine.get_balance,
    "get_spending_summary": real_engine.get_spending_summary,
    "check_affordability": real_engine.check_affordability,
    "project_goal_completion": real_engine.project_goal_completion,
    "get_insights": real_engine.get_insights,
}


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
    Executes the end-to-end FinSight conversational AI pipeline.

    Parameters:
    -----------
    user_id : int | str
        Authenticated user identifier.
    query : str
        Natural language financial question from the user.
    db : Session, optional
        Active SQLAlchemy session provided by caller.
    context : dict, optional
        Application context (e.g. goals dictionary).
    engine_registry : dict, optional
        Custom engine mapping for testing. Defaults to production financial_engine functions.
    router_client : OpenAI, optional
        Client for Intent Router.
    explainer_client : OpenAI, optional
        Client for Explainer.
    model : str, optional
        Model override for LLM calls.

    Returns:
    --------
    dict:
        {
            "answer_text": str,
            "structured_data": dict | list
        }
    """
    if user_id is None:
        return {
            "answer_text": "Unable to process request: missing user identifier.",
            "structured_data": {"status": "error", "message": "user_id is required."},
        }

    # Manage DB session lifecycle: reuse caller's db if provided, or create dedicated session
    own_session = False
    active_db = db
    if active_db is None:
        try:
            active_db = SessionLocal()
            own_session = True
        except Exception:
            active_db = None

    try:
        # Resolve user_id to integer for database operations
        resolved_user_id: Optional[int] = None
        if isinstance(user_id, int):
            resolved_user_id = user_id
        elif isinstance(user_id, str):
            if user_id.isdigit():
                resolved_user_id = int(user_id)
            elif active_db:
                # Resolve demo user or email identifier dynamically
                demo_user = active_db.query(User).filter((User.email == user_id) | (User.full_name == user_id)).first()
                if not demo_user and user_id.lower() == "demo_user":
                    demo_user = active_db.query(User).first()
                if demo_user:
                    resolved_user_id = demo_user.id

        context_dict = dict(context or {})

        # Populate context goals from database if available and not explicitly provided
        if active_db and resolved_user_id is not None and "goals" not in context_dict:
            try:
                db_goals = active_db.query(Goal).filter(Goal.user_id == resolved_user_id).all()
                if db_goals:
                    context_dict["goals"] = {g.name.lower(): g.id for g in db_goals}
            except Exception:
                pass

        # Check API key configuration for dynamic local fallback
        api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        has_live_key = bool(api_key and api_key not in ("your_api_key_here", "dummy_key_for_mocking"))

        is_real_llm = bool(has_live_key and (router_client is None or not hasattr(router_client, "_mock_return_value")))
        execution_mode = "REAL_LLM" if is_real_llm else "MOCK_FALLBACK"

        active_router_client = router_client
        if active_router_client is None and not has_live_key:
            from ai.live_demo import build_dynamic_mock_router
            active_router_client = build_dynamic_mock_router(query, context=context_dict)

        # 1. Intent Routing
        router_user_id_str = str(resolved_user_id if resolved_user_id is not None else user_id)
        router_result = route_query(
            query=query,
            user_id=router_user_id_str,
            context=context_dict,
            client=active_router_client,
            model=model,
        )

        status = router_result.get("status")

        # Fallback to dynamic mock router if live LLM call encountered a network/503 error
        if status == "error" and is_real_llm:
            from ai.live_demo import build_dynamic_mock_router
            fallback_client = build_dynamic_mock_router(query, context=context_dict)
            fallback_result = route_query(
                query=query,
                user_id=router_user_id_str,
                context=context_dict,
                client=fallback_client,
                model=model,
            )
            if fallback_result.get("status") in ("success", "clarification_needed"):
                router_result = fallback_result
                status = router_result.get("status")
                execution_mode = "MOCK_FALLBACK"

        # 2. Handle Clarification / Non-financial queries
        if status == "clarification_needed":
            clarification_msg = router_result.get(
                "question", "Could you please provide more details?"
            )
            return {
                "answer_text": clarification_msg,
                "structured_data": router_result,
                "conversation_status": "awaiting_clarification",
                "intent": router_result.get("intent"),
                "parameters": router_result.get("extracted_parameters", {}),
                "missing_parameters": router_result.get("missing_parameters", []),
                "clarification_question": clarification_msg,
                "execution_mode": execution_mode,
            }

        # 3. Handle Router Errors
        if status != "success":
            error_msg = router_result.get(
                "message", "An error occurred while analyzing your request."
            )
            return {
                "answer_text": "I encountered an issue processing your request.",
                "structured_data": router_result,
                "conversation_status": "active",
                "execution_mode": execution_mode,
            }



        # 4. Handle PROTECT Scam Safety Checker (Independent of Financial Engine)
        func_name = router_result.get("function_name", "")
        args = router_result.get("arguments", {})

        if func_name == "check_scam_message":
            msg_text = (args.get("message") or "").strip()
            if not msg_text and context.get("status") == "awaiting_clarification" and context.get("intent") == "check_scam_message":
                msg_text = query.strip()

            if not msg_text:
                clarification_msg = "Sure — please paste the message or SMS you'd like me to check."
                return {
                    "answer_text": clarification_msg,
                    "structured_data": {
                        "status": "clarification_needed",
                        "question": clarification_msg,
                    },
                    "conversation_status": "awaiting_clarification",
                    "intent": "check_scam_message",
                    "parameters": {},
                    "missing_parameters": ["message"],
                    "clarification_question": clarification_msg,
                    "execution_mode": execution_mode,
                }

            scam_client = explainer_client or router_client
            scam_result = assess_scam_message(
                message=msg_text,
                client=scam_client,
                model=model,
            )
            answer_text = format_scam_conversational_response(scam_result)
            return {
                "answer_text": answer_text,
                "structured_data": scam_result,
                "conversation_status": "completed",
                "intent": "check_scam_message",
                "parameters": {"message": msg_text},
                "missing_parameters": [],
                "execution_mode": execution_mode,
            }

        # 5. Handle UI Control & Accessibility Intents (Independent of Financial Engine)
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
            return {
                "answer_text": answer_text,
                "structured_data": structured_data,
                "conversation_status": "completed",
                "intent": func_name,
                "parameters": args,
                "missing_parameters": [],
                "execution_mode": execution_mode,
            }

        # 6. Invoke Deterministic Financial Engine
        registry = engine_registry or PRODUCTION_ENGINE_REGISTRY
        engine_fn = registry.get(func_name)

        if not engine_fn:
            return {
                "answer_text": "The requested financial function is not currently supported.",
                "structured_data": {
                    "status": "error",
                    "message": f"Unsupported engine function: {func_name}",
                },
            }

        # Explicit dispatch to strictly match real engine signatures
        try:
            # Check if using custom mock engine without db parameter
            fn_sig = inspect.signature(engine_fn)
            accepts_db = "db" in fn_sig.parameters

            # Use resolved integer user_id if available for real database engine
            engine_user_id = resolved_user_id if resolved_user_id is not None else user_id

            if func_name == "get_balance":
                if accepts_db:
                    engine_result = engine_fn(user_id=engine_user_id, db=active_db)
                else:
                    engine_result = engine_fn(user_id=engine_user_id)

            elif func_name == "get_spending_summary":
                period = args.get("period", "this_month")
                if accepts_db:
                    engine_result = engine_fn(user_id=engine_user_id, db=active_db, period=period)
                else:
                    cat = args.get("category")
                    if "category" in fn_sig.parameters and cat:
                        engine_result = engine_fn(user_id=engine_user_id, period=period, category=cat)
                    else:
                        engine_result = engine_fn(user_id=engine_user_id, period=period)

            elif func_name == "check_affordability":
                amount = args.get("amount")
                if accepts_db:
                    engine_result = engine_fn(user_id=engine_user_id, amount=amount, db=active_db)
                else:
                    item_desc = args.get("item_description")
                    if "item_description" in fn_sig.parameters and item_desc:
                        engine_result = engine_fn(user_id=engine_user_id, amount=amount, item_description=item_desc)
                    else:
                        engine_result = engine_fn(user_id=engine_user_id, amount=amount)

            elif func_name == "project_goal_completion":
                goal_id = args.get("goal_id")
                hypo_contrib = args.get("hypothetical_contribution")

                # If goal_id was not resolved by router, attempt DB resolution
                if not goal_id and active_db and resolved_user_id is not None:
                    goal_name_or_id = args.get("goal_name") or args.get("goal_name_or_id", "")
                    goal_id = resolve_goal_id_from_db(resolved_user_id, goal_name_or_id, active_db)

                if not goal_id:
                    return {
                        "answer_text": "Which savings goal would you like me to check?",
                        "structured_data": {
                            "status": "clarification_needed",
                            "question": "Which savings goal would you like me to check?",
                        },
                    }

                engine_goal_id = int(goal_id) if str(goal_id).isdigit() else goal_id

                if accepts_db:
                    engine_result = engine_fn(
                        goal_id=engine_goal_id,
                        db=active_db,
                        hypothetical_contribution=hypo_contrib,
                    )
                else:
                    if "user_id" in fn_sig.parameters:
                        engine_result = engine_fn(
                            user_id=engine_user_id,
                            goal_id=engine_goal_id,
                            hypothetical_contribution=hypo_contrib,
                        )
                    else:
                        engine_result = engine_fn(
                            goal_id=engine_goal_id,
                            hypothetical_contribution=hypo_contrib,
                        )

            elif func_name == "get_insights":
                if accepts_db:
                    engine_result = engine_fn(user_id=engine_user_id, db=active_db)
                else:
                    engine_result = engine_fn(user_id=engine_user_id)

            else:
                return {
                    "answer_text": "The requested financial function is not currently supported.",
                    "structured_data": {
                        "status": "error",
                        "message": f"Unknown engine function: {func_name}",
                    },
                }

        except Exception as e:
            return {
                "answer_text": "I couldn't retrieve your financial data right now. Please try again.",
                "structured_data": {
                    "status": "error",
                    "message": f"Financial engine execution failed: {str(e)}",
                },
            }

        # 5. Generate Grounded Explanation
        active_explainer_client = explainer_client
        if active_explainer_client is None and not has_live_key:
            from ai.live_demo import build_dynamic_mock_explainer
            active_explainer_client = build_dynamic_mock_explainer(engine_result, query)

        explanation = explain_result(
            engine_result=engine_result,
            user_question=query,
            client=active_explainer_client,
            model=model,
        )

        answer_text = explanation.get(
            "answer_text", "I don't have that information available."
        )

        if (not answer_text or "Unable to generate explanation" in answer_text) and is_real_llm:
            from ai.live_demo import build_dynamic_mock_explainer
            fallback_explainer = build_dynamic_mock_explainer(engine_result, query)
            fallback_exp = explain_result(
                engine_result=engine_result,
                user_question=query,
                client=fallback_explainer,
                model=model,
            )
            if fallback_exp.get("answer_text"):
                answer_text = fallback_exp["answer_text"]

        return {
            "answer_text": answer_text,
            "structured_data": engine_result,
            "conversation_status": "completed",
            "intent": func_name,
            "parameters": args,
            "missing_parameters": [],
            "execution_mode": execution_mode,
        }



    finally:
        if own_session and active_db is not None:
            active_db.close()
