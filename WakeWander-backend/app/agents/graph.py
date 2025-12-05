"""
Graph construction for the travel planner.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState, create_initial_state
from app.agents.node_utilities import (
    create_general_handler,
    create_analyze_input,
    create_identify_missing,
    create_ask_question,
    create_research,
    create_analyze,
    create_season_recommendations,
    create_plan_days,
    create_finalize
)


def initialize_state(
    user_request: str,
    user_preferences: Dict[str, Any] = None,
) -> AgentState:
    """
    Initialize the agent state.
    
    Args:
        user_request: The travel request from user
        user_preferences: Optional existing user preferences
        
    Returns:
        Initial AgentState
    """
    return create_initial_state(user_request, user_preferences)


def create_travel_planner_graph(
    google_api_key: str = None,
    temperature: float = 0.7,
    checkpointer = None
) -> StateGraph:
    """
    Create the travel planner graph with streaming support.
    
    Args:
        google_api_key: Google API key (if None, will try to get from environment)
        temperature: LLM temperature setting
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
    """
    # Initialize LLM
    if google_api_key is None:
        google_api_key = os.getenv("GOOGLE_API_KEY")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        temperature=temperature,
        google_api_key=google_api_key,
        convert_system_message_to_human=True
    )
    
    # Create node functions
    general_handler = create_general_handler(llm)
    analyze_input = create_analyze_input(llm)
    identify_missing = create_identify_missing(llm)
    ask_question = create_ask_question(llm)
    research = create_research(llm)
    analyze = create_analyze(llm)
    season_recs = create_season_recommendations(llm)
    plan_days = create_plan_days(llm)
    finalize = create_finalize(llm)
    
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("general_handler", general_handler)
    workflow.add_node("analyze_input", analyze_input)
    workflow.add_node("identify_missing", identify_missing)
    workflow.add_node("ask_question", ask_question)
    workflow.add_node("research", research)
    workflow.add_node("analyze", analyze)
    workflow.add_node("season_recs", season_recs)
    workflow.add_node("plan_days", plan_days)
    workflow.add_node("finalize", finalize)
    
    # Define routing logic
    def route_after_general_handler(state: AgentState) -> str:
        """Route after general handler."""
        if state.get('is_general_chat'):
            return END
        return "analyze_input"
    
    def route_after_analyze_input(state: AgentState) -> str:
        """Route after analyzing input."""
        if state['status'] == 'failed':
            return END
        return "identify_missing"
    
    def route_after_identify_missing(state: AgentState) -> str:
        """Route after identifying missing info."""
        missing = state.get('missing_info', [])
        status = state.get('status', '')
        
        # If we have missing info, ask questions
        if missing:
            return "ask_question"
        
        # If status is researching, do research
        if status == 'researching':
            return "research"
        
        return END
    
    def route_after_ask_question(state: AgentState) -> str:
        """Route after asking question."""
        # After user answers, go back to identify_missing to check what's still needed
        return "identify_missing"
    
    def route_after_research(state: AgentState) -> str:
        """Route after research."""
        if state['status'] == 'failed':
            return END
        
        # After research, analyze budget and select location
        return "analyze"
    
    def route_after_analyze(state: AgentState) -> str:
        """Route after analysis and location selection."""
        if state['status'] == 'failed':
            return END
        
        # After selecting location, get season recommendations
        return "season_recs"
    
    def route_after_season_recs(state: AgentState) -> str:
        """Route after season recommendations."""
        return "plan_days"
    
    def route_after_plan_days(state: AgentState) -> str:
        """Route after planning days."""
        if state['status'] == 'failed':
            return END
        return "finalize"
    
    def route_after_finalize(state: AgentState) -> str:
        """Route after finalization."""
        return END
    
    # Set entry point
    workflow.set_entry_point("general_handler")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "general_handler",
        route_after_general_handler,
        {
            "analyze_input": "analyze_input",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "analyze_input",
        route_after_analyze_input,
        {
            "identify_missing": "identify_missing",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "identify_missing",
        route_after_identify_missing,
        {
            "ask_question": "ask_question",
            "research": "research",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "ask_question",
        route_after_ask_question,
        {
            "identify_missing": "identify_missing"
        }
    )
    
    workflow.add_conditional_edges(
        "research",
        route_after_research,
        {
            "analyze": "analyze",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "analyze",
        route_after_analyze,
        {
            "season_recs": "season_recs",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "season_recs",
        route_after_season_recs,
        {
            "plan_days": "plan_days"
        }
    )
    
    workflow.add_conditional_edges(
        "plan_days",
        route_after_plan_days,
        {
            "finalize": "finalize",
            END: END
        }
    )
    
    workflow.add_conditional_edges(
        "finalize",
        route_after_finalize,
        {
            END: END
        }
    )
    
    # Compile graph with interrupts before ask_question and analyze nodes
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["ask_question", "analyze"]
    )