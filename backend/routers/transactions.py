"""
Transactions Router for FinSight.

Provides transaction history, voice transaction ingestion, and statement candidate confirmation.
"""

from typing import List, Dict, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import extract

from backend.db import get_db
from backend.models import User, Account, Transaction, Document
from backend.auth.dependencies import get_current_user
from backend.engine import get_balance, get_spending_summary
from backend.engine.financial_engine import _get_previous_calendar_month
from backend.schemas import (
    TransactionsListResponse,
    TransactionResponse,
    VoiceTransactionRequest,
    ConfirmTransactionsRequest,
    ConfirmTransactionsResponse,
    SkippedTransactionItem,
)
from backend.ingestion.normalizer import normalize_transaction_input
from backend.ingestion.deduplicator import is_duplicate_transaction

router = APIRouter(tags=["Transactions"])


@router.get("/transactions", response_model=TransactionsListResponse, summary="Get User Transactions")
@router.get("/api/v1/transactions", response_model=TransactionsListResponse, include_in_schema=False)
def get_user_transactions(
    user_id: Optional[int] = Query(None, description="Optional legacy demo user ID (overridden by authenticated JWT identity)"),
    period: str = Query("this_month", description="Period to filter ('this_month' or 'last_month')"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionsListResponse:
    """
    Returns transaction history for the authenticated user and period, along with deterministic
    category spending totals.
    """
    authoritative_user_id = current_user.id

    if period not in ("this_month", "last_month"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported period '{period}'. Supported periods are: 'this_month', 'last_month'.",
        )

    # 1. Obtain categorical totals directly from the deterministic financial engine
    spending_summary = get_spending_summary(authoritative_user_id, db, period=period)
    by_category: Dict[str, Decimal] = spending_summary["by_category"]

    # 2. Determine calendar period range matching the financial engine
    balance_info = get_balance(authoritative_user_id, db)
    as_of = balance_info["as_of"]

    if not as_of:
        return TransactionsListResponse(transactions=[], by_category=by_category)

    if period == "this_month":
        target_year, target_month = as_of.year, as_of.month
    else:  # "last_month"
        target_year, target_month = _get_previous_calendar_month(as_of.year, as_of.month)

    # 3. Query transactions with strict user ownership and period filtering
    transactions = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Account.user_id == authoritative_user_id,
            Transaction.user_id == authoritative_user_id,
            extract("year", Transaction.transaction_date) == target_year,
            extract("month", Transaction.transaction_date) == target_month,
        )
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    transactions_responses = [TransactionResponse.model_validate(t) for t in transactions]

    return TransactionsListResponse(
        transactions=transactions_responses,
        by_category=by_category,
    )


@router.post("/transactions/voice", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, summary="Ingest Voice Transaction")
@router.post("/api/v1/transactions/voice", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def ingest_voice_transaction(
    payload: VoiceTransactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Accepts structured transaction JSON from the voice/AI layer for the authenticated user,
    validates inputs, normalizes the sign convention, and stores it with source='voice'.
    """
    authoritative_user_id = current_user.id

    if payload.account_id:
        account = db.query(Account).filter(Account.id == payload.account_id, Account.user_id == authoritative_user_id).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {payload.account_id} not found for user {authoritative_user_id}.",
            )
    else:
        account = db.query(Account).filter(Account.user_id == authoritative_user_id, Account.is_active == True).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active account found for user {authoritative_user_id}.",
            )

    try:
        normalized = normalize_transaction_input(
            amount=payload.amount,
            transaction_type=payload.transaction_type,
            category=payload.category,
            merchant_name=payload.merchant_name,
            description=payload.description,
            transaction_date=payload.transaction_date,
            source="voice",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    tx = Transaction(
        account_id=account.id,
        user_id=authoritative_user_id,
        amount=normalized["amount"],
        currency="INR",
        transaction_type=normalized["transaction_type"],
        category=normalized["category"],
        merchant_name=normalized["merchant_name"],
        description=normalized["description"],
        source="voice",
        reference_id=None,
        transaction_date=normalized["transaction_date"],
        is_suspicious=False,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    return TransactionResponse.model_validate(tx)


@router.post("/transactions/confirm", response_model=ConfirmTransactionsResponse, summary="Confirm Statement Candidates")
@router.post("/api/v1/transactions/confirm", response_model=ConfirmTransactionsResponse, include_in_schema=False)
def confirm_statement_transactions(
    payload: ConfirmTransactionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfirmTransactionsResponse:
    """
    Confirms validated statement transaction candidates for the authenticated user and
    persists them into the Transaction table with source='statement'. Skips any duplicate items.
    """
    authoritative_user_id = current_user.id

    # Verify document ownership if document_id is provided
    if payload.document_id is not None:
        doc = (
            db.query(Document)
            .filter(Document.id == payload.document_id, Document.user_id == authoritative_user_id)
            .first()
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with id {payload.document_id} not found for user {authoritative_user_id}.",
            )


    if payload.account_id:
        account = db.query(Account).filter(Account.id == payload.account_id, Account.user_id == authoritative_user_id).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {payload.account_id} not found for user {authoritative_user_id}.",
            )
    else:
        account = db.query(Account).filter(Account.user_id == authoritative_user_id, Account.is_active == True).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active account found for user {authoritative_user_id}.",
            )


    confirmed_txs: List[Transaction] = []
    skipped_items: List[SkippedTransactionItem] = []

    for candidate in payload.candidates:
        try:
            normalized = normalize_transaction_input(
                amount=candidate.amount,
                transaction_type=candidate.transaction_type,
                category=candidate.category,
                merchant_name=candidate.merchant_name,
                description=candidate.description,
                transaction_date=candidate.transaction_date,
                source="statement",
                reference_id=candidate.reference_id,
            )
        except ValueError as e:
            skipped_items.append(
                SkippedTransactionItem(
                    reference_id=candidate.reference_id,
                    merchant_name=candidate.merchant_name,
                    amount=str(candidate.amount),
                    reason=f"Validation failed: {str(e)}",
                )
            )
            continue

        is_dup, dup_id, dup_reason = is_duplicate_transaction(
            db=db,
            account_id=account.id,
            user_id=authoritative_user_id,
            amount=normalized["amount"],
            transaction_date=normalized["transaction_date"],
            merchant_name=normalized["merchant_name"],
            reference_id=normalized["reference_id"],
        )

        if is_dup:
            skipped_items.append(
                SkippedTransactionItem(
                    reference_id=normalized["reference_id"],
                    merchant_name=normalized["merchant_name"],
                    amount=str(normalized["amount"]),
                    reason=dup_reason,
                    existing_transaction_id=dup_id,
                )
            )
        else:
            new_tx = Transaction(
                account_id=account.id,
                user_id=authoritative_user_id,
                amount=normalized["amount"],
                currency="INR",
                transaction_type=normalized["transaction_type"],
                category=normalized["category"],
                merchant_name=normalized["merchant_name"],
                description=normalized["description"],
                source="statement",
                reference_id=normalized["reference_id"],
                transaction_date=normalized["transaction_date"],
                is_suspicious=False,
            )
            db.add(new_tx)
            db.flush()
            confirmed_txs.append(new_tx)

    db.commit()

    for tx in confirmed_txs:
        db.refresh(tx)

    tx_responses = [TransactionResponse.model_validate(t) for t in confirmed_txs]

    return ConfirmTransactionsResponse(
        status="success",
        confirmed_count=len(tx_responses),
        skipped_duplicates_count=len(skipped_items),
        transactions=tx_responses,
        skipped_items=skipped_items,
    )

