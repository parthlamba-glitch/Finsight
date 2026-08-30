"""
AI Router for FinSight.

Provides the /ask conversational endpoint connecting natural language / voice
queries to the AI Intent Router, Backend Dispatcher, and Explainer.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User
from backend.auth.dependencies import get_current_user
from backend.schemas import AskRequest, AskResponse
from ai.pipeline import AIPipeline

router = APIRouter(tags=["AI Copilot"])


@router.post("/ask", response_model=AskResponse, summary="Natural Language Financial Copilot Query")
@router.post("/api/v1/ask", response_model=AskResponse, include_in_schema=False)
def ask_financial_copilot(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    """
    Primary conversational endpoint for FinSight.

    Architecture Flow:
    1. Authenticates request and obtains authoritative current_user.id.
    2. Passes query to AI Intent Router to extract intent and slots.
    3. Backend Dispatcher routes intent to deterministic financial / payment engine using current_user.id.
    4. AI Explainer synthesizes accessible, screen-reader-safe spoken narration.
    5. Returns authoritative facts and accessible narration.
    """
    # The authenticated current_user.id is strictly authoritative (overriding any body user_id)
    user_id = current_user.id

    try:
        result = AIPipeline.process_query(
            user_id=user_id,
            query=request.query,
            db=db,
            confirmation_token=request.confirmation_token,
            conversation_id=request.conversation_id,
            voice=request.voice,
        )


        facts = result.get("structured_facts", {})
        execution_mode = result.get("execution_mode", "MOCK_FALLBACK")
        conv_status = result.get("conversation_status", "completed")
        if result.get("requires_confirmation"):
            conv_status = "awaiting_confirmation"
        elif facts.get("status") == "clarification_needed":
            conv_status = "clarification_needed"

        return AskResponse(
            intent=result.get("intent", "unknown"),
            answer_text=result.get("answer_text", "Processed successfully."),
            aria_priority=result.get("aria_priority", "polite"),
            requires_confirmation=result.get("requires_confirmation", False),
            confirmation_token=result.get("confirmation_token"),
            pending_payment_id=result.get("pending_payment_id"),
            structured_facts=facts,
            structured_data=facts,
            execution_mode=execution_mode,
            conversation_status=conv_status,
            conversation_id=result.get("conversation_id", request.conversation_id),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
