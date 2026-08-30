"""
Payments Router for FinSight.

Exposes the real deterministic payment preview and persistent confirmation
execution endpoints for the frontend and voice clients.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, PendingPayment
from backend.auth.dependencies import get_current_user
from backend.payment.payment_engine import preview_payment, execute_payment
from backend.payment.risk import evaluate_payment_risk
from backend.schemas import (
    PaymentPreviewRequest,
    PaymentPreviewResponse,
    PaymentExecuteRequest,
    PaymentExecuteResponse,
)

router = APIRouter(tags=["Payments"])


@router.post(
    "/payments/preview",
    response_model=PaymentPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview Payment and Stage Persistent Confirmation",
)
@router.post(
    "/api/v1/payments/preview",
    response_model=PaymentPreviewResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def preview_payment_endpoint(
    request: PaymentPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentPreviewResponse:
    """
    Computes a deterministic pre-payment preview, evaluates risk anomalies,
    and stages a persistent PendingPayment row in the database.

    Security & Safety Guarantees:
    - Zero database transactions are written during preview.
    - Deterministic risk assessment flags unusually large or anomalous payments.
    - Confirmation token/ID is generated and persisted for explicit user confirmation.
    - Staged strictly for the authenticated current_user.id.
    """
    user_id = current_user.id

    if not request.recipient_name or not request.recipient_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient name must be a non-empty string.",
        )

    if request.amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero.",
        )

    try:
        # 1. Deterministic payment preview
        preview_facts = preview_payment(
            user_id=user_id,
            amount=request.amount,
            recipient_name=request.recipient_name.strip(),
            db=db,
        )

        # 2. Deterministic payment risk evaluation
        risk_facts = evaluate_payment_risk(
            user_id=user_id,
            amount=request.amount,
            recipient_name=request.recipient_name.strip(),
            db=db,
        )

        # 3. Create persistent PendingPayment record (15-minute expiration)
        pending_payment = PendingPayment(
            user_id=user_id,
            amount=request.amount,
            recipient_name=request.recipient_name.strip(),
            status="pending",
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            created_at=datetime.utcnow(),
        )
        db.add(pending_payment)
        db.commit()
        db.refresh(pending_payment)

        return PaymentPreviewResponse(
            can_proceed=preview_facts["can_proceed"],
            amount=preview_facts["amount"],
            recipient_name=preview_facts["recipient_name"],
            current_balance=preview_facts["current_balance"],
            balance_after=preview_facts["balance_after"],
            upcoming_bills=preview_facts["upcoming_bills"],
            available_after_commitments=preview_facts["available_after_commitments"],
            risk_level=risk_facts["risk_level"],
            fraud_warning=risk_facts["fraud_warning"],
            risk_reasons=risk_facts["risk_reasons"],
            pending_payment_id=pending_payment.id,
            requires_confirmation=True,
            confirmation_token=str(pending_payment.id),
            reasoning_facts=preview_facts["reasoning_facts"],
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/payments/execute",
    response_model=PaymentExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Staged Pending Payment",
)
@router.post(
    "/api/v1/payments/execute",
    response_model=PaymentExecuteResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def execute_payment_endpoint(
    request: PaymentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentExecuteResponse:
    """
    Executes a previously staged PendingPayment upon explicit user confirmation.

    Security & Safety Guarantees:
    - User ownership verification against current_user.id.
    - Single-use execution (status must be 'pending').
    - Expiration check (cannot execute expired pending payments).
    - Amount and recipient are loaded strictly from the database record (anti-tampering).
    - Records an expense transaction (source='payment') and recalculates authoritative balance.
    """
    user_id = current_user.id

    pending_payment = (
        db.query(PendingPayment)
        .filter(PendingPayment.id == request.pending_payment_id)
        .first()
    )
    if not pending_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending payment with id {request.pending_payment_id} not found.",
        )

    # 1. User ownership check against authenticated current_user
    if pending_payment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Pending payment does not belong to the requesting user.",
        )


    # 2. Status verification
    if pending_payment.status == "executed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment has already been executed.",
        )
    elif pending_payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment cannot be executed because it is {pending_payment.status}.",
        )

    # 3. Expiration check
    if pending_payment.is_expired():
        pending_payment.status = "expired"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending payment has expired. Please initiate a new payment preview.",
        )

    # 4. Deterministic payment execution with tamper-proof DB values
    try:
        exec_facts = execute_payment(
            user_id=user_id,
            amount=pending_payment.amount,
            recipient_name=pending_payment.recipient_name,
            db=db,
        )


        # 5. Mark pending payment as executed
        pending_payment.status = "executed"
        db.commit()

        return PaymentExecuteResponse(
            success=True,
            transaction_id=exec_facts["transaction_id"],
            recipient_name=exec_facts["recipient_name"],
            amount=exec_facts["amount"],
            previous_balance=exec_facts["previous_balance"],
            new_balance=exec_facts["new_balance"],
            transaction_type="expense",
            pending_payment_id=pending_payment.id,
            status="executed",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
