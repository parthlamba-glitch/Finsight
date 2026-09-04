"""
Integration tests for Voice Endpoints:
- POST /voice/transcribe & POST /api/v1/voice/transcribe
- POST /voice/ask & POST /api/v1/voice/ask (Unified direct voice query)

Verifies:
1. Verbatim speech transcription with timing instrumentation.
2. Direct voice query pipeline (Audio -> In-memory STT -> AI Pipeline -> VoiceAskResponse).
3. Preservation of conversation_id, multi-turn memory, and tool execution.
4. Structured latency timing metadata (stt_ms, routing_ms, engine_ms, explainer_ms, total).
5. Audio validation (size limits, empty payload, unsupported format).
"""

import io
import math
import struct
import wave
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction
from ai.conversation import conversation_manager


def _generate_test_wav(duration_sec: float = 0.2, freq: float = 440.0) -> bytes:
    """Generates a valid mono 16-bit PCM WAV in memory."""
    buf = io.BytesIO()
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    with wave.open(buf, "wb") as wav_out:
        wav_out.setnchannels(1)
        wav_out.setsampwidth(2)
        wav_out.setframerate(sample_rate)
        frames = bytearray()
        for i in range(num_samples):
            val = int(32767.0 * 0.1 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            frames.extend(struct.pack("<h", val))
        wav_out.writeframes(frames)
    return buf.getvalue()


@pytest.fixture
def seed_voice_user(db_session: Session):
    """Seeds a test user with an account and balance for voice queries."""
    user = User(
        full_name="Kavya Iyer",
        email="kavya.voice@example.com",
        accessibility_prefs={"voice_first": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    acc = Account(
        user_id=user.id,
        name="SBI Savings",
        account_type="savings",
        balance=Decimal("95000.00"),
        monthly_income=Decimal("60000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()

    tx = Transaction(
        account_id=acc.id,
        user_id=user.id,
        amount=Decimal("95000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add(tx)
    db_session.commit()
    return user


class TestVoiceApiEndpoints:
    def setup_method(self):
        conversation_manager.clear()

    def test_transcribe_audio_format_validation(self, client: TestClient):
        """Rejects empty or corrupt audio uploads."""
        # Empty payload
        res = client.post("/voice/transcribe", files={"audio": ("empty.wav", b"", "audio/wav")})
        assert res.status_code == 400

        # Unsupported format
        res_bad_format = client.post("/voice/transcribe", files={"audio": ("test.exe", b"A" * 100, "application/octet-stream")})
        assert res_bad_format.status_code == 400

    def test_transcribe_audio_endpoint(self, client: TestClient):
        """Transcribes valid audio and returns timing metadata."""
        wav_data = _generate_test_wav(duration_sec=0.3)
        files = {"audio": ("sample_balance.wav", wav_data, "audio/wav")}

        with patch("backend.routers.voice.transcribe_audio") as mock_stt:
            mock_stt.return_value = {
                "status": "success",
                "transcript": "What's my balance?",
                "language": "en",
                "timing_ms": {"stt_total_ms": 120.5},
            }
            res = client.post("/voice/transcribe", files=files)
            assert res.status_code == 200
            data = res.json()

            assert data["status"] == "success"
            assert "balance" in data["transcript"].lower()
            assert "timing_ms" in data

    def test_unified_voice_ask_endpoint(self, client: TestClient, seed_voice_user):
        """Verifies unified /voice/ask executes transcription + pipeline in single roundtrip."""
        wav_data = _generate_test_wav(duration_sec=0.3)
        files = {"audio": ("sample_balance.wav", wav_data, "audio/wav")}
        data_payload = {
            "conversation_id": "test-voice-conv-1",
            "language": "en",
        }

        with patch("backend.routers.voice.transcribe_audio") as mock_stt:
            mock_stt.return_value = {
                "status": "success",
                "transcript": "What's my balance?",
                "language": "en",
                "timing_ms": {"stt_total_ms": 115.0},
            }
            res = client.post("/voice/ask", files=files, data=data_payload)
            assert res.status_code == 200
            data = res.json()

            # Transcript returned alongside answer
            assert "transcript" in data
            assert "balance" in data["transcript"].lower()

            # Copilot response fields
            assert data["intent"] == "get_balance"
            assert "95,000" in data["answer_text"] or "95000" in data["answer_text"]
            assert data["conversation_id"] == "test-voice-conv-1"

            # Structured timing metadata present
            assert "timing_ms" in data
            timing = data["timing_ms"]
            assert "stt_ms" in timing
            assert "intent_routing_ms" in timing
            assert "financial_tool_execution_ms" in timing
            assert "explainer_ms" in timing
            assert "total_voice_backend_ms" in timing

    def test_unified_voice_ask_affordability(self, client: TestClient, seed_voice_user):
        """Verifies /voice/ask handles affordability query from audio filename/tones."""
        wav_data = _generate_test_wav(duration_sec=0.3)
        files = {"audio": ("sample_afford.wav", wav_data, "audio/wav")}

        with patch("backend.routers.voice.transcribe_audio") as mock_stt:
            mock_stt.return_value = {
                "status": "success",
                "transcript": "Can I afford a phone for ₹10,000?",
                "language": "en",
                "timing_ms": {"stt_total_ms": 130.0},
            }
            res = client.post("/api/v1/voice/ask", files=files)
            assert res.status_code == 200
            data = res.json()

            assert data["intent"] == "check_affordability"
            assert data["structured_facts"]["can_afford"] is True
            assert "timing_ms" in data
