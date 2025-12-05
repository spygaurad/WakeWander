from sqlalchemy import Column, String, DateTime, JSON, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(JSON)
    messages = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Itinerary(Base):
    __tablename__ = "itineraries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True))
    
    destination = Column(String(255), nullable=False)
    duration_days = Column(Integer, nullable=False)
    budget = Column(Integer, nullable=False)
    season = Column(String(50))  # winter, spring, summer, fall
    travel_dates = Column(String(100))
    
    # Complete itinerary data
    plan = Column(JSON)
    budget_allocation = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
