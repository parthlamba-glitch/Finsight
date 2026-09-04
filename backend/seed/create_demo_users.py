"""
FinSight Dedicated Demo Users Seeding Utility
==============================================

Creates hackathon-ready demo accounts with predefined passwords and comprehensive,
deterministic multi-month financial datasets into the active FastAPI backend database.

Accounts created:
1. demo@finsight.com (Name: FinSight Demo User)
   - Password: Demo@123
   - Balance: ~₹138,372.00
   - 86 transactions (May 2026 - August 2026)
   - Emergency Fund goal (target ₹150,000, current ₹45,000)
   - 3 upcoming bills totaling ₹6,529.00
   - Full category spending & subscription price increase data for AI insights

2. student@finsight.com (Name: Student Demo)
   - Password: Student@123
   - Balance: ~₹22,700.00
   - 61 transactions (May 2026 - August 2026)
   - Laptop Upgrade Fund goal (target ₹50,000, current ₹15,000)
   - 3 upcoming bills totaling ₹3,858.00
   - Student spending patterns (stipend, hostel, food, books, Spotify student)

ARCHITECTURAL GUARANTEES:
1. Targets the EXACT SQLite database configured by backend.db.
2. 100% Idempotent: safely re-runnable without duplicating users, accounts, transactions, goals, or bills.
3. Preserves all existing real user accounts and financial data.
4. Passwords securely hashed with bcrypt using backend.auth.security.hash_password.
5. Authoritative balance is computed deterministically as SUM(transaction.amount).
"""

import sys
import os
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Optional

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

from sqlalchemy.orm import Session
from backend.db import SessionLocal, engine, init_db
from backend.models import User, Account, Transaction, Goal, Bill, Document
from backend.models.user import DEFAULT_ACCESSIBILITY_PREFS
from backend.auth.security import hash_password
from backend.engine import get_balance, get_spending_summary, get_insights, check_affordability
from backend.seed.generate_synthetic_data import seed_synthetic_data, DEMO_EMAIL as AARAV_EMAIL
from backend.seed.attach_demo_data import attach_demo_data_to_user


# =============================================================================
# 1. Student Demo Deterministic Transaction Dataset
# =============================================================================

