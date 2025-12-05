"""
State definition for the travel itinerary planner.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add
from dataclasses import dataclass, asdict, field


@dataclass
class TravelPreferences:
    """User travel preferences."""
    destination: Optional[str] = None
    duration_days: Optional[int] = None
    budget: Optional[float] = None
    season: Optional[str] = None
    num_people: Optional[int] = 1
    travel_dates: Optional[str] = None
    interests: Optional[List[str]] = None
    accommodation_type: Optional[str] = None
    travel_style: Optional[str] = None
    
    def to_dict(self):
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class BudgetAllocation:
    """Budget allocation breakdown."""
    total_budget: float
    daily_budget: float
    accommodation_budget: float
    food_budget: float
    activities_budget: float
    transport_budget: float
    contingency: float
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LocationData:
    """Location research data."""
    name: str
    avg_daily_cost: float
    best_season: Optional[str] = None
    season_notes: Optional[str] = None
    description: Optional[str] = None
    highlights: Optional[List[str]] = field(default_factory=list)
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)


class AgentState(TypedDict):
    """
    State for the travel planning agent.
    
    Attributes:
        user_request: Original travel request from user
        preferences: Extracted travel preferences
        missing_info: List of missing required information
        current_question: Current question to ask user
        plan: List of planned steps/tasks to execute
        current_step: Current step number being executed
        completed_steps: List of completed steps with results
        research_data: Research results for destinations
        needs_destination_research: Whether we need to research destinations
        needs_destination_selection: Whether user needs to select destination
        budget_allocation: Budget breakdown
        filtered_locations: Locations matching budget
        selected_location: Selected destination
        season_recommendations: Season-specific recommendations
        daily_plans: Day-by-day itinerary
        itinerary: Final complete itinerary
        errors: List of errors encountered
        retry_count: Number of retries for current step
        messages: Conversation history
        needs_replanning: Whether replanning is needed
        status: Current status of planning
        is_general_chat: Whether this is general chat vs travel planning
    """
    user_request: str
    preferences: Optional[TravelPreferences]
    missing_info: List[str]
    current_question: Optional[str]
    plan: List[Dict[str, Any]]
    current_step: int
    completed_steps: Annotated[List[Dict[str, Any]], add]
    research_data: List[LocationData]
    needs_destination_research: bool
    needs_destination_selection: bool
    budget_allocation: Optional[BudgetAllocation]
    filtered_locations: List[LocationData]
    selected_location: Optional[LocationData]
    season_recommendations: Optional[str]
    daily_plans: List[Dict[str, Any]]
    itinerary: Optional[Dict[str, Any]]
    errors: Annotated[List[str], add]
    retry_count: int
    messages: Annotated[List[Dict[str, str]], add]
    needs_replanning: bool
    status: str
    is_general_chat: bool


def create_initial_state(
    user_request: str,
    user_preferences: Optional[Dict[str, Any]] = None
) -> AgentState:
    """
    Create initial state for the agent.
    
    Args:
        user_request: The travel request from user
        user_preferences: Optional existing user preferences
        
    Returns:
        Initial AgentState
    """
    # Convert dict preferences to TravelPreferences if provided
    prefs = None
    if user_preferences:
        prefs = TravelPreferences(**user_preferences)
    
    return AgentState(
        user_request=user_request,
        preferences=prefs,
        missing_info=[],
        current_question=None,
        plan=[],
        current_step=0,
        completed_steps=[],
        research_data=[],
        needs_destination_research=False,
        needs_destination_selection=False,
        budget_allocation=None,
        filtered_locations=[],
        selected_location=None,
        season_recommendations=None,
        daily_plans=[],
        itinerary=None,
        errors=[],
        retry_count=0,
        messages=[{"role": "user", "content": user_request}],
        needs_replanning=False,
        status="analyzing",
        is_general_chat=False
    )