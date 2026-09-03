"""
FinSight Speech-to-Text (STT) Module
====================================

Architectural Boundary & Invariants:
------------------------------------
1. The STT system has exactly ONE responsibility: AUDIO -> TRANSCRIPT TEXT.
2. It NEVER imports or calls backend.engine.financial_engine.
3. It NEVER performs financial calculations, tool selection, or affordability decisions.
4. It NEVER calls the existing /ask pipeline automatically.
5. It preserves original user phrasing verbatim (including Hindi and Hinglish)
   without translating to English.
"""

import base64
import os
import re
from typing import Any, Dict, Optional
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import httpx

load_dotenv()

# Supported MIME types and file extension mappings
SUPPORTED_MIME_TYPES = {
    "audio/webm": "audio/webm",
    "audio/wav": "audio/wav",
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/mp3": "audio/mp3",
    "audio/mpeg": "audio/mp3",
    "audio/mp4": "audio/mp4",
    "audio/m4a": "audio/mp4",
    "audio/x-m4a": "audio/mp4",
    "audio/ogg": "audio/ogg",
    "audio/opus": "audio/ogg",
    "audio/flac": "audio/flac",
    "audio/x-flac": "audio/flac",
    "audio/aac": "audio/aac",
}

EXTENSION_TO_MIME = {
    ".webm": "audio/webm",
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
}

STT_SYSTEM_PROMPT = """You are FinSight's verbatim speech transcription engine.
Transcribe exactly what the speaker says in this audio.

CRITICAL INSTRUCTIONS:
1. Transcribe verbatim. Do not summarize, rephrase, expand, or add commentary.
2. Do NOT translate into English. Keep the exact words in the language spoken.
3. If spoken in Hindi, Hinglish, Indian English, or code-mixed language (e.g. "Bhai mere account mein kitne paise hain?" or "Can I buy headphones for 8k?"), transcribe it exactly in that language and phrasing.
4. Do not add markdown labels, bullet points, introductory phrases (such as "Here is the transcription:"), or quotes.
5. If the audio contains only silence, ambient noise, non-speech sounds, or no intelligible human speech, output exactly: [NO_SPEECH]
6. Never fabricate or invent speech that is not present in the audio.
"""

NO_SPEECH_TOKENS = {
    "[no_speech]",
    "<no_speech>",
    "no_speech",
    "<noise>",
    "[noise]",
    "noise",
    "[silence]",
    "<silence>",
    "silence",
}


