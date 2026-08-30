"""
Mock Bank Router for FinSight.

Simulates connection to a financial institution and deterministic bank feed synchronization.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, Account
from backend.auth.dependencies import get_current_user
from backend.schemas import (
    BankConnectRequest,
    BankConnectResponse,
    BankSyncRequest,
    BankSyncResponse,
    TransactionResponse,
    SkippedTransactionItem,
)
from backend.ingestion.bank_sync import sync_mock_bank_transactions

router = APIRouter(tags=["Bank Ingestion"])


@router.post("/bank/connect", response_model=BankConnectResponse, summary="Connect Mock Bank")
@router.post("/api/v1/bank/connect", response_model=BankConnectResponse, include_in_schema=False)
def connect_mock_bank(
    payload: BankConnectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankConnectResponse:
    """
    Simulates connecting the authenticated user's account to a mock financial institution.
    """
    authoritative_user_id = current_user.id

    if payload.account_id:
        account = db.query(Account).filter(Account.id == payload.account_id, Account.user_id == authoritative_user_id).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with id {payload.account_id} not found for authenticated user.",
            )
    else:
        account = db.query(Account).filter(Account.user_id == authoritative_user_id, Account.is_active == True).first()
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active account found for authenticated user.",
            )

    return BankConnectResponse(
        status="connected",
        institution_name=payload.institution_name,
        user_id=authoritative_user_id,
        account_id=account.id,
        message=f"Successfully connected account '{account.name}' to {payload.institution_name}.",
    )


@router.post("/bank/sync", response_model=BankSyncResponse, summary="Sync Mock Bank Transactions")
@router.post("/api/v1/bank/sync", response_model=BankSyncResponse, include_in_schema=False)
def sync_bank_feed(
    payload: BankSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BankSyncResponse:
    """
    Synchronizes deterministic mock bank transactions for the authenticated user and account.
    Repeated calls automatically skip duplicates.
    """
    authoritative_user_id = current_user.id

    try:
        sync_result = sync_mock_bank_transactions(
            user_id=authoritative_user_id,
            account_id=payload.account_id,
            db=db,
        )
    except ValueError as e:
        if "does not exist" in str(e) or "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    imported_responses = [TransactionResponse.model_validate(t) for t in sync_result["imported_transactions"]]
    skipped_items = [SkippedTransactionItem(**item) for item in sync_result["skipped_transactions"]]

    return BankSyncResponse(
        status="success",
        user_id=sync_result["user_id"],
        account_id=sync_result["account_id"],
        imported_count=sync_result["imported_count"],
        duplicate_count=sync_result["duplicate_count"],
        skipped_count=sync_result["skipped_count"],
        imported_transactions=imported_responses,
        skipped_transactions=skipped_items,
    )

