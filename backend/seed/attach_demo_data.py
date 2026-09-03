"""
FinSight Demo Data Attachment Utility
======================================

Safely clones and attaches Aarav Sharma's 4-month synthetic financial dataset
(accounts, transactions, goals, bills, documents) to a target user account
without modifying User records, credentials, or the deterministic financial engine.

Architectural Guarantees:
1. User Isolation: All cloned records strictly point to target_user_id.
2. Zero Credential Mutation: Passwords, password hashes, and WebAuthn credentials are untouched.
3. Strict Determinism: Authoritative balance is SUM(transaction.amount) across transactions.
4. Idempotency: Re-running this utility cleanly syncs records without duplicating transactions or balances.
5. Dual-DB Synchronization: Applies to both the active backend database and the root database if present.
"""

import os
import sys
import argparse
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pathlib import Path

# Ensure standard output can handle UTF-8 symbols on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.models import User, Account, Transaction, Goal, Bill, Document, PendingPayment
from backend.engine import get_balance, get_spending_summary, check_affordability


def get_target_db_paths(explicit_path: Optional[str] = None) -> List[Path]:
    """Identifies all relevant SQLite database paths to keep development and runtime in sync."""
    if explicit_path:
        p = Path(explicit_path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Specified database file does not exist: {p}")
        return [p]

    paths = []
    root_db = PROJECT_ROOT / "finsight.db"
    backend_db = PROJECT_ROOT / "backend" / "finsight.db"

    if root_db.exists():
        paths.append(root_db)
    if backend_db.exists() and backend_db not in paths:
        paths.append(backend_db)

    if not paths:
        # Default fallback to standard DATABASE_URL or finsight.db in root
        paths.append(root_db)

    return paths


def attach_demo_data_to_user(
    db: Session,
    target_user_id: int,
    source_user_id: Optional[int] = 153,
    source_email: str = "aarav.sharma@example.com",
) -> Dict[str, Any]:
    """
    Idempotently copies financial records from the source demo user (Aarav Sharma)
    to the target user ID, remapping all foreign keys and preserving user isolation.
    """
    # 1. Validate Target User existence
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise ValueError(f"Target user with ID {target_user_id} does not exist in the database.")

    # 2. Locate Source User (Aarav)
    source_user = None
    if source_user_id:
        source_user = db.query(User).filter(User.id == source_user_id).first()
    if not source_user:
        source_user = db.query(User).filter(User.email == source_email).first()

    if not source_user:
        raise ValueError(
            f"Source synthetic demo user not found (checked ID: {source_user_id}, Email: {source_email}). "
            "Please run 'python -m backend.seed.generate_synthetic_data' first."
        )

    # 3. Retrieve Source Financial Records
    src_account = (
        db.query(Account)
        .filter(Account.user_id == source_user.id)
        .order_by(Account.id.asc())
        .first()
    )
    if not src_account:
        raise ValueError(f"Source user {source_user.id} has no accounts to clone.")

    src_transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id == src_account.id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    src_goals = db.query(Goal).filter(Goal.user_id == source_user.id).all()
    src_bills = db.query(Bill).filter(Bill.user_id == source_user.id).all()
    src_docs = db.query(Document).filter(Document.user_id == source_user.id).all()

    # 4. Prepare / Re-map Target Primary Account
    target_account = (
        db.query(Account)
        .filter(Account.user_id == target_user_id)
        .order_by(Account.id.asc())
        .first()
    )

    if not target_account:
        target_account = Account(
            user_id=target_user_id,
            name=src_account.name,
            account_type=src_account.account_type,
            balance=Decimal("0.00"),
            monthly_income=src_account.monthly_income,
            currency=src_account.currency,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(target_account)
        db.flush()
    else:
        # Update existing account metadata without changing ID
        target_account.name = src_account.name
        target_account.account_type = src_account.account_type
        target_account.monthly_income = src_account.monthly_income
        target_account.currency = src_account.currency
        target_account.is_active = True
        target_account.updated_at = datetime.utcnow()
        db.flush()

    # 5. Idempotent Transaction Synchronization
    # Remove any existing demo/synthetic transactions for target user to prevent duplication
    db.query(Transaction).filter(
        Transaction.user_id == target_user_id,
        Transaction.account_id == target_account.id,
    ).delete()
    db.flush()

    # Clone all 86 transactions with foreign keys remapped
    cloned_txs = []
    for idx, stx in enumerate(src_transactions):
        new_tx = Transaction(
            account_id=target_account.id,
            user_id=target_user_id,
            amount=stx.amount,
            currency=stx.currency,
            transaction_type=stx.transaction_type,
            category=stx.category,
            merchant_name=stx.merchant_name,
            description=stx.description,
            source="synthetic",
            reference_id=f"syn_usr{target_user_id}_{idx}_{int(stx.transaction_date.timestamp())}",
            transaction_date=stx.transaction_date,
            is_suspicious=stx.is_suspicious,
            created_at=stx.created_at or datetime.utcnow(),
        )
        db.add(new_tx)
        cloned_txs.append(new_tx)
    db.flush()

    # 6. Recalculate Authoritative Balance and Update Account Cache
    authoritative_balance = sum((t.amount for t in cloned_txs), Decimal("0.00"))
    target_account.balance = authoritative_balance
    db.flush()

    # 7. Idempotent Goals Synchronization
    for sg in src_goals:
        existing_goal = (
            db.query(Goal)
            .filter(Goal.user_id == target_user_id, Goal.name == sg.name)
            .first()
        )
        if existing_goal:
            existing_goal.target_amount = sg.target_amount
            existing_goal.current_amount = sg.current_amount
            existing_goal.monthly_contribution = sg.monthly_contribution
            existing_goal.currency = sg.currency
            existing_goal.target_date = sg.target_date
            existing_goal.status = sg.status
            existing_goal.updated_at = datetime.utcnow()
        else:
            new_goal = Goal(
                user_id=target_user_id,
                name=sg.name,
                target_amount=sg.target_amount,
                current_amount=sg.current_amount,
                monthly_contribution=sg.monthly_contribution,
                currency=sg.currency,
                target_date=sg.target_date,
                status=sg.status,
                created_at=sg.created_at or datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_goal)
    db.flush()

    # 8. Idempotent Bills Synchronization
    for sb in src_bills:
        existing_bill = (
            db.query(Bill)
            .filter(Bill.user_id == target_user_id, Bill.name == sb.name)
            .first()
        )
        if existing_bill:
            existing_bill.amount = sb.amount
            existing_bill.currency = sb.currency
            existing_bill.category = sb.category
            existing_bill.due_date = sb.due_date
            existing_bill.frequency = sb.frequency
            existing_bill.status = sb.status
            existing_bill.is_recurring = sb.is_recurring
            existing_bill.updated_at = datetime.utcnow()
        else:
            new_bill = Bill(
                user_id=target_user_id,
                name=sb.name,
                amount=sb.amount,
                currency=sb.currency,
                category=sb.category,
                due_date=sb.due_date,
                frequency=sb.frequency,
                status=sb.status,
                is_recurring=sb.is_recurring,
                created_at=sb.created_at or datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_bill)
    db.flush()

    # 9. Idempotent Documents Synchronization
    for sd in src_docs:
        existing_doc = (
            db.query(Document)
            .filter(Document.user_id == target_user_id, Document.filename == sd.filename)
            .first()
        )
        if existing_doc:
            existing_doc.file_path = sd.file_path
            existing_doc.document_type = sd.document_type
            existing_doc.mime_type = sd.mime_type
            existing_doc.raw_text = sd.raw_text
            existing_doc.extracted_facts = sd.extracted_facts
            existing_doc.is_suspicious = sd.is_suspicious
            existing_doc.updated_at = datetime.utcnow()
        else:
            new_doc = Document(
                user_id=target_user_id,
                filename=sd.filename,
                file_path=sd.file_path,
                document_type=sd.document_type,
                mime_type=sd.mime_type,
                raw_text=sd.raw_text,
                extracted_facts=sd.extracted_facts,
                is_suspicious=sd.is_suspicious,
                created_at=sd.created_at or datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(new_doc)
    db.flush()

    # Commit all changes atomically
    db.commit()

    return {
        "target_user_id": target_user_id,
        "target_user_email": target_user.email,
        "account_id": target_account.id,
        "authoritative_balance": authoritative_balance,
        "transactions_copied": len(cloned_txs),
        "goals_count": db.query(Goal).filter(Goal.user_id == target_user_id).count(),
        "bills_count": db.query(Bill).filter(Bill.user_id == target_user_id).count(),
        "documents_count": db.query(Document).filter(Document.user_id == target_user_id).count(),
    }


def verify_user_financial_state(db: Session, target_user_id: int) -> Dict[str, Any]:
    """Runs rigorous verification on financial engine and AI queries for target user."""
    user = db.query(User).filter(User.id == target_user_id).first()
    if not user:
        raise ValueError(f"User {target_user_id} not found during verification.")

    tx_count = db.query(Transaction).filter(Transaction.user_id == target_user_id).count()
    goals = db.query(Goal).filter(Goal.user_id == target_user_id).all()
    bills = db.query(Bill).filter(Bill.user_id == target_user_id, Bill.status == "unpaid").all()

    # 1. Deterministic Financial Engine checks
    balance_info = get_balance(target_user_id, db)
    authoritative_balance = balance_info["balance"]

    spending_info = get_spending_summary(target_user_id, db, period="this_month")
    monthly_spending = spending_info["total"]

    affordability_info = check_affordability(target_user_id, Decimal("8000.00"), db)

    # 2. AI Pipeline integration checks
    from ai.pipeline import AIPipeline
    balance_ai = AIPipeline.process_query(user_id=target_user_id, query="What's my balance?", db=db)
    spend_ai = AIPipeline.process_query(user_id=target_user_id, query="How much did I spend this month?", db=db)
    afford_ai = AIPipeline.process_query(user_id=target_user_id, query="Can I afford headphones for ₹8,000?", db=db)

    return {
        "user_id": target_user_id,
        "email": user.email,
        "name": user.full_name,
        "authoritative_balance": authoritative_balance,
        "transactions_count": tx_count,
        "active_goals": [{"name": g.name, "target": g.target_amount, "current": g.current_amount} for g in goals],
        "unpaid_bills_count": len(bills),
        "unpaid_bills_total": sum((b.amount for b in bills), Decimal("0.00")),
        "monthly_spending": monthly_spending,
        "afford_8000_result": affordability_info["can_afford"],
        "afford_balance_after": affordability_info["balance_after"],
        "ai_balance_answer": balance_ai["answer_text"],
        "ai_spend_answer": spend_ai["answer_text"],
        "ai_afford_answer": afford_ai["answer_text"],
    }


def main():
    parser = argparse.ArgumentParser(description="FinSight Demo Data Attachment Utility")
    parser.add_argument("--user-id", type=int, default=154, help="Target user ID (default: 154)")
    parser.add_argument("--source-user-id", type=int, default=153, help="Source user ID (default: 153)")
    parser.add_argument("--source-email", type=str, default="aarav.sharma@example.com", help="Source user email")
    parser.add_argument("--db-path", type=str, default=None, help="Explicit SQLite DB file path (optional)")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing state without copying")

    args = parser.parse_args()

    db_paths = get_target_db_paths(args.db_path)
    print(f"Target databases to process ({len(db_paths)}): {[str(p) for p in db_paths]}")

    for db_path in db_paths:
        print(f"\n=======================================================")
        print(f"Processing Database: {db_path.name} ({db_path})")
        print(f"=======================================================")

        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionMaker()

        try:
            target_user = db.query(User).filter(User.id == args.user_id).first()
            if not target_user:
                print(f"Notice: User {args.user_id} does not exist in {db_path.name}. Skipping this database.")
                continue

            if not args.verify_only:
                result = attach_demo_data_to_user(
                    db=db,
                    target_user_id=args.user_id,
                    source_user_id=args.source_user_id,
                    source_email=args.source_email,
                )
                print(f"Successfully attached demo data to User {result['target_user_id']} ({result['target_user_email']}):")
                print(f"  - Account ID: {result['account_id']}")
                print(f"  - Authoritative Balance: ₹{result['authoritative_balance']:,.2f}")
                print(f"  - Transactions Copied: {result['transactions_copied']}")
                print(f"  - Active Goals: {result['goals_count']}")
                print(f"  - Upcoming Bills: {result['bills_count']}")
                print(f"  - Documents: {result['documents_count']}")

            # Verification
            print("\n--- Verifying Target User State ---")
            verification = verify_user_financial_state(db, args.user_id)
            print(f"User ID: {verification['user_id']} ({verification['email']})")
            print(f"Balance: ₹{verification['authoritative_balance']:,.2f} (Non-zero: {verification['authoritative_balance'] > 0})")
            print(f"Transactions: {verification['transactions_count']} (Expected: 86)")
            print(f"Active Goals: {len(verification['active_goals'])} ({verification['active_goals'][0]['name'] if verification['active_goals'] else 'None'})")
            print(f"Upcoming Bills: {verification['unpaid_bills_count']} (Total: ₹{verification['unpaid_bills_total']:,.2f})")
            print(f"Monthly Spending: ₹{verification['monthly_spending']:,.2f}")
            print(f"Can Afford ₹8,000?: {verification['afford_8000_result']} (Balance After: ₹{verification['afford_balance_after']:,.2f})")
            print(f"\nAI Copilot Answers:")
            print(f"  [Balance]: {verification['ai_balance_answer']}")
            print(f"  [Spending]: {verification['ai_spend_answer']}")
            print(f"  [Affordability]: {verification['ai_afford_answer']}")

            # Invariant Assertions
            assert verification['authoritative_balance'] > Decimal("0.00"), "Authoritative balance must be positive"
            assert verification['transactions_count'] == 86, f"Expected 86 transactions, got {verification['transactions_count']}"
            assert len(verification['active_goals']) >= 1, "Expected at least 1 active goal"
            assert verification['unpaid_bills_count'] == 3, f"Expected 3 unpaid bills, got {verification['unpaid_bills_count']}"
            assert verification['afford_8000_result'] is True, "Affordability check for ₹8,000 must succeed"
            print(f"\n>>> Database {db_path.name}: ALL ASSERTIONS PASSED! <<<")

        finally:
            db.close()


if __name__ == "__main__":
    main()
