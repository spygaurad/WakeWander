from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from app.core.database import get_db
from app.schemas.schemas import ChatMessage, ResumeRequest
from app.agents.graph import create_travel_planner_graph, initialize_state
from app.models.models import Conversation, Itinerary
import json
import asyncio
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from typing import Any, Optional

router = APIRouter()

# Create global memory checkpointer and graph
memory_checkpointer = MemorySaver()
travel_graph = create_travel_planner_graph(checkpointer=memory_checkpointer)


async def stream_planning_execution(
    message: str, 
    conversation_id: str, 
    db: Session,
    resume_value: Optional[Any] = None
):
    """Stream detailed planning steps with human-in-the-loop support."""
    
    config = {
        "configurable": {
            "thread_id": conversation_id
        }
    }
    
    # Get or create conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            messages=[],
            state={}
        )
        db.add(conversation)
        db.commit()
    
    try:
        # Determine if we're resuming or starting new
        if resume_value is not None:
            # RESUME from interrupt
            print(f"\n RESUMING with value: {resume_value}")
            
            yield {
                "event": "resume",
                "data": json.dumps({
                    "type": "system",
                    "content": "Processing your response...",
                    "conversation_id": conversation_id
                })
            }
            await asyncio.sleep(0.1)
            
            # Resume execution with user's answer
            input_data = Command(resume=resume_value)
            
        else:
            # START new conversation or continue existing
            print(f"\n STARTING with message: {message}")
            
            # Get existing state from checkpointer
            try:
                state_snapshot = travel_graph.get_state(config)
                if state_snapshot and state_snapshot.values:
                    # We have existing state, this is a continuation
                    print(" Found existing state, continuing conversation")
                    existing_state = state_snapshot.values
                    
                    # Update with new user request
                    existing_state['user_request'] = message
                    input_data = existing_state
                else:
                    # No existing state - create new
                    print(" Creating new initial state")
                    existing_prefs = conversation.state.get("preferences", {})
                    state = initialize_state(message, existing_prefs)
                    input_data = state
            except Exception as e:
                print(f" Could not retrieve state: {e}, creating new")
                existing_prefs = conversation.state.get("preferences", {})
                state = initialize_state(message, existing_prefs)
                input_data = state
            
            yield {
                "event": "start",
                "data": json.dumps({
                    "type": "system",
                    "content": "Starting travel planning...",
                    "conversation_id": conversation_id
                })
            }
            await asyncio.sleep(0.1)
        
        # Stream graph execution
        for step_output in travel_graph.stream(input_data, config, stream_mode="updates"):
            
            if not step_output:
                continue
            
            node_name = list(step_output.keys())[0]
            node_state = step_output[node_name]
            
            print(f"\n Executed Node: {node_name}")
            
            # Handle interrupt nodes, return tuples
            if node_name == "__interrupt__":
                print("   Interrupt detected, checking state...")
                continue
            
            # Only access .get() if it's a dict
            if isinstance(node_state, dict):
                print(f"   Status: {node_state.get('status', 'N/A')}")
            else:
                print(f"   State type: {type(node_state)}")
            
            # Handle each node's output
            if node_name == "general_handler":
                if node_state.get('is_general_chat'):
                    # General chat response - return and end
                    messages = node_state.get('messages', [])
                    if messages:
                        content = messages[-1].get('content', '')
                        print(f" Sending general chat message: {content}")
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "message",
                                "content": content,
                                "conversation_id": conversation_id
                            })
                        }
                        await asyncio.sleep(0.1)
                    yield {
                        "event": "end",
                        "data": json.dumps({"type": "complete"})
                    }
                    return
            
            elif node_name == "analyze_input":
                prefs = node_state.get("preferences")
                if prefs:
                    prefs_dict = prefs.to_dict() if hasattr(prefs, 'to_dict') else prefs
                    
                    yield {
                        "event": "step",
                        "data": json.dumps({
                            "type": "step",
                            "step": "Analyzing Request",
                            "content": f"Extracted preferences: {prefs_dict.get('destination', 'TBD')}, {prefs_dict.get('duration_days', 'TBD')} days, ${prefs_dict.get('budget', 'TBD')}",
                            "data": prefs_dict
                        })
                    }
                    await asyncio.sleep(0.3)
            
            elif node_name == "identify_missing":
                missing = node_state.get("missing_info", [])
                if missing:
                    yield {
                        "event": "step",
                        "data": json.dumps({
                            "type": "step",
                            "step": "Checking Requirements",
                            "content": f"Need information: {', '.join(missing)}",
                            "data": {"missing": missing}
                        })
                    }
                else:
                    yield {
                        "event": "step",
                        "data": json.dumps({
                            "type": "step",
                            "step": "Requirements Complete",
                            "content": "All basic information gathered!",
                            "data": {"ready": True}
                        })
                    }
                await asyncio.sleep(0.3)
            
            elif node_name == "research":
                locations = node_state.get("research_data", [])
                needs_selection = node_state.get("needs_destination_selection", False)
                
                yield {
                    "event": "research",
                    "data": json.dumps({
                        "type": "research",
                        "step": "Researching Destinations",
                        "content": f"Found {len(locations)} great destinations for your trip",
                        "data": {
                            "total_found": len(locations),
                            "needs_selection": needs_selection
                        }
                    })
                }
                await asyncio.sleep(0.5)
            
            elif node_name == "season_recs":
                recommendations = node_state.get("season_recommendations")
                if recommendations:
                    yield {
                        "event": "season",
                        "data": json.dumps({
                            "type": "season",
                            "step": "Season Recommendations",
                            "content": recommendations,
                            "data": {"recommendations": recommendations}
                        })
                    }
                    await asyncio.sleep(0.5)
            
            elif node_name == "plan_days":
                daily_plans = node_state.get("daily_plans", [])
                if daily_plans:
                    yield {
                        "event": "planning",
                        "data": json.dumps({
                            "type": "planning",
                            "step": "Creating Itinerary",
                            "content": f"Planned {len(daily_plans)} days of activities",
                            "data": {"days": len(daily_plans)}
                        })
                    }
                    await asyncio.sleep(0.5)
            
            elif node_name == "finalize":
                itinerary = node_state.get("itinerary")
                if itinerary:
                    # Save to database
                    saved_itinerary = Itinerary(
                        conversation_id=uuid.UUID(conversation_id),
                        destination=itinerary["destination"],
                        duration_days=itinerary["duration_days"],
                        budget=itinerary["total_budget"],
                        season=itinerary.get("season"),
                        travel_dates=itinerary.get("travel_dates"),
                        plan=itinerary,
                        budget_allocation=itinerary.get("budget_allocation")
                    )
                    db.add(saved_itinerary)
                    db.commit()
                    
                    yield {
                        "event": "result",
                        "data": json.dumps({
                            "type": "result",
                            "step": "Complete",
                            "content": f"Your {itinerary['duration_days']}-day itinerary to {itinerary['destination']} is ready!",
                            "itinerary": itinerary,
                            "itinerary_id": str(saved_itinerary.id)
                        })
                    }
        
        # Check if we've hit an interrupt
        final_state = travel_graph.get_state(config)
        
        print(f"\n Final state check:")
        print(f"   Next nodes: {final_state.next}")
        print(f"   Status: {final_state.values.get('status', 'N/A')}")
        
        if final_state.next:
            # We're at an interrupt point
            next_node = final_state.next[0]
            current_state = final_state.values
            
            if next_node == "ask_question":
                # Question interrupt
                missing_info = current_state.get("missing_info", [])
                
                if missing_info:
                    field = missing_info[0]
                    questions = {
                        "season": "Which season are you planning to travel? (spring/summer/fall/winter)",
                        "duration_days": "How many days do you want to travel for?",
                        "budget": "What's your total budget for this trip in USD?",
                        "num_people": "How many people are traveling?",
                        "destination": "Where would you like to travel to?",
                        "travel_dates": "Do you have specific travel dates in mind?"
                    }
                    
                    yield {
                        "event": "interrupt",
                        "data": json.dumps({
                            "type": "interrupt",
                            "interrupt_type": "question",
                            "question": questions.get(field, f"Could you provide {field}?"),
                            "field": field,
                            "missing_info": missing_info,
                            "conversation_id": conversation_id
                        })
                    }
                    
                    # Save state
                    if current_state.get("preferences"):
                        prefs = current_state["preferences"]
                        conversation.state = {
                            "preferences": prefs.to_dict() if hasattr(prefs, "to_dict") else prefs
                        }
                        db.commit()
                    
                    return
            
            elif next_node == "analyze":
                # Destination selection interrupt
                research_data = current_state.get("research_data", [])
                needs_dest = current_state.get("needs_destination_selection", False)
                budget_alloc = current_state.get("budget_allocation")
                
                if needs_dest or (not current_state.get("selected_location") and research_data):
                    # Prepare options
                    prefs = current_state.get("preferences")
                    num_people = prefs.num_people if prefs else 1
                    daily_budget = (prefs.budget / prefs.duration_days / num_people) if prefs else 0
                    
                    # Filter by budget if we have allocation
                    if budget_alloc:
                        per_person_daily = budget_alloc.daily_budget / num_people
                        filtered = [loc for loc in research_data if loc.avg_daily_cost <= per_person_daily * 1.15]
                    else:
                        filtered = research_data
                    
                    if not filtered:
                        filtered = sorted(research_data, key=lambda x: x.avg_daily_cost)[:7]
                    
                    destination_options = [
                        {
                            "index": i,
                            "name": loc.name,
                            "avg_daily_cost": loc.avg_daily_cost,
                            "best_season": loc.best_season,
                            "season_notes": loc.season_notes,
                            "description": loc.description,
                            "highlights": loc.highlights if hasattr(loc, 'highlights') else []
                        }
                        for i, loc in enumerate(filtered[:7])
                    ]
                    
                    yield {
                        "event": "interrupt",
                        "data": json.dumps({
                            "type": "interrupt",
                            "interrupt_type": "destination_selection",
                            "question": f"I found {len(destination_options)} great destinations within your ${daily_budget:.2f}/person/day budget. Which would you like to visit?",
                            "options": destination_options,
                            "field": "destination",
                            "conversation_id": conversation_id
                        })
                    }
                    
                    # Save state
                    if current_state.get("preferences"):
                        prefs = current_state["preferences"]
                        conversation.state = {
                            "preferences": prefs.to_dict() if hasattr(prefs, "to_dict") else prefs
                        }
                        db.commit()
                    
                    return
        
        # If we reach here, execution is complete
        yield {
            "event": "end",
            "data": json.dumps({"type": "complete"})
        }
        
    except Exception as e:
        import traceback
        print(f" Error in stream: {str(e)}")
        print(traceback.format_exc())
        
        yield {
            "event": "error",
            "data": json.dumps({
                "type": "error",
                "content": f"Error: {str(e)}"
            })
        }


