"""
Statement Ingestion Router for FinSight.

Establishes the backend integration boundary for bank statement candidate ingestion.
Evaluates extracted candidates for validation and duplicates without persisting them directly to transactions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, Account, Document
from backend.auth.dependencies import get_current_user
from backend.schemas import (
    StatementUploadRequest,
    StatementUploadResponse,
    StatementEvaluatedCandidate,
)
from backend.ingestion.normalizer import normalize_transaction_input
from backend.ingestion.deduplicator import is_duplicate_transaction

router = APIRouter(tags=["Statement Ingestion"])


@router.post("/statements/upload", response_model=StatementUploadResponse, summary="Upload Statement Candidates")
@router.post("/api/v1/statements/upload", response_model=StatementUploadResponse, include_in_schema=False)
def upload_statement_candidates(
    payload: StatementUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatementUploadResponse:
    """
    Receives statement metadata and extracted transaction candidates for the authenticated user.
    Evaluates candidate validity and detects duplicates against existing transactions.
    Candidates are staged in the Document store and are NOT automatically written to the Transaction ledger.
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


    # Stage metadata into Document store
    doc = Document(
        user_id=authoritative_user_id,
        filename=payload.filename,
        document_type="bank_statement",
        mime_type="application/pdf",
        extracted_facts=[c.model_dump(mode="json") for c in payload.extracted_candidates],
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    evaluated_candidates: List[StatementEvaluatedCandidate] = []
    dup_count = 0

    for idx, candidate in enumerate(payload.extracted_candidates, 1):
        cand_id = candidate.reference_id or f"CAND-{doc.id}-{idx:03d}"

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
            # Mark invalid candidates as duplicates/unusable with reason
            evaluated_candidates.append(
                StatementEvaluatedCandidate(
                    candidate_id=cand_id,
                    reference_id=candidate.reference_id,
                    amount=candidate.amount,
                    transaction_type=candidate.transaction_type,
                    category=candidate.category,
                    merchant_name=candidate.merchant_name,
                    description=candidate.description,
                    transaction_date=candidate.transaction_date,
                    is_duplicate=True,
                    duplicate_reason=f"Validation failed: {str(e)}",
                )
            )
            dup_count += 1
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
            dup_count += 1

        evaluated_candidates.append(
            StatementEvaluatedCandidate(
                candidate_id=cand_id,
                reference_id=candidate.reference_id,
                amount=candidate.amount,
                transaction_type=candidate.transaction_type,
                category=normalized["category"],
                merchant_name=normalized["merchant_name"],
                description=normalized["description"],
                transaction_date=normalized["transaction_date"],
                is_duplicate=is_dup,
                duplicate_reason=dup_reason,
            )
        )

    valid_count = len(evaluated_candidates) - dup_count

    return StatementUploadResponse(
        document_id=doc.id,
        filename=payload.filename,
        total_candidates=len(evaluated_candidates),
        valid_candidates_count=valid_count,
        duplicate_candidates_count=dup_count,
        candidates=evaluated_candidates,
    )