def resolve_mime_type(
    content_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> Optional[str]:
    """
    Safely resolves and normalizes audio MIME type from content_type header or filename extension.
    """
    if content_type:
        raw_mime = content_type.split(";")[0].strip().lower()
        if raw_mime in SUPPORTED_MIME_TYPES:
            return SUPPORTED_MIME_TYPES[raw_mime]

    if filename:
        ext = os.path.splitext(filename.lower())[1]
        if ext in EXTENSION_TO_MIME:
            return EXTENSION_TO_MIME[ext]

    return None


def get_stt_config() -> Dict[str, str]:
    """
    Retrieves speech transcription configuration from environment variables.
    Never exposes credentials in logs.
    """
    api_key = (
        os.getenv("LLM_API_KEY")
        or os.getenv("STT_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    )
    # Default model precedence: STT_MODEL -> LLM_MODEL -> 'gemini-3.5-flash-lite'
    model = os.getenv("STT_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.5-flash-lite"
    base_url = (
        os.getenv("GEMINI_API_BASE_URL")
        or "https://generativelanguage.googleapis.com/v1beta"
    )
    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url.rstrip("/"),
    }


def transcribe_audio(
    audio_bytes: bytes,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    language: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribes audio bytes to text using Google Gemini native Generative AI REST API.

    Parameters:
    -----------
    audio_bytes : bytes
        Raw binary audio content.
    filename : Optional[str]
        Original filename for extension-based format deduction.
    content_type : Optional[str]
        MIME type provided by client header.
    language : Optional[str]
        Optional language hint (e.g. 'en', 'hi', 'hi-IN').
    model : Optional[str]
        Model override (defaults to environment STT_MODEL or LLM_MODEL).
    api_key : Optional[str]
        API key override (defaults to environment credentials).
    base_url : Optional[str]
        Base URL override.

    Returns:
    --------
    Dict[str, Any]:
        Success: {"status": "success", "transcript": str, "language": Optional[str]}
        Error:   {"status": "error", "error_type": str, "message": str}
    """
    # 1. Validate audio bytes presence and length
    if not audio_bytes or len(audio_bytes) == 0:
        return {
            "status": "error",
            "error_type": "empty_audio",
            "message": "The uploaded audio file is empty. Please try speaking again.",
        }

    # Files smaller than 32 bytes cannot contain valid audio headers
    if len(audio_bytes) < 32:
        return {
            "status": "error",
            "error_type": "corrupt_audio",
            "message": "The audio file is too short or corrupted. Please record again.",
        }

    # 2. Resolve audio MIME type
    mime_type = resolve_mime_type(content_type=content_type, filename=filename)
    if not mime_type:
        raw_type = content_type or (filename and os.path.splitext(filename)[1]) or "unknown"
        return {
            "status": "error",
            "error_type": "unsupported_media_type",
            "message": (
                f"Unsupported audio format '{raw_type}'. "
                "Supported formats are: webm, wav, mp3, m4a, ogg, flac, aac."
            ),
        }

    # 3. Resolve API configuration
    cfg = get_stt_config()
    active_api_key = api_key or cfg["api_key"]
    active_model = model or cfg["model"]
    active_base_url = base_url or cfg["base_url"]

    if not active_api_key or active_api_key == "dummy_key_for_mocking":
        return {
            "status": "error",
            "error_type": "authentication_error",
            "message": "Speech transcription service API key is not configured.",
        }

    # Clean model identifier
    clean_model = active_model.replace("models/", "")

    # 4. Construct Gemini REST payload with inline base64 audio
    try:
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        return {
            "status": "error",
            "error_type": "corrupt_audio",
            "message": f"Failed to encode audio data: {str(e)}",
        }

    prompt_text = STT_SYSTEM_PROMPT
    if language:
        prompt_text += f"\nLanguage hint from user: {language}."

    endpoint_url = (
        f"{active_base_url}/models/{clean_model}:generateContent?key={active_api_key}"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_audio,
                        }
                    },
                    {"text": prompt_text},
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
        },
    }

    # 5. Execute HTTP request with robust error handling
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint_url, json=payload)

        # Handle HTTP status codes
        if response.status_code == 200:
            return _parse_gemini_response(response.json(), requested_language=language)

        if response.status_code in (401, 403):
            return {
                "status": "error",
                "error_type": "authentication_error",
                "message": (
                    "Speech transcription authentication failed. Please verify API key permissions."
                ),
            }

        if response.status_code == 429:
            return {
                "status": "error",
                "error_type": "rate_limit",
                "message": (
                    "Speech transcription service rate limit exceeded. Please wait a moment and try again."
                ),
            }

        if response.status_code == 503:
            return {
                "status": "error",
                "error_type": "service_unavailable",
                "message": (
                    "Speech transcription service is currently experiencing high demand. Please try again shortly."
                ),
            }

        if response.status_code == 404:
            return {
                "status": "error",
                "error_type": "model_not_found",
                "message": f"Configured STT model '{clean_model}' was not found.",
            }

        # Other 4xx / 5xx provider responses
        try:
            err_json = response.json()
            err_msg = err_json.get("error", {}).get("message", response.text[:200])
        except Exception:
            err_msg = response.text[:200]

        return {
            "status": "error",
            "error_type": "provider_error",
            "message": f"Transcription provider returned an error: {err_msg}",
        }

    except httpx.TimeoutException:
        return {
            "status": "error",
            "error_type": "timeout",
            "message": "Speech transcription request timed out. Please try speaking again.",
        }
    except (httpx.ConnectError, httpx.NetworkError) as e:
        return {
            "status": "error",
            "error_type": "network_error",
            "message": f"Network error connecting to speech transcription provider: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "unexpected_error",
            "message": f"Unexpected error during audio transcription: {str(e)}",
        }


def _parse_gemini_response(
    resp_json: Dict[str, Any],
    requested_language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parses and sanitizes the Gemini generateContent response.
    Never fabricates a transcript.
    """
    candidates = resp_json.get("candidates")
    if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
        # Prompt feedback or safety blocks may leave candidates empty
        return {
            "status": "error",
            "error_type": "unintelligible_speech",
            "message": "I couldn't detect any clear speech in the audio. Please try speaking again.",
        }

    first_candidate = candidates[0]
    content = first_candidate.get("content", {})
    parts = content.get("parts", [])

    if not parts or not isinstance(parts, list) or len(parts) == 0:
        return {
            "status": "error",
            "error_type": "unintelligible_speech",
            "message": "I couldn't detect any clear speech in the audio. Please try speaking again.",
        }

    raw_text = parts[0].get("text", "")
    if not raw_text or not isinstance(raw_text, str):
        return {
            "status": "error",
            "error_type": "unintelligible_speech",
            "message": "I couldn't detect any clear speech in the audio. Please try speaking again.",
        }

    cleaned = raw_text.strip()

    # Check for empty output or silence/noise indicator tokens
    if not cleaned or cleaned.lower() in NO_SPEECH_TOKENS:
        return {
            "status": "error",
            "error_type": "unintelligible_speech",
            "message": "I couldn't detect any clear speech in the audio. Please try speaking again.",
        }

    # Strip surrounding quotes if the model wrapped the verbatim output in quotes
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        cleaned = cleaned[1:-1].strip()

    if not cleaned or cleaned.lower() in NO_SPEECH_TOKENS:
        return {
            "status": "error",
            "error_type": "unintelligible_speech",
            "message": "I couldn't detect any clear speech in the audio. Please try speaking again.",
        }

    return {
        "status": "success",
        "transcript": cleaned,
        "language": requested_language or "en",
    }