@router.post("/chat/stream")
async def chat_stream(
    chat_message: ChatMessage,
    db: Session = Depends(get_db)
):
    """Stream chat responses with interrupt support."""
    conversation_id = chat_message.conversation_id or str(uuid.uuid4())
    
    return EventSourceResponse(
        stream_planning_execution(
            chat_message.message,
            conversation_id,
            db
        )
    )


@router.post("/chat/resume")
async def chat_resume(
    resume_request: ResumeRequest,
    db: Session = Depends(get_db)
):
    """Resume interrupted conversation with user input."""
    return EventSourceResponse(
        stream_planning_execution(
            "",  # No new message needed when resuming
            resume_request.conversation_id,
            db,
            resume_value=resume_request.value
        )
    )


@router.post("/conversation/new")
async def create_new_conversation(db: Session = Depends(get_db)):
    """Create a new conversation."""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        messages=[],
        state={}
    )
    db.add(conversation)
    db.commit()
    return {"conversation_id": str(conversation.id)}


@router.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Get conversation details."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {
        "id": str(conversation.id),
        "messages": conversation.messages,
        "state": conversation.state,
        "created_at": conversation.created_at
    }


@router.get("/itinerary/{itinerary_id}")
async def get_itinerary(itinerary_id: str, db: Session = Depends(get_db)):
    """Get specific itinerary."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return {
        "id": str(itinerary.id),
        "destination": itinerary.destination,
        "duration_days": itinerary.duration_days,
        "budget": itinerary.budget,
        "season": itinerary.season,
        "travel_dates": itinerary.travel_dates,
        "plan": itinerary.plan,
        "budget_allocation": itinerary.budget_allocation,
        "created_at": itinerary.created_at
    }


@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
    """List all conversations."""
    conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).limit(50).all()
    return [
        {
            "id": str(c.id),
            "created_at": c.created_at,
            "has_itinerary": db.query(Itinerary).filter(Itinerary.conversation_id == c.id).first() is not None
        }
        for c in conversations
    ]