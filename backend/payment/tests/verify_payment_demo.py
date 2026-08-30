import sys
import os
import json
from decimal import Decimal

sys.path.insert(0, os.path.abspath(r"c:\Users\Parth\.gemini\antigravity-ide\scratch\finsight"))

from backend.db import SessionLocal
from backend.models import User
from backend.payment.payment_engine import preview_payment, execute_payment

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

db = SessionLocal()
try:
    user = db.query(User).filter_by(email="aarav.sharma@example.com").first()
    assert user is not None, "Demo user not found"

    print("=== 1. PAYMENT PREVIEW EXAMPLE ===")
    preview = preview_payment(
        user_id=user.id,
        amount=Decimal("5000.00"),
        recipient_name="Dr. Rao Clinic",
        db=db,
    )
    print("Preview Result:")
    for k, v in preview.items():
        if k != "reasoning_facts":
            print(f"  {k}: {v}")
    print("  reasoning_facts:")
    for f in preview["reasoning_facts"]:
        print(f"    * {f}")

    print("\n=== 2. PAYMENT EXECUTION EXAMPLE ===")
    payment_result = execute_payment(
        user_id=user.id,
        amount=Decimal("5000.00"),
        recipient_name="Dr. Rao Clinic",
        db=db,
    )
    print("Payment Execution Result:")
    for k, v in payment_result.items():
        print(f"  {k}: {v}")

finally:
    db.close()
