"""
Backend Dispatcher for FinSight.

The Dispatcher is the strict architectural bridge between the AI layer's
structured intent and the deterministic financial/payment engines.

NON-NEGOTIABLE PRINCIPLES:
1. Zero financial calculations in the Dispatcher or AI layer.
2. The authenticated user_id is injected; AI user_id is strictly ignored.
3. Monetary inputs are converted via Decimal(str(value)).
4. Natural language queries for goals are resolved to real user-scoped Goal IDs.
5. All financial data returned to the AI layer comes exclusively from the engine.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from backend.models import User, Goal, PendingPayment
from backend.engine.financial_engine import (
    get_balance,
    get_spending_summary,
    check_affordability,
    project_goal_completion,
    get_insights,
)
from backend.payment.payment_engine import (
    preview_payment,
    execute_payment,
)
from backend.payment.risk import evaluate_payment_risk


def dispatch_intent(
    user_id: int,
    intent_data: Dict[str, Any],
    db: Session,
    confirmation_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates structured intent from AI, executes the appropriate deterministic
    engine functions with authenticated user scoping, and returns authoritative facts.

    Args:
        user_id: Authenticated user ID (overrides any AI-supplied user_id).
        intent_data: Structured intent dict, e.g. {"intent": "...", "arguments": {...}}
        db: SQLAlchemy database session.
        confirmation_token: Optional confirmation token / pending_payment_id.

    Returns:
        Dict of authoritative structured facts or clarification request.

    Raises:
        ValueError: On invalid monetary inputs, security violations, or missing users.
    """
    # 1. Verify user exists in database
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    if not intent_data or not isinstance(intent_data, dict):
        raise ValueError("Invalid intent data provided to dispatcher.")

    intent_name = intent_data.get("intent", "").strip()
    arguments = intent_data.get("arguments", {})
    if not isinstance(arguments, dict):
        arguments = {}

    # =========================================================================
    # 1. get_balance
    # =========================================================================
    if intent_name == "get_balance":
        balance_facts = get_balance(user_id=user_id, db=db)
        return {
            "intent": "get_balance",
            "balance": balance_facts["balance"],
            "as_of": balance_facts["as_of"],
        }

    # =========================================================================
    # 2. get_spending_summary
    # =========================================================================
    elif intent_name == "get_spending_summary":
        period = arguments.get("period", "this_month")
        if not period or period not in ("this_month", "last_month"):
            period = "this_month"

        spending_facts = get_spending_summary(user_id=user_id, db=db, period=period)
        requested_category = arguments.get("category")

        response = {
            "intent": "get_spending_summary",
            "period": period,
            "total": spending_facts["total"],
            "by_category": spending_facts["by_category"],
            "vs_last_period_pct": spending_facts["vs_last_period_pct"],
        }
        if requested_category:
            response["requested_category"] = requested_category
        return response

    # =========================================================================
    # 3. check_affordability
    # =========================================================================
    elif intent_name == "check_affordability":
        amount_raw = arguments.get("amount")
        if amount_raw is None or str(amount_raw).strip() == "":
            return {
                "status": "clarification_needed",
                "question": "How much does the item cost?",
            }

        try:
            amount = Decimal(str(amount_raw).replace(",", "").strip())
        except Exception:
            raise ValueError(f"Invalid monetary amount '{amount_raw}'.")

        if amount <= Decimal("0.00"):
            raise ValueError(f"Purchase amount must be positive, got {amount}.")

        affordability_facts = check_affordability(user_id=user_id, amount=amount, db=db)
        item_name = arguments.get("item_name")

        response = {
            "intent": "check_affordability",
            "amount": amount,
            "can_afford": affordability_facts["can_afford"],
            "balance_after": affordability_facts["balance_after"],
            "upcoming_bills": affordability_facts["upcoming_bills"],
            "savings_goal_impact_months": affordability_facts["savings_goal_impact_months"],
            "reasoning_facts": affordability_facts["reasoning_facts"],
        }
        if item_name:
            response["item_name"] = item_name
        return response

    # =========================================================================
    # 4. project_goal_completion
    # =========================================================================
    elif intent_name == "project_goal_completion":
        goal_name_query = arguments.get("goal_name")
        hypothetical_raw = arguments.get("hypothetical_contribution")

        hypothetical_contribution: Optional[Decimal] = None
        if hypothetical_raw is not None and str(hypothetical_raw).strip() != "":
            try:
                hypothetical_contribution = Decimal(str(hypothetical_raw).replace(",", "").strip())
                if hypothetical_contribution <= Decimal("0.00"):
                    raise ValueError("Hypothetical contribution must be greater than zero.")
            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                raise ValueError(f"Invalid hypothetical contribution '{hypothetical_raw}'.")

        # Resolve goal scoped strictly to user
        active_goals = (
            db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.status == "active")
            .order_by(Goal.id.asc())
            .all()
        )

        resolved_goal: Optional[Goal] = None

        if goal_name_query and str(goal_name_query).strip():
            query_str = str(goal_name_query).strip().lower()
            for g in active_goals:
                if g.name.lower() == query_str or query_str in g.name.lower() or g.name.lower() in query_str:
                    resolved_goal = g
                    break
        else:
            # If no goal name provided, select if exactly one active goal exists
            if len(active_goals) == 1:
                resolved_goal = active_goals[0]

        if not resolved_goal:
            return {
                "status": "clarification_needed",
                "question": "Which savings goal would you like me to check?",
            }

        projection_facts = project_goal_completion(
            goal_id=resolved_goal.id,
            db=db,
            hypothetical_contribution=hypothetical_contribution,
        )

        return {
            "intent": "project_goal_completion",
            "goal_id": resolved_goal.id,
            "goal_name": resolved_goal.name,
            "target_amount": resolved_goal.target_amount,
            "current_amount": resolved_goal.current_amount,
            "monthly_contribution": resolved_goal.monthly_contribution,
            "current_months_remaining": projection_facts["current_months_remaining"],
            "hypothetical_months_remaining": projection_facts["hypothetical_months_remaining"],
        }

    # =========================================================================
    # 5. get_insights
    # =========================================================================
    elif intent_name == "get_insights":
        insights_facts = get_insights(user_id=user_id, db=db)
        return {
            "intent": "get_insights",
            "insights": insights_facts,
        }

    # =========================================================================
    # 6. payment_preview
    # =========================================================================
    elif intent_name == "payment_preview":
        amount_raw = arguments.get("amount")
        recipient_name = arguments.get("recipient_name")

        if amount_raw is None or str(amount_raw).strip() == "":
            return {
                "status": "clarification_needed",
                "question": "How much would you like to send?",
            }

        if not recipient_name or not str(recipient_name).strip():
            return {
                "status": "clarification_needed",
                "question": "Who would you like to send this payment to?",
            }

        try:
            amount = Decimal(str(amount_raw).replace(",", "").strip())
        except Exception:
            raise ValueError(f"Invalid payment amount '{amount_raw}'.")

        if amount <= Decimal("0.00"):
            raise ValueError(f"Payment amount must be greater than zero, got {amount}.")

        cleaned_recipient = str(recipient_name).strip()

        # 1. Deterministic payment preview
        preview_facts = preview_payment(
            user_id=user_id,
            amount=amount,
            recipient_name=cleaned_recipient,
            db=db,
        )

        # 2. Deterministic payment risk & fraud checks
        risk_facts = evaluate_payment_risk(
            user_id=user_id,
            amount=amount,
            recipient_name=cleaned_recipient,
            db=db,
        )

        # 3. Create persistent PendingPayment record (expires in 15 minutes)
        pending_payment = PendingPayment(
            user_id=user_id,
            amount=amount,
            recipient_name=cleaned_recipient,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            created_at=datetime.utcnow(),
        )
        db.add(pending_payment)
        db.commit()
        db.refresh(pending_payment)

        return {
            "intent": "payment_preview",
            "requires_confirmation": True,
            "pending_payment_id": pending_payment.id,
            "confirmation_token": str(pending_payment.id),
            "can_proceed": preview_facts["can_proceed"],
            "amount": preview_facts["amount"],
            "recipient_name": preview_facts["recipient_name"],
            "current_balance": preview_facts["current_balance"],
            "balance_after": preview_facts["balance_after"],
            "upcoming_bills": preview_facts["upcoming_bills"],
            "available_after_commitments": preview_facts["available_after_commitments"],
            "risk_level": risk_facts["risk_level"],
            "fraud_warning": risk_facts["fraud_warning"],
            "risk_reasons": risk_facts["risk_reasons"],
            "reasoning_facts": preview_facts["reasoning_facts"],
        }

    # =========================================================================
    # 7. payment_execute
    # =========================================================================
    elif intent_name == "payment_execute":
        pending_id_raw = (
            arguments.get("pending_payment_id")
            or arguments.get("confirmation_token")
            or confirmation_token
        )

        if not pending_id_raw or str(pending_id_raw).strip() == "":
            return {
                "status": "clarification_needed",
                "question": "Which payment would you like to confirm?",
            }

        try:
            pending_id = int(str(pending_id_raw).strip())
        except Exception:
            raise ValueError(f"Invalid pending payment ID '{pending_id_raw}'.")

        pending_payment = (
            db.query(PendingPayment)
            .filter(PendingPayment.id == pending_id)
            .first()
        )
        if not pending_payment:
            raise ValueError(f"Pending payment with ID {pending_id} not found.")

        # Enforce strict user ownership
        if pending_payment.user_id != user_id:
            raise ValueError("Unauthorized: Payment does not belong to the authenticated user.")

        # Check status and expiry
        if pending_payment.status != "pending":
            raise ValueError(f"Payment cannot be executed because it is already {pending_payment.status}.")

        if pending_payment.is_expired():
            pending_payment.status = "expired"
            db.commit()
            raise ValueError("Payment confirmation has expired.")

        # Execute payment using amounts strictly stored in the database record
        exec_facts = execute_payment(
            user_id=user_id,
            amount=pending_payment.amount,
            recipient_name=pending_payment.recipient_name,
            db=db,
        )

        # Mark pending payment as executed
        pending_payment.status = "executed"
        db.commit()

        return {
            "intent": "payment_execute",
            "success": True,
            "transaction_id": exec_facts["transaction_id"],
            "recipient_name": exec_facts["recipient_name"],
            "amount": exec_facts["amount"],
            "previous_balance": exec_facts["previous_balance"],
            "new_balance": exec_facts["new_balance"],
            "transaction_type": "expense",
            "pending_payment_id": pending_payment.id,
            "status": "executed",
        }

    # =========================================================================
    # Unsupported Intent Fallback
    # =========================================================================
    else:
        return {
            "status": "unsupported_intent",
            "intent": intent_name,
            "message": f"Intent '{intent_name}' is not recognized or supported by FinSight.",
        }
