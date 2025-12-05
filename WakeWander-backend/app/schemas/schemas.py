"""
Pydantic schemas for API requests and responses.
"""
from pydantic import BaseModel
from typing import Optional, Any


class ChatMessage(BaseModel):
    """Chat message from user."""
    message: str
    conversation_id: Optional[str] = None


class ResumeRequest(BaseModel):
    """Request to resume an interrupted conversation."""
    conversation_id: str
    value: Any  # The user's answer to the interrupt (question answer or selection index)


class ConversationCreate(BaseModel):
    """Create a new conversation."""
    initial_message: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    messages: list
    state: dict
    created_at: str


class ItineraryResponse(BaseModel):
    """Itinerary response."""
    id: str
    destination: str
    duration_days: int
    budget: float
    season: Optional[str]
    travel_dates: Optional[str]
    plan: dict
    budget_allocation: Optional[dict]
    created_at: str