def get_student_raw_transactions() -> List[Dict[str, Any]]:
    """Returns 61 deterministic transactions for student@finsight.com spanning May-Aug 2026."""
    return [
        # --- Opening Balance & May 2026 ---
        {"date": datetime(2026, 4, 30, 20, 0, 0), "amount": Decimal("5000.00"), "type": "income", "category": "Other", "merchant": None, "desc": "Opening Balance"},
        {"date": datetime(2026, 5, 1, 9, 0, 0), "amount": Decimal("25000.00"), "type": "income", "category": "Other", "merchant": "University Labs", "desc": "Internship Stipend Credit"},
        {"date": datetime(2026, 5, 2, 10, 0, 0), "amount": Decimal("-10000.00"), "type": "expense", "category": "Bills", "merchant": "Campus Living PG", "desc": "Monthly PG Accommodation Fee"},
        {"date": datetime(2026, 5, 3, 11, 30, 0), "amount": Decimal("-1200.00"), "type": "expense", "category": "Food", "merchant": "Blinkit", "desc": "Hostel Snacks & Essentials"},
        {"date": datetime(2026, 5, 4, 12, 0, 0), "amount": Decimal("-299.00"), "type": "expense", "category": "Bills", "merchant": "Jio", "desc": "Jio Prepaid 5G Plan Recharge"},
        {"date": datetime(2026, 5, 5, 14, 0, 0), "amount": Decimal("-59.00"), "type": "expense", "category": "Entertainment", "merchant": "Spotify", "desc": "Spotify Student Premium"},
        {"date": datetime(2026, 5, 6, 8, 30, 0), "amount": Decimal("-500.00"), "type": "expense", "category": "Transport", "merchant": "Namma Metro", "desc": "Metro Card Recharge"},
        {"date": datetime(2026, 5, 8, 13, 0, 0), "amount": Decimal("-450.00"), "type": "expense", "category": "Food", "merchant": "Campus Canteen", "desc": "Canteen Meals"},
        {"date": datetime(2026, 5, 10, 16, 0, 0), "amount": Decimal("-1450.00"), "type": "expense", "category": "Education", "merchant": "Sapna Book House", "desc": "Semester Engineering Textbooks"},
        {"date": datetime(2026, 5, 14, 20, 0, 0), "amount": Decimal("-720.00"), "type": "expense", "category": "Food", "merchant": "Swiggy", "desc": "Team Study Dinner"},
        {"date": datetime(2026, 5, 16, 18, 0, 0), "amount": Decimal("-650.00"), "type": "expense", "category": "Entertainment", "merchant": "BookMyShow", "desc": "Weekend Movie with Friends"},
        {"date": datetime(2026, 5, 18, 11, 0, 0), "amount": Decimal("-1150.00"), "type": "expense", "category": "Food", "merchant": "Zepto", "desc": "Fruits and Dairy"},
        {"date": datetime(2026, 5, 20, 9, 0, 0), "amount": Decimal("-250.00"), "type": "expense", "category": "Transport", "merchant": "Uber Auto", "desc": "Auto Ride to Campus"},
        {"date": datetime(2026, 5, 23, 20, 30, 0), "amount": Decimal("-550.00"), "type": "expense", "category": "Food", "merchant": "Zomato", "desc": "Dinner Delivery"},
        {"date": datetime(2026, 5, 25, 15, 0, 0), "amount": Decimal("-1100.00"), "type": "expense", "category": "Shopping", "merchant": "Myntra", "desc": "Summer College T-Shirts"},
        {"date": datetime(2026, 5, 28, 17, 0, 0), "amount": Decimal("-1350.00"), "type": "expense", "category": "Food", "merchant": "Local Supermarket", "desc": "Monthly Staples"},

        # --- June 2026 ---
        {"date": datetime(2026, 6, 1, 9, 0, 0), "amount": Decimal("25000.00"), "type": "income", "category": "Other", "merchant": "University Labs", "desc": "Internship Stipend Credit"},
        {"date": datetime(2026, 6, 2, 10, 0, 0), "amount": Decimal("-10000.00"), "type": "expense", "category": "Bills", "merchant": "Campus Living PG", "desc": "Monthly PG Accommodation Fee"},
        {"date": datetime(2026, 6, 3, 11, 30, 0), "amount": Decimal("-1300.00"), "type": "expense", "category": "Food", "merchant": "Blinkit", "desc": "Hostel Snacks & Essentials"},
        {"date": datetime(2026, 6, 4, 12, 0, 0), "amount": Decimal("-299.00"), "type": "expense", "category": "Bills", "merchant": "Jio", "desc": "Jio Prepaid 5G Plan Recharge"},
        {"date": datetime(2026, 6, 5, 14, 0, 0), "amount": Decimal("-59.00"), "type": "expense", "category": "Entertainment", "merchant": "Spotify", "desc": "Spotify Student Premium"},
        {"date": datetime(2026, 6, 6, 8, 30, 0), "amount": Decimal("-500.00"), "type": "expense", "category": "Transport", "merchant": "Namma Metro", "desc": "Metro Card Recharge"},
        {"date": datetime(2026, 6, 8, 13, 0, 0), "amount": Decimal("-500.00"), "type": "expense", "category": "Food", "merchant": "Campus Canteen", "desc": "Canteen Meals"},
        {"date": datetime(2026, 6, 12, 16, 0, 0), "amount": Decimal("-650.00"), "type": "expense", "category": "Education", "merchant": "College Stationery", "desc": "Lab Manuals & Engineering Paper"},
        {"date": datetime(2026, 6, 14, 20, 0, 0), "amount": Decimal("-820.00"), "type": "expense", "category": "Food", "merchant": "Swiggy", "desc": "Study Group Pizza"},
        {"date": datetime(2026, 6, 18, 9, 0, 0), "amount": Decimal("-280.00"), "type": "expense", "category": "Transport", "merchant": "Uber Auto", "desc": "Auto Ride to Campus"},
        {"date": datetime(2026, 6, 19, 11, 0, 0), "amount": Decimal("-1200.00"), "type": "expense", "category": "Food", "merchant": "Zepto", "desc": "Groceries & Fruit"},
        {"date": datetime(2026, 6, 21, 18, 0, 0), "amount": Decimal("-750.00"), "type": "expense", "category": "Entertainment", "merchant": "BookMyShow", "desc": "Weekend Cinema Ticket"},
        {"date": datetime(2026, 6, 24, 20, 30, 0), "amount": Decimal("-600.00"), "type": "expense", "category": "Food", "merchant": "Zomato", "desc": "Dinner Delivery"},
        {"date": datetime(2026, 6, 25, 15, 0, 0), "amount": Decimal("-1450.00"), "type": "expense", "category": "Shopping", "merchant": "Decathlon", "desc": "Sports Shoes & Water Bottle"},
        {"date": datetime(2026, 6, 28, 17, 0, 0), "amount": Decimal("-1260.00"), "type": "expense", "category": "Food", "merchant": "Local Supermarket", "desc": "Monthly Essentials"},

        # --- July 2026 ---
        {"date": datetime(2026, 7, 1, 9, 0, 0), "amount": Decimal("25000.00"), "type": "income", "category": "Other", "merchant": "University Labs", "desc": "Internship Stipend Credit"},
        {"date": datetime(2026, 7, 2, 10, 0, 0), "amount": Decimal("-10000.00"), "type": "expense", "category": "Bills", "merchant": "Campus Living PG", "desc": "Monthly PG Accommodation Fee"},
        {"date": datetime(2026, 7, 3, 11, 30, 0), "amount": Decimal("-1350.00"), "type": "expense", "category": "Food", "merchant": "Blinkit", "desc": "Hostel Snacks & Essentials"},
        {"date": datetime(2026, 7, 4, 12, 0, 0), "amount": Decimal("-299.00"), "type": "expense", "category": "Bills", "merchant": "Jio", "desc": "Jio Prepaid 5G Plan Recharge"},
        {"date": datetime(2026, 7, 5, 14, 0, 0), "amount": Decimal("-59.00"), "type": "expense", "category": "Entertainment", "merchant": "Spotify", "desc": "Spotify Student Premium"},
        {"date": datetime(2026, 7, 6, 8, 30, 0), "amount": Decimal("-500.00"), "type": "expense", "category": "Transport", "merchant": "Namma Metro", "desc": "Metro Card Recharge"},
        {"date": datetime(2026, 7, 8, 13, 0, 0), "amount": Decimal("-520.00"), "type": "expense", "category": "Food", "merchant": "Campus Canteen", "desc": "Canteen Meals"},
        {"date": datetime(2026, 7, 13, 20, 0, 0), "amount": Decimal("-850.00"), "type": "expense", "category": "Food", "merchant": "Swiggy", "desc": "Dinner Delivery"},
        {"date": datetime(2026, 7, 15, 16, 0, 0), "amount": Decimal("-2100.00"), "type": "expense", "category": "Education", "merchant": "Amazon India", "desc": "Electronics Microcontroller Lab Kit"},
        {"date": datetime(2026, 7, 18, 11, 0, 0), "amount": Decimal("-1250.00"), "type": "expense", "category": "Food", "merchant": "Zepto", "desc": "Groceries & Juices"},
        {"date": datetime(2026, 7, 19, 17, 0, 0), "amount": Decimal("-600.00"), "type": "expense", "category": "Entertainment", "merchant": "Gaming Cafe", "desc": "LAN Gaming Session"},
        {"date": datetime(2026, 7, 22, 9, 0, 0), "amount": Decimal("-300.00"), "type": "expense", "category": "Transport", "merchant": "Uber Auto", "desc": "Auto Ride to Campus"},
        {"date": datetime(2026, 7, 23, 20, 30, 0), "amount": Decimal("-620.00"), "type": "expense", "category": "Food", "merchant": "Zomato", "desc": "Late Night Study Snack"},
        {"date": datetime(2026, 7, 27, 17, 0, 0), "amount": Decimal("-1250.00"), "type": "expense", "category": "Food", "merchant": "Local Supermarket", "desc": "Hostel Supplies"},
        {"date": datetime(2026, 7, 29, 15, 0, 0), "amount": Decimal("-1200.00"), "type": "expense", "category": "Shopping", "merchant": "Amazon India", "desc": "Laptop Sleeve & Backpack"},

        # --- August 2026 (Spike in Food Spending for AI Insight: ₹7,250 vs ₹5,840 July -> +24.1%) ---
        {"date": datetime(2026, 8, 1, 9, 0, 0), "amount": Decimal("25000.00"), "type": "income", "category": "Other", "merchant": "University Labs", "desc": "Internship Stipend Credit"},
        {"date": datetime(2026, 8, 2, 10, 0, 0), "amount": Decimal("-10000.00"), "type": "expense", "category": "Bills", "merchant": "Campus Living PG", "desc": "Monthly PG Accommodation Fee"},
        {"date": datetime(2026, 8, 3, 11, 30, 0), "amount": Decimal("-1650.00"), "type": "expense", "category": "Food", "merchant": "Blinkit", "desc": "Hostel Snacks & Team Refreshments"},
        {"date": datetime(2026, 8, 4, 12, 0, 0), "amount": Decimal("-299.00"), "type": "expense", "category": "Bills", "merchant": "Jio", "desc": "Jio Prepaid 5G Plan Recharge"},
        {"date": datetime(2026, 8, 5, 14, 0, 0), "amount": Decimal("-59.00"), "type": "expense", "category": "Entertainment", "merchant": "Spotify", "desc": "Spotify Student Premium"},
        {"date": datetime(2026, 8, 6, 8, 30, 0), "amount": Decimal("-500.00"), "type": "expense", "category": "Transport", "merchant": "Namma Metro", "desc": "Metro Card Recharge"},
        {"date": datetime(2026, 8, 8, 13, 0, 0), "amount": Decimal("-650.00"), "type": "expense", "category": "Food", "merchant": "Campus Canteen", "desc": "Lunch with Project Mentors"},
        {"date": datetime(2026, 8, 10, 16, 0, 0), "amount": Decimal("-850.00"), "type": "expense", "category": "Education", "merchant": "Sapna Book House", "desc": "Competitive Exam Prep Guides"},
        {"date": datetime(2026, 8, 13, 20, 0, 0), "amount": Decimal("-1150.00"), "type": "expense", "category": "Food", "merchant": "Swiggy", "desc": "Project Team Milestone Dinner"},
        {"date": datetime(2026, 8, 15, 18, 0, 0), "amount": Decimal("-850.00"), "type": "expense", "category": "Entertainment", "merchant": "BookMyShow", "desc": "Independence Day Movie & Popcorn"},
        {"date": datetime(2026, 8, 17, 11, 0, 0), "amount": Decimal("-1450.00"), "type": "expense", "category": "Food", "merchant": "Zepto", "desc": "Groceries & Semester Snacks"},
        {"date": datetime(2026, 8, 20, 9, 0, 0), "amount": Decimal("-320.00"), "type": "expense", "category": "Transport", "merchant": "Uber Auto", "desc": "Auto Ride to Campus"},
        {"date": datetime(2026, 8, 21, 15, 0, 0), "amount": Decimal("-1878.00"), "type": "expense", "category": "Shopping", "merchant": "Myntra", "desc": "Campus Walking Sneakers"},
        {"date": datetime(2026, 8, 22, 20, 30, 0), "amount": Decimal("-850.00"), "type": "expense", "category": "Food", "merchant": "Zomato", "desc": "Weekend Treat Delivery"},
        {"date": datetime(2026, 8, 26, 17, 0, 0), "amount": Decimal("-1500.00"), "type": "expense", "category": "Food", "merchant": "Local Supermarket", "desc": "Semester Food Staples"},
    ]


