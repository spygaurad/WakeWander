"""
Node utilities for the travel planner graph.
Contains planner, executor, and validator functions.
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import re
from langgraph.types import interrupt
from app.agents.state import TravelPreferences, BudgetAllocation, LocationData


# Maximum retries for a step
MAX_RETRIES = 3


def create_general_handler(llm: ChatGoogleGenerativeAI):
    """
    Handle general questions and greetings.
    """
    def general_handler(state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n GENERAL HANDLER NODE ")
        user_request = state.get('user_request', '').lower()
        
        # Check if it's a travel-related request or general chat
        travel_keywords = ['travel', 'trip', 'visit', 'vacation', 'holiday', 'tour', 'destination', 
                          'days', 'budget', 'go to', 'fly to', 'plan', 'itinerary', 'day', 'week']
        
        is_travel_request = any(keyword in user_request for keyword in travel_keywords)
        
        if not is_travel_request:
            # Handle general chat requests
            general_prompt = f"""
            The user said: "{state.get('user_request')}"
            
            This seems like a general greeting or question, not a travel planning request.
            Respond warmly and encourage them to start planning a trip.
            
            Keep it brief (2-3 sentences) and friendly. Mention that you can help them plan trips
            by providing details like duration, budget, and season.
            """
            
            try:
                messages = [
                    SystemMessage(content="You are a friendly travel planning assistant."),
                    HumanMessage(content=general_prompt)
                ]
                response = llm.invoke(messages)
                content = response.content

                # Handle both string and list responses provided by Gemini

                if isinstance(content, list):
                    # Extract text from list format
                    content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
                elif not isinstance(content, str):
                    content = str(content)

                print(f" General chat response: {content}")
                # Handle both string and list responses
                if isinstance(content, list):
                    # Extract text from list format
                    content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
                elif not isinstance(content, str):
                    content = str(content)
                
                return {
                    "status": "general_chat",
                    "messages": [{"role": "assistant", "content": content}],
                    "is_general_chat": True
                }
            except Exception as e:
                print(f"Error generating general response: {e}")
                return {
                    "status": "general_chat",
                    "messages": [{"role": "assistant", "content": "Hello! I'm your AI travel planning assistant. I can help you plan amazing trips! Just tell me where you'd like to go, how many days, your budget, and preferred season, and I'll create a personalized itinerary for you!"}],
                    "is_general_chat": True
                }
        
        # It's a travel request - continue with analysis
        print(" Detected travel request, continuing to analysis")
        return {
            "status": "analyzing",
            "is_general_chat": False
        }
    
    return general_handler


def create_analyze_input(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to analyze user input and extract preferences.
    """
    def analyze_input(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze user request and extract travel preferences.
        """
        print("\n ANALYZE INPUT NODE ")
        user_request = state['user_request']
        existing_prefs = state.get('preferences')
        
        # Build preferences from existing state
        current_prefs = {}
        if existing_prefs:
            if hasattr(existing_prefs, 'to_dict'):
                current_prefs = existing_prefs.to_dict()
            elif isinstance(existing_prefs, dict):
                current_prefs = existing_prefs
        
        analysis_prompt = f"""
Analyze this travel request and extract structured information.

User Request: {user_request}

Current Preferences (if any): {json.dumps(current_prefs, indent=2)}

Extract and return a JSON object with these fields:
- destination: string (city/country name, or null if not mentioned)
- duration_days: integer (number of days, or null if not mentioned)
- budget: float (total budget in dollars, or null if not mentioned)
- season: string (spring/summer/fall/winter, or null if not mentioned)
- travel_dates: string (specific dates if mentioned, or null)
- interests: array of strings (activities/interests mentioned)
- accommodation_type: string (hotel/hostel/airbnb/luxury, or null)
- travel_style: string (budget/mid-range/luxury, or null)
- num_people: integer (number of travelers, default to 1 if not mentioned)

IMPORTANT: Return ONLY valid JSON, no markdown code blocks, no extra text.

Example output:
{{
    "destination": "Paris",
    "duration_days": 7,
    "budget": 4000,
    "season": "summer",
    "travel_dates": null,
    "interests": ["museums", "food", "architecture"],
    "accommodation_type": "mid-range hotel",
    "travel_style": "mid-range",
    "num_people": 2
}}
"""
        
        try:
            messages = [
                SystemMessage(content="You are a travel planning assistant that extracts structured data from user requests. Always return valid JSON only."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = llm.invoke(messages)
            content = response.content
            
            # Handle both string and list responses
            if isinstance(content, list):
                # Extract text from list format
                content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
            elif not isinstance(content, str):
                content = str(content)
                
            print(f" Raw LLM response: {content[:200]}...")
            
            # Clean up response - remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```'):
                # Remove markdown code blocks
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            # Extract JSON from the content
            # Try to find JSON object in the text
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                extracted = json.loads(json_str)
            else:
                # Try parsing the entire content as JSON
                extracted = json.loads(content)
            
            print(f" Extracted data: {extracted}")
            
            # Merge with existing preferences (new values override old)
            merged_prefs = {**current_prefs, **{k: v for k, v in extracted.items() if v is not None}}
            preferences = TravelPreferences(**merged_prefs)
            
            print(f" Final preferences: {preferences}")
            
            return {
                "preferences": preferences,
                "status": "analyzing",
                "messages": [{"role": "assistant", "content": "Analyzing your travel request..."}]
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}\nContent: {content[:500]}"
            print(f" ERROR: {error_msg}")
            return {
                "errors": [error_msg],
                "status": "failed"
            }
        except Exception as e:
            error_msg = f"Analysis error: {str(e)}"
            print(f" ERROR: {error_msg}")
            return {
                "errors": [error_msg],
                "status": "failed"
            }
    
    return analyze_input


def create_identify_missing(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to identify missing required information.
    """
    def identify_missing(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify what information is still needed.
        """
        print("\n=== IDENTIFY MISSING NODE ===")
        preferences = state.get('preferences')
        
        if not preferences:
            return {
                "missing_info": ["season", "budget", "duration_days"],
                "status": "missing_info"
            }
        
        # Required fields for initial planning
        required_fields = {
            "season": preferences.season,
            "budget": preferences.budget,
            "duration_days": preferences.duration_days
        }
        
        missing = [field for field, value in required_fields.items() if value is None]
        
        print(f"Missing fields: {missing}")
        
        if missing:
            return {
                "missing_info": missing,
                "status": "missing_info"
            }
        else:
            # Check if we need to research destinations
            if not preferences.destination:
                return {
                    "missing_info": [],
                    "needs_destination_research": True,
                    "status": "researching"
                }
            else:
                return {
                    "missing_info": [],
                    "needs_destination_research": False,
                    "status": "researching"
                }
    
    return identify_missing


def create_ask_question(llm: ChatGoogleGenerativeAI):
    """
    Creates function to ask user for missing information.
    """
    def ask_question(state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n=== ASK QUESTION NODE ===")
        missing_info = state.get('missing_info', [])
        
        if not missing_info:
            return {"status": "researching"}
        
        field = missing_info[0]
        
        questions = {
            "season": "Which season are you planning to travel? (spring/summer/fall/winter)",
            "duration_days": "How many days do you want to travel for?",
            "budget": "What's your total budget for this trip in USD?",
            "num_people": "How many people are traveling?",
            "destination": "Where would you like to travel to?",
            "travel_dates": "Do you have specific travel dates in mind?"
        }
        
        question = questions.get(field, f"Could you provide information about {field}?")
        
        print(f"Asking for field: {field}")
        print(f"Question: {question}")
        
        # This will cause an interrupt - the graph will pause here
        user_response = interrupt({
            "type": "question",
            "field": field,
            "question": question,
            "missing_info": missing_info
        })
        
        # When resumed, user_response will contain the answer
        print(f"User answered: {user_response}")
        
        # Update preferences with user's answer
        preferences = state.get('preferences')
        prefs_dict = preferences.to_dict() if hasattr(preferences, 'to_dict') else (preferences or {})
        
        # Type conversion based on field
        if field == "duration_days" or field == "num_people":
            prefs_dict[field] = int(user_response)
        elif field == "budget":
            prefs_dict[field] = float(user_response)
        else:
            prefs_dict[field] = str(user_response).strip()
        
        preferences = TravelPreferences(**prefs_dict)
        
        # Remove answered field from missing_info
        remaining_missing = [f for f in missing_info if f != field]
        
        return {
            "preferences": preferences,
            "missing_info": remaining_missing,
            "status": "analyzing",
            "messages": [
                {"role": "assistant", "content": question},
                {"role": "user", "content": str(user_response)}
            ]
        }
    
    return ask_question


def create_research(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to research destinations.
    """
    def research(state: Dict[str, Any]) -> Dict[str, Any]:
        print("\n=== RESEARCH NODE ===")
        preferences = state.get('preferences')
        
        if not preferences:
            return {
                "errors": ["No preferences specified"],
                "status": "failed"
            }
        
        destination = preferences.destination
        season = preferences.season
        budget = preferences.budget
        duration = preferences.duration_days
        num_people = preferences.num_people or 1
        
        # Calculate per-person daily budget
        daily_budget = (budget / duration) / num_people if budget and duration and num_people else None
        
        if not destination:
            # User didn't specify destination - suggest destinations
            research_prompt = f"""
            The user wants to travel but hasn't specified a destination.
            
            Travel details provided:
            - Season: {season}
            - Duration: {duration} days
            - Budget: ${budget} total (${daily_budget:.2f} per person per day)
            - Number of travelers: {num_people}
            
            Suggest 6-8 diverse travel destinations that would be perfect for these criteria.
            Focus on destinations that are great to visit in {season}.
            Ensure destinations fit within the ${daily_budget:.2f}/person/day budget.
            
            Return ONLY valid JSON, no markdown code blocks:
            {{
                "locations": [
                    {{
                        "name": "Paris, France",
                        "avg_daily_cost": 85.0,
                        "best_season": "spring",
                        "season_notes": "Perfect weather with blooming gardens",
                        "description": "The City of Light offers world-class museums, cuisine, and architecture",
                        "highlights": ["Eiffel Tower", "Louvre Museum", "Notre-Dame"]
                    }}
                ]
            }}
            """
        else:
            # User specified destination - research it + alternatives
            research_prompt = f"""
            Research travel information for {destination} and similar destinations.
            
            Travel criteria:
            - Season: {season}
            - Duration: {duration} days
            - Budget: ${budget} total (${daily_budget:.2f} per person per day)
            - Number of travelers: {num_people}
            
            Return ONLY valid JSON with {destination} as first option, then 5-6 similar alternatives.
            No markdown code blocks:
            {{
                "locations": [
                    {{
                        "name": "destination name",
                        "avg_daily_cost": 0.0,
                        "best_season": "season",
                        "season_notes": "notes",
                        "description": "description",
                        "highlights": ["attraction1", "attraction2"]
                    }}
                ]
            }}
            
            Ensure all destinations fit the budget and are good for {season}.
            """
        
        try:
            messages = [
                SystemMessage(content="You are a travel research expert. Always return valid JSON only, no markdown code blocks."),
                HumanMessage(content=research_prompt)
            ]
            
            response = llm.invoke(messages)
            content = response.content
            # Handle both string and list responses
            if isinstance(content, list):
                # Extract text from list format
                content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
            elif not isinstance(content, str):
                content = str(content)
            
            content = content.strip()
            print(f" Raw research response: {content[:200]}...")
            
            # Clean markdown code blocks
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            # Extract JSON
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(content)
            
            locations = [LocationData(**loc) for loc in data.get('locations', [])]
            
            print(f" Researched {len(locations)} locations")
            
            # If no destination was specified, we need user to choose
            needs_destination_selection = not destination
            
            return {
                "research_data": locations,
                "needs_destination_selection": needs_destination_selection,
                "status": "analyzed"
            }
            
        except Exception as e:
            error_msg = f"Research error: {str(e)}"
            print(f" ERROR: {error_msg}")
            return {
                "errors": [error_msg],
                "status": "failed"
            }
    
    return research


def create_analyze(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to analyze budget and select location.
    """
    def analyze(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze budget and select appropriate location.
        """
        print("\n=== ANALYZE NODE ===")
        preferences = state.get('preferences')
        research_data = state.get('research_data', [])
        needs_destination_selection = state.get('needs_destination_selection', False)
        
        if not preferences or not research_data:
            return {
                "errors": ["Missing preferences or research data"],
                "status": "failed"
            }
        
        # Calculate budget allocation
        total_budget = preferences.budget
        duration_days = preferences.duration_days
        num_people = preferences.num_people or 1
        
        daily_budget = total_budget / duration_days
        per_person_daily = daily_budget / num_people
        
        budget_allocation = BudgetAllocation(
            total_budget=total_budget,
            daily_budget=daily_budget,
            accommodation_budget=daily_budget * 0.40,
            food_budget=daily_budget * 0.25,
            activities_budget=daily_budget * 0.25,
            transport_budget=daily_budget * 0.05,
            contingency=daily_budget * 0.05
        )
        
        # Filter locations that fit budget (with 15% buffer)
        filtered = [loc for loc in research_data if loc.avg_daily_cost <= per_person_daily * 1.15]
        
        if not filtered:
            # Fallback: if no locations fit, take the cheapest ones
            filtered = sorted(research_data, key=lambda x: x.avg_daily_cost)[:5]
        
        print(f"Budget: ${per_person_daily:.2f}/person/day")
        print(f"Filtered {len(filtered)} locations within budget")
        
        # If destination was already specified, select it
        if not needs_destination_selection and preferences.destination:
            # Find the matching location
            selected = next(
                (loc for loc in filtered if preferences.destination.lower() in loc.name.lower()),
                filtered[0] if filtered else None
            )
            
            if selected:
                print(f"Pre-selected destination: {selected.name}")
                return {
                    "budget_allocation": budget_allocation,
                    "filtered_locations": filtered,
                    "selected_location": selected,
                    "status": "planning"
                }
        
        # User needs to select from options
        location_options = [
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
        
        print(f"Presenting {len(location_options)} location options to user")
        
        # INTERRUPT - let user select destination
        selected_index = interrupt({
            "type": "destination_selection",
            "question": f"I found {len(location_options)} great destinations within your ${per_person_daily:.2f}/person/day budget. Which would you like to visit?",
            "options": location_options,
            "budget_allocation": budget_allocation.to_dict()
        })
        
        # When resumed, selected_index will contain user's choice
        selected = filtered[int(selected_index)]
        
        print(f"User selected: {selected.name}")
        
        # Update preferences with selected destination
        prefs_dict = preferences.to_dict()
        prefs_dict['destination'] = selected.name
        preferences = TravelPreferences(**prefs_dict)
        
        return {
            "preferences": preferences,
            "budget_allocation": budget_allocation,
            "filtered_locations": filtered,
            "selected_location": selected,
            "status": "planning",
            "messages": [
                {"role": "assistant", "content": f"Excellent choice! Let me plan your {duration_days}-day trip to {selected.name}."}
            ]
        }
    
    return analyze


def create_season_recommendations(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to generate season-specific recommendations.
    """
    def season_recommendations(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate season-specific recommendations.
        """
        print("\n=== SEASON RECOMMENDATIONS NODE ===")
        preferences = state.get('preferences')
        selected_location = state.get('selected_location')
        
        if not preferences or not selected_location:
            return {}
        
        season = preferences.season
        if not season:
            return {"season_recommendations": None}
        
        recommendations_prompt = f"""
Generate season-specific travel recommendations for {selected_location.name} in {season}.

Include:
1. Weather expectations (temperature, rainfall, etc.)
2. What to pack (clothing, gear)
3. Best activities for {season}
4. Any seasonal events, festivals, or special considerations
5. Tips for making the most of {season} visit

Keep it concise and practical (4-5 sentences).

Provide just the text, no JSON.
"""
        
        try:
            messages = [
                SystemMessage(content="You are a travel expert specializing in seasonal travel planning."),
                HumanMessage(content=recommendations_prompt)
            ]
            
            response = llm.invoke(messages)
            content = response.content
            # Handle both string and list responses
            if isinstance(content, list):
                # Extract text from list format
                content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
            elif not isinstance(content, str):
                content = str(content)
            
            recommendations = content.strip()
            print(f" Generated season recommendations")
            
            return {
                "season_recommendations": recommendations
            }
            
        except Exception as e:
            print(f"Season recommendations error: {e}")
            return {"season_recommendations": None}
    
    return season_recommendations


def create_plan_days(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to plan day-by-day itinerary.
    """
    def plan_days(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create detailed day-by-day itinerary.
        """
        print("\n=== PLAN DAYS NODE ===")
        preferences = state.get('preferences')
        budget_allocation = state.get('budget_allocation')
        selected_location = state.get('selected_location')
        
        if not all([preferences, budget_allocation, selected_location]):
            return {
                "errors": ["Missing required data for planning"],
                "status": "failed"
            }
        
        num_people = preferences.num_people or 1
        
        planning_prompt = f"""
Create a detailed {preferences.duration_days}-day itinerary for {num_people} {"person" if num_people == 1 else "people"} visiting {selected_location.name}.

Budget per day (total): ${budget_allocation.daily_budget:.2f}
Budget per person per day: ${budget_allocation.daily_budget / num_people:.2f}
Season: {preferences.season}
Interests: {', '.join(preferences.interests or ['general sightseeing'])}

Budget breakdown per day (total for {num_people} {"person" if num_people == 1 else "people"}):
- Accommodation: ${budget_allocation.accommodation_budget:.2f}
- Food: ${budget_allocation.food_budget:.2f}
- Activities: ${budget_allocation.activities_budget:.2f}
- Transport: ${budget_allocation.transport_budget:.2f}

For each day, provide a JSON object with:
- day: day number (1, 2, 3, etc.)
- title: brief title for the day (e.g., "Exploring Historic Center")
- weather: expected weather for {preferences.season}
- season_notes: brief seasonal tip specific to that day's activities
- hotel: {{"name": string, "cost": float (total for {num_people} {"person" if num_people == 1 else "people"})}}
- breakfast: {{"location": string, "cost": float (total)}}
- lunch: {{"location": string, "cost": float (total)}}
- dinner: {{"location": string, "cost": float (total)}}
- activities: array of {{"time": string, "activity": string, "location": string, "cost": float, "duration": string}}
- daily_total: float (sum of all costs for the day)

Return ONLY valid JSON, no markdown:
{{
    "days": [
        {{
            "day": 1,
            "title": "Arrival and City Orientation",
            "weather": "Sunny, 75°F",
            "season_notes": "Perfect weather for walking tours",
            "hotel": {{"name": "Central Hotel", "cost": 150.0}},
            "breakfast": {{"location": "Hotel Breakfast", "cost": 20.0}},
            "lunch": {{"location": "Local Bistro", "cost": 45.0}},
            "dinner": {{"location": "Traditional Restaurant", "cost": 60.0}},
            "activities": [
                {{"time": "10:00 AM", "activity": "Walking Tour", "location": "Old Town", "cost": 25.0, "duration": "3 hours"}}
            ],
            "daily_total": 300.0
        }}
    ]
}}
"""
        
        try:
            messages = [
                SystemMessage(content="You are an expert travel itinerary planner. Return only valid JSON, no markdown code blocks."),
                HumanMessage(content=planning_prompt)
            ]
            
            response = llm.invoke(messages)
            content = response.content

            # Handle both string and list responses
            if isinstance(content, list):
                # Extract text from list format
                content = ''.join([item.get('text', '') if isinstance(item, dict) else str(item) for item in content])
            elif not isinstance(content, str):
                content = str(content)
            
            content = content.strip()
            print(f" Raw planning response: {content[:200]}...")

            # Clean markdown
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            # Extract JSON - find the outermost braces
            try:
                json_start = content.find('{')
                json_end = content.rfind('}')
                
                if json_start != -1 and json_end != -1:
                    json_str = content[json_start:json_end + 1]
                    data = json.loads(json_str)
                else:
                    data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f" JSON parsing failed: {e}")
                print(f"Content: {content[:500]}")
                raise

            daily_plans = data.get('days', [])
            
            print(f" Created {len(daily_plans)} daily plans")
            
            return {
                "daily_plans": daily_plans,
                "status": "finalizing"
            }
            
        except Exception as e:
            error_msg = f"Planning error: {str(e)}"
            print(f" ERROR: {error_msg}")
            return {
                "errors": [error_msg],
                "status": "failed"
            }
    
    return plan_days


def create_finalize(llm: ChatGoogleGenerativeAI):
    """
    Creates a function to finalize the complete itinerary.
    """
    def finalize(state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create final complete itinerary.
        """
        print("\n=== FINALIZE NODE ===")
        preferences = state.get('preferences')
        budget_allocation = state.get('budget_allocation')
        selected_location = state.get('selected_location')
        season_recommendations = state.get('season_recommendations')
        daily_plans = state.get('daily_plans', [])
        
        if not all([preferences, budget_allocation, selected_location, daily_plans]):
            return {
                "errors": ["Missing required data for finalization"],
                "status": "failed"
            }
        
        # Calculate total costs
        total_cost = sum(day.get('daily_total', 0) for day in daily_plans)
        
        # Build final itinerary
        itinerary = {
            "destination": selected_location.name,
            "duration_days": preferences.duration_days,
            "num_people": preferences.num_people or 1,
            "season": preferences.season,
            "travel_dates": preferences.travel_dates,
            "total_budget": preferences.budget,
            "actual_cost": total_cost,
            "budget_remaining": preferences.budget - total_cost,
            "budget_allocation": budget_allocation.to_dict() if budget_allocation else None,
            "season_recommendations": season_recommendations,
            "daily_itinerary": daily_plans,
            "summary": {
                "destination_description": selected_location.description,
                "best_season": selected_location.best_season,
                "avg_daily_cost": selected_location.avg_daily_cost,
                "total_days": len(daily_plans),
                "total_activities": sum(len(day.get('activities', [])) for day in daily_plans)
            }
        }
        
        print(f" Finalized itinerary: {selected_location.name}, {len(daily_plans)} days")
        print(f"   Total cost: ${total_cost:.2f} / ${preferences.budget:.2f}")
        
        return {
            "itinerary": itinerary,
            "status": "completed",
            "messages": [{"role": "assistant", "content": f"🎉 Your {preferences.duration_days}-day {preferences.season} itinerary for {selected_location.name} is ready!"}]
        }
    
    return finalize