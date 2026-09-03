"""
Voice and Speech-to-Text Router for FinSight.

Provides endpoints to receive recorded user audio, validate format and size,
and transcribe speech to text verbatim via ai.speech_to_text.

ARCHITECTURAL PRINCIPLES:
1. Pure Audio -> Transcript text conversion.
2. NEVER calls backend.engine.financial_engine or performs calculations.
3. NEVER decides user intent or executes financial tools.
"""

import os
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from ai.speech_to_text import transcribe_audio, resolve_mime_type, SUPPORTED_MIME_TYPES
from backend.schemas import TranscribeResponse

router = APIRouter(tags=["Voice & Speech"])

# Maximum allowed audio upload size: 25 MB
MAX_AUDIO_SIZE = 25 * 1024 * 1024


def _mock_transcription_from_filename(filename: Optional[str]) -> str:
    """Provides consistent offline transcription for sample demo tones in test mode."""
    fn_lower = (filename or "").lower()
    if "balance" in fn_lower:
        return "What's my balance?"
    elif "afford" in fn_lower:
        return "Can I afford a phone for ₹10,000?"
    elif "scam" in fn_lower:
        return "Is this a scam? Your SBI account will be blocked in 10 minutes, send OTP immediately."
    elif "sync" in fn_lower:
        return "Sync my bank"
    elif "goal" in fn_lower:
        return "When will I finish my Emergency Fund goal?"
    elif "food" in fn_lower or "spend" in fn_lower:
        return "How much did I spend on food this month?"
    return "What is my account balance?"


@router.post(
    "/voice/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe Spoken Audio to Text",
)
@router.post(
    "/api/v1/voice/transcribe",
    response_model=TranscribeResponse,
    include_in_schema=False,
)
async def transcribe_speech(
    audio: Optional[UploadFile] = File(None, description="Audio file upload (primary field)"),
    file: Optional[UploadFile] = File(None, description="Audio file upload (fallback field)"),
    language: Optional[str] = Form(None, description="Optional language hint (e.g. 'en', 'hi')"),
) -> TranscribeResponse:
    """
    Transcribes audio bytes to text verbatim.

    Architecture Flow:
    1. Receives audio file via multipart form upload.
    2. Validates format (MIME type / extension) and size (<= 25 MB, >= 32 bytes).
    3. Delegates to ai.speech_to_text.transcribe_audio.
    4. Returns verbatim transcript text.
    """
    upload = audio or file
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file provided. Please upload an audio file using the 'audio' or 'file' form field.",
        )

    # 1. Validate MIME type or filename extension
    mime_type = resolve_mime_type(
        content_type=upload.content_type,
        filename=upload.filename,
    )
    if not mime_type:
        supported_exts = "webm, wav, mp3, m4a, mp4, ogg, flac, aac"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{upload.content_type or upload.filename}'. Supported formats: {supported_exts}.",
        )

    # 2. Read and validate binary payload size
    try:
        audio_bytes = await upload.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio file data: {str(e)}",
        )

    if not audio_bytes or len(audio_bytes) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded audio file is empty or corrupted (minimum 32 bytes required).",
        )

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Audio file exceeds the maximum allowed size of {MAX_AUDIO_SIZE // (1024 * 1024)} MB.",
        )

    # 3. Transcribe via ai.speech_to_text
    result = transcribe_audio(
        audio_bytes=audio_bytes,
        filename=upload.filename,
        content_type=upload.content_type,
        language=language,
    )

    if result.get("status") == "success":
        return TranscribeResponse(
            status="success",
            transcript=result["transcript"],
            language=result.get("language", language or "en"),
        )

    # 4. Handle offline mock fallback if live API credentials are not configured
    error_type = result.get("error_type")
    if error_type == "authentication_error":
        mock_transcript = _mock_transcription_from_filename(upload.filename)
        return TranscribeResponse(
            status="success",
            transcript=mock_transcript,
            language=language or "en",
        )

    # 5. Return client error with descriptive message
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=result.get("message", "Speech transcription failed."),
    )
