import sys
import os
import json
from decimal import Decimal
from datetime import datetime

sys.path.insert(0, os.path.abspath(r"c:\Users\Parth\.gemini\antigravity-ide\scratch\finsight"))

from fastapi.testclient import TestClient
from backend.main import app
from backend.db import SessionLocal
from backend.models import User
from backend.engine import get_balance, get_spending_summary

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

client = TestClient(app)

print("=== DAY 4B INGESTION PIPELINE LIVE VERIFICATION ===\n")

db = SessionLocal()
try:
    user = db.query(User).filter_by(email="aarav.sharma@example.com").first()
    assert user is not None, "Demo user not found"
    user_id = user.id

    # Baseline Authoritative Balance
    bal_initial = get_balance(user_id, db)["balance"]
    print(f"0. Initial Authoritative Balance: ₹{bal_initial:,.2f}")

    # 1. Mock Bank Connection
    r_connect = client.post("/bank/connect", json={"user_id": user_id, "institution_name": "HDFC Bank NetBanking"})
    print(f"\n1. Mock Bank Connection (POST /bank/connect):")
    print(f"   Status: {r_connect.status_code}")
    print(f"   Response: {r_connect.json()}")

    # 2. First Bank Sync (Imports 4 transactions: +15,000 Income, -450 Food, -320 Transport, -1299 Shopping = +12,931 net)
    r_sync1 = client.post("/bank/sync", json={"user_id": user_id})
    print(f"\n2. First Bank Sync (POST /bank/sync):")
    data_sync1 = r_sync1.json()
    print(f"   Status: {r_sync1.status_code}")
    print(f"   Imported Count: {data_sync1['imported_count']}")
    print(f"   Duplicate Count: {data_sync1['duplicate_count']}")
    for tx in data_sync1["imported_transactions"]:
        print(f"     * [{tx['source'].upper()}] {tx['transaction_date'][:10]} | {tx['merchant_name']} | ₹{tx['amount']} ({tx['category']}) | Ref: {tx['reference_id']}")

    bal_after_sync1 = get_balance(user_id, db)["balance"]
    print(f"   -> Authoritative Balance After First Sync: ₹{bal_after_sync1:,.2f}")

    # 3. Second Bank Sync (Idempotency: duplicates skipped)
    r_sync2 = client.post("/bank/sync", json={"user_id": user_id})
    data_sync2 = r_sync2.json()
    print(f"\n3. Second Bank Sync (Idempotency Check):")
    print(f"   Status: {r_sync2.status_code}")
    print(f"   Imported Count: {data_sync2['imported_count']} (Expected: 0)")
    print(f"   Duplicate Count: {data_sync2['duplicate_count']} (Expected: 4)")
    for sk in data_sync2["skipped_transactions"]:
        print(f"     * Skipped: {sk['merchant_name']} | ₹{sk['amount']} | Reason: {sk['reason']}")

    # 4. Voice Transaction Ingestion (POST /transactions/voice: -₹250.00 Food at Chai Point)
    voice_payload = {
        "user_id": user_id,
        "amount": 250.00,
        "transaction_type": "expense",
        "category": "Food",
        "merchant_name": "Chai Point Indiranagar",
        "description": "Voice captured: 2 masala chai and samosa",
        "transaction_date": "2026-08-27T17:30:00",
    }
    r_voice = client.post("/transactions/voice", json=voice_payload)
    print(f"\n4. Voice Transaction Ingestion (POST /transactions/voice):")
    print(f"   Status: {r_voice.status_code}")
    voice_data = r_voice.json()
    print(f"   Created Transaction: ID {voice_data['id']} | Amount: ₹{voice_data['amount']} | Category: {voice_data['category']} | Source: {voice_data['source']}")

    # 5. Statement Ingestion & Confirmation
    # Step 5a: Upload / Stage Statement Candidates
    statement_upload_payload = {
        "user_id": user_id,
        "filename": "hdfc_credit_card_august.pdf",
        "extracted_candidates": [
            {
                "reference_id": "STMT-CC-202608-01",
                "amount": 850.00,
                "transaction_type": "expense",
                "category": "Food",
                "merchant_name": "FreshMenu Bangalore",
                "description": "Lunch Meal Box",
                "transaction_date": "2026-08-27T13:00:00",
            },
            {
                "reference_id": "STMT-CC-202608-02",
                "amount": 1450.00,
                "transaction_type": "expense",
                "category": "Healthcare",
                "merchant_name": "Apollo Pharmacy",
                "description": "Prescription Medicines",
                "transaction_date": "2026-08-27T16:00:00",
            }
        ]
    }
    r_stmt_upload = client.post("/statements/upload", json=statement_upload_payload)
    print(f"\n5a. Statement Ingestion (POST /statements/upload - Staging Boundary):")
    print(f"   Status: {r_stmt_upload.status_code}")
    stmt_data = r_stmt_upload.json()
    print(f"   Document ID: {stmt_data['document_id']} | Total Candidates: {stmt_data['total_candidates']} | Valid: {stmt_data['valid_candidates_count']}")
    for cand in stmt_data["candidates"]:
        print(f"     * Candidate: {cand['merchant_name']} | ₹{cand['amount']} | Is Duplicate: {cand['is_duplicate']}")

    # Step 5b: Confirm Candidates into Ledger
    confirm_payload = {
        "user_id": user_id,
        "document_id": stmt_data["document_id"],
        "candidates": statement_upload_payload["extracted_candidates"]
    }
    r_confirm = client.post("/transactions/confirm", json=confirm_payload)
    print(f"\n5b. Statement Confirmation (POST /transactions/confirm - Persistence):")
    print(f"   Status: {r_confirm.status_code}")
    confirm_data = r_confirm.json()
    print(f"   Confirmed Count: {confirm_data['confirmed_count']}")
    for tx in confirm_data["transactions"]:
        print(f"     * Persisted: ID {tx['id']} | Amount: ₹{tx['amount']} | Source: {tx['source']} | Ref: {tx['reference_id']}")

    # 6. Final Authoritative Balance & Financial Engine Consumption
    final_balance = get_balance(user_id, db)["balance"]
    spending_summary = get_spending_summary(user_id, db, period="this_month")

    print(f"\n6. Financial Engine Final State:")
    print(f"   - Initial Balance: ₹{bal_initial:,.2f}")
    # Net change: +15,000 - 450 - 320 - 1,299 - 250 - 850 - 1,450 = +10,381.00
    print(f"   - Final Authoritative Balance: ₹{final_balance:,.2f} (Net change: +₹{final_balance - bal_initial:,.2f})")
    print(f"   - August 2026 Total Spending: ₹{spending_summary['total']:,.2f}")
    print(f"   - August 2026 Food Spending: ₹{spending_summary['by_category']['Food']:,.2f}")

finally:
    db.close()