# =============================================================================
# 2. Idempotent User & Account Creation Helpers
# =============================================================================

def get_or_create_demo_user(
    db: Session,
    email: str,
    full_name: str,
    plain_password: str,
) -> User:
    """Idempotently finds or creates a user account with a secure bcrypt password hash."""
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    hashed_pw = hash_password(plain_password)

    if user:
        # Update user attributes safely without touching ID
        user.full_name = full_name.strip()
        user.hashed_password = hashed_pw
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.flush()
    else:
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            hashed_password=hashed_pw,
            accessibility_prefs=dict(DEFAULT_ACCESSIBILITY_PREFS),
            is_active=True,
            created_at=datetime(2026, 4, 30, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(user)
        db.flush()

    return user


def get_or_create_primary_account(
    db: Session,
    user_id: int,
    name: str,
    account_type: str = "savings",
    monthly_income: Decimal = Decimal("25000.00"),
) -> Account:
    """Finds or creates a primary account for the target user."""
    account = db.query(Account).filter(Account.user_id == user_id).order_by(Account.id.asc()).first()
    if account:
        account.name = name
        account.account_type = account_type
        account.monthly_income = monthly_income
        account.is_active = True
        account.updated_at = datetime.utcnow()
        db.flush()
    else:
        account = Account(
            user_id=user_id,
            name=name,
            account_type=account_type,
            balance=Decimal("0.00"),
            monthly_income=monthly_income,
            currency="INR",
            is_active=True,
            created_at=datetime(2026, 4, 30, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(account)
        db.flush()

    return account


# =============================================================================
# 3. Student Demo Data Seeder (Idempotent)
# =============================================================================

def seed_student_demo_dataset(db: Session, student_user_id: int) -> Dict[str, Any]:
    """Populates deterministic multi-month financial dataset for the student user."""
    account = get_or_create_primary_account(
        db=db,
        user_id=student_user_id,
        name="SBI Student Savings",
        account_type="savings",
        monthly_income=Decimal("25000.00"),
    )

    # Clean existing transactions for this user only
    db.query(Transaction).filter(
        Transaction.user_id == student_user_id,
        Transaction.account_id == account.id,
    ).delete()
    db.flush()

    raw_txs = get_student_raw_transactions()
    tx_entities = []
    for idx, t in enumerate(raw_txs):
        tx = Transaction(
            account_id=account.id,
            user_id=student_user_id,
            amount=t["amount"],
            currency="INR",
            transaction_type=t["type"],
            category=t["category"],
            merchant_name=t["merchant"],
            description=t["desc"],
            source="synthetic",
            reference_id=f"syn_std_{student_user_id}_{idx}_{int(t['date'].timestamp())}",
            transaction_date=t["date"],
            is_suspicious=False,
            created_at=t["date"],
        )
        tx_entities.append(tx)
        db.add(tx)
    db.flush()

    authoritative_balance = sum((t.amount for t in tx_entities), Decimal("0.00"))
    account.balance = authoritative_balance
    db.flush()

    # Idempotent Goal: Laptop Upgrade Fund
    goal = db.query(Goal).filter(Goal.user_id == student_user_id, Goal.name == "Laptop Upgrade Fund").first()
    if goal:
        goal.target_amount = Decimal("50000.00")
        goal.current_amount = Decimal("15000.00")
        goal.monthly_contribution = Decimal("3000.00")
        goal.target_date = date(2027, 4, 30)
        goal.status = "active"
        goal.updated_at = datetime.utcnow()
    else:
        goal = Goal(
            user_id=student_user_id,
            name="Laptop Upgrade Fund",
            target_amount=Decimal("50000.00"),
            current_amount=Decimal("15000.00"),
            monthly_contribution=Decimal("3000.00"),
            currency="INR",
            target_date=date(2027, 4, 30),
            status="active",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(goal)
    db.flush()

    # Idempotent Bills (3 unpaid bills totaling ₹3,858)
    bills_specs = [
        {"name": "Jio 5G Mobile Recharge", "amount": Decimal("299.00"), "due": date(2026, 9, 2), "cat": "Bills"},
        {"name": "Spotify Student Premium", "amount": Decimal("59.00"), "due": date(2026, 9, 5), "cat": "Entertainment"},
        {"name": "Hostel Mess Advance", "amount": Decimal("3500.00"), "due": date(2026, 9, 8), "cat": "Bills"},
    ]
    for b_spec in bills_specs:
        existing_bill = db.query(Bill).filter(Bill.user_id == student_user_id, Bill.name == b_spec["name"]).first()
        if existing_bill:
            existing_bill.amount = b_spec["amount"]
            existing_bill.due_date = b_spec["due"]
            existing_bill.category = b_spec["cat"]
            existing_bill.status = "unpaid"
            existing_bill.is_recurring = True
            existing_bill.updated_at = datetime.utcnow()
        else:
            new_b = Bill(
                user_id=student_user_id,
                name=b_spec["name"],
                amount=b_spec["amount"],
                currency="INR",
                category=b_spec["cat"],
                due_date=b_spec["due"],
                frequency="monthly",
                status="unpaid",
                is_recurring=True,
                created_at=datetime(2026, 8, 20, 10, 0, 0),
                updated_at=datetime(2026, 8, 20, 10, 0, 0),
            )
            db.add(new_b)
    db.flush()

    # Idempotent Sample Document
    existing_doc = db.query(Document).filter(Document.user_id == student_user_id, Document.filename == "hostel_mess_receipt.pdf").first()
    if not existing_doc:
        doc = Document(
            user_id=student_user_id,
            filename="hostel_mess_receipt.pdf",
            file_path="/storage/documents/hostel_mess_receipt.pdf",
            document_type="bill",
            mime_type="application/pdf",
            raw_text="Campus Living Hostel Mess Advance. Amount: Rs 3,500.00 Due Date: 2026-09-08",
            extracted_facts={"vendor": "Campus Living", "amount": 3500.00, "due_date": "2026-09-08"},
            is_suspicious=False,
            created_at=datetime(2026, 8, 22, 10, 0, 0),
            updated_at=datetime(2026, 8, 22, 10, 0, 0),
        )
        db.add(doc)
    db.flush()
    db.commit()

    return {
        "user_id": student_user_id,
        "authoritative_balance": authoritative_balance,
        "transactions_count": len(tx_entities),
        "goals_count": db.query(Goal).filter(Goal.user_id == student_user_id).count(),
        "bills_count": db.query(Bill).filter(Bill.user_id == student_user_id).count(),
    }


# =============================================================================
# 4. Main Demo Users Seeding Orchestrator
# =============================================================================

def seed_demo_users() -> Dict[str, Any]:
    """
    Executes the idempotent seeding for both hackathon demo accounts:
    1. demo@finsight.com
    2. student@finsight.com
    """
    init_db()
    db: Session = SessionLocal()

    target_db_name = engine.url.database or "finsight.db"
    target_db_abs = Path(target_db_name).resolve() if engine.url.database else Path("finsight.db").resolve()

    print(f"Target Database: {target_db_abs}")

    try:
        # Step 0: Ensure golden reference synthetic user (Aarav Sharma) exists in this database
        ref_user = db.query(User).filter(User.email == AARAV_EMAIL).first()
        if not ref_user:
            print(f"Reference user ({AARAV_EMAIL}) not found in target database. Generating reference synthetic dataset...")
            seed_synthetic_data()
            ref_user = db.query(User).filter(User.email == AARAV_EMAIL).first()
            if not ref_user:
                raise RuntimeError("Failed to initialize reference synthetic user.")

        # ---------------------------------------------------------------------
        # Account 1: demo@finsight.com (FinSight Demo User)
        # ---------------------------------------------------------------------
        demo_user = get_or_create_demo_user(
            db=db,
            email="demo@finsight.com",
            full_name="FinSight Demo User",
            plain_password="Demo@123",
        )
        # Attach the rich 86-transaction dataset from Aarav Sharma
        demo_attach_res = attach_demo_data_to_user(
            db=db,
            target_user_id=demo_user.id,
            source_user_id=ref_user.id,
            source_email=ref_user.email,
        )

        # ---------------------------------------------------------------------
        # Account 2: student@finsight.com (Student Demo)
        # ---------------------------------------------------------------------
        student_user = get_or_create_demo_user(
            db=db,
            email="student@finsight.com",
            full_name="Student Demo",
            plain_password="Student@123",
        )
        # Attach the deterministic student dataset
        student_res = seed_student_demo_dataset(db=db, student_user_id=student_user.id)

        # ---------------------------------------------------------------------
        # Gather Verification Data
        # ---------------------------------------------------------------------
        def get_user_summary(user_obj: User):
            bal_info = get_balance(user_obj.id, db)
            tx_count = db.query(Transaction).filter(Transaction.user_id == user_obj.id).count()
            goal_count = db.query(Goal).filter(Goal.user_id == user_obj.id).count()
            bill_count = db.query(Bill).filter(Bill.user_id == user_obj.id, Bill.status == "unpaid").count()
            return {
                "email": user_obj.email,
                "user_id": user_obj.id,
                "balance": bal_info["balance"],
                "tx_count": tx_count,
                "goal_count": goal_count,
                "upcoming_bill_count": bill_count,
            }

        demo_summary = get_user_summary(demo_user)
        student_summary = get_user_summary(student_user)

        # Print structured verification output (NEVER print passwords or API keys)
        print("\n==================================================")
        print("FinSight Demo Accounts Seeding Report")
        print("==================================================")
        print(f"Target Database: {target_db_abs}")
        print("--------------------------------------------------")
        print("Demo Account:")
        print(f"Email: {demo_summary['email']}")
        print(f"User ID: {demo_summary['user_id']}")
        print(f"Account Balance: ₹{demo_summary['balance']:,.2f}")
        print(f"Transaction Count: {demo_summary['tx_count']}")
        print(f"Goal Count: {demo_summary['goal_count']}")
        print(f"Upcoming Bill Count: {demo_summary['upcoming_bill_count']}")
        print("--------------------------------------------------")
        print("Demo Account:")
        print(f"Email: {student_summary['email']}")
        print(f"User ID: {student_summary['user_id']}")
        print(f"Account Balance: ₹{student_summary['balance']:,.2f}")
        print(f"Transaction Count: {student_summary['tx_count']}")
        print(f"Goal Count: {student_summary['goal_count']}")
        print(f"Upcoming Bill Count: {student_summary['upcoming_bill_count']}")
        print("==================================================\n")

        return {
            "database": str(target_db_abs),
            "demo_user": demo_summary,
            "student_user": student_summary,
        }

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_users()
