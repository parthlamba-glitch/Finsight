"""
FinSight Conversation Manager.
Manages ephemeral multi-turn conversational context across user requests.

ARCHITECTURAL PRINCIPLES:
- Stores ONLY conversational interaction metadata (intents, last questions, pending parameters).
- NEVER calculates financial values or stores authoritative financial state.
"""

from typing import Dict, Any, Optional


class ConversationManager:
    """In-memory conversation session context manager."""

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_context(self, conversation_id: Optional[str]) -> Dict[str, Any]:
        """Retrieves conversational context for a given session ID."""
        if not conversation_id or conversation_id not in self._sessions:
            return {}
        return dict(self._sessions[conversation_id])

    def update_context(self, conversation_id: Optional[str], context_data: Dict[str, Any]) -> None:
        """Updates conversational context for a given session ID."""
        if not conversation_id:
            return
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = {}
        self._sessions[conversation_id].update(context_data)

    def set_context(self, conversation_id: Optional[str], context_data: Dict[str, Any]) -> None:
        """Overwrites conversational context for a given session ID."""
        if not conversation_id:
            return
        self._sessions[conversation_id] = dict(context_data)

    def clear(self, conversation_id: Optional[str] = None) -> None:
        """Clears context for a specific session ID, or all sessions if None."""
        if conversation_id is not None:
            self._sessions.pop(conversation_id, None)
        else:
            self._sessions.clear()


conversation_manager = ConversationManager()
