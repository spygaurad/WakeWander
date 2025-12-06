"""
ReAct Travel Itinerary Agent with Auto-Selection Flow

FLOW:
Step 1: Auto-select season (spring, summer, fall, winter)
Step 2: Auto-select budget tier (budget, medium, luxury)
Step 3: Auto-select duration (days) and group size
Step 4: Search destinations based on selections
Step 5: Reason and select ONE destination
Step 6: Get detailed info about selected destination
Step 7: Generate day-by-day itinerary
Step 8: Compile final itinerary
"""

import json
import os
from typing import TypedDict, Annotated, Literal
from operator import add
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

MAX_ITERATIONS = 25


# ============================================================================
# STEP 1: AUTO-SELECT SEASON
# ============================================================================
@tool
def auto_select_season(user_hint: str = "") -> str:
    """
    STEP 1: Auto-select travel season from: spring, summer, fall, winter.
    Args:
        user_hint: Optional hint like "warm", "avoid crowds", "beach"
    """
    seasons = {
        "spring": {"months": "Mar-May", "weather": "55-70°F", "pros": ["Fewer crowds", "Flowers"], "best_for": ["Gardens", "Hiking"]},
        "summer": {"months": "Jun-Aug", "weather": "75-95°F", "pros": ["Beach weather", "Long days"], "best_for": ["Beaches", "Festivals"]},
        "fall": {"months": "Sep-Nov", "weather": "50-70°F", "pros": ["Foliage", "Comfortable"], "best_for": ["Sightseeing", "Wine tours"]},
        "winter": {"months": "Dec-Feb", "weather": "30-50°F", "pros": ["Low prices", "No crowds"], "best_for": ["Museums", "Skiing"]}
    }
    
    scores = {"spring": 25, "summer": 25, "fall": 25, "winter": 25}
    reasoning = []
    hint = user_hint.lower()
    
    boosts = {
        "warm": {"summer": 30, "spring": 15}, "beach": {"summer": 40}, "avoid crowds": {"fall": 25, "winter": 25},
        "cheap": {"winter": 30}, "budget": {"winter": 30}, "foliage": {"fall": 40}, "snow": {"winter": 40},
        "ski": {"winter": 40}, "flowers": {"spring": 40}, "hiking": {"fall": 20, "spring": 20}
    }
    
    for keyword, boost_map in boosts.items():
        if keyword in hint:
            for s, b in boost_map.items():
                scores[s] += b
                reasoning.append(f"'{keyword}' → {s} +{b}")
    
    if not hint:
        month = datetime.now().month
        current = "winter" if month in [12,1,2] else "spring" if month in [3,4,5] else "summer" if month in [6,7,8] else "fall"
        scores[current] += 15
        reasoning.append(f"Current season ({current}) +15")
    
    selected = max(scores, key=scores.get)
    return json.dumps({
        "step": 1, "name": "season_selection", "selected_season": selected,
        "details": seasons[selected], "scores": scores, "reasoning": reasoning or ["Default scoring"]
    })


# ============================================================================
# STEP 2: AUTO-SELECT BUDGET
# ============================================================================
@tool
def auto_select_budget(season: str, user_hint: str = "") -> str:
    """
    STEP 2: Auto-select budget tier from: budget, medium, luxury.
    Args:
        season: Selected season (affects pricing)
        user_hint: Optional hint like "cheap", "splurge", "moderate"
    """
    tiers = {
        "budget": {"daily": [80, 150], "desc": "Hostels, street food, free attractions"},
        "medium": {"daily": [150, 300], "desc": "3-star hotels, restaurants, tours"},
        "luxury": {"daily": [300, 600], "desc": "5-star hotels, fine dining, private tours"}
    }
    
    multipliers = {"summer": 1.3, "winter": 0.8, "spring": 1.0, "fall": 1.0}
    mult = multipliers.get(season.lower(), 1.0)
    
    scores = {"budget": 33, "medium": 34, "luxury": 33}
    reasoning = []
    hint = user_hint.lower()
    
    boosts = {
        "cheap": {"budget": 40}, "save": {"budget": 30}, "backpack": {"budget": 40},
        "moderate": {"medium": 40}, "comfortable": {"medium": 35},
        "splurge": {"luxury": 40}, "luxury": {"luxury": 45}, "honeymoon": {"luxury": 40}
    }
    
    for keyword, boost_map in boosts.items():
        if keyword in hint:
            for t, b in boost_map.items():
                scores[t] += b
                reasoning.append(f"'{keyword}' → {t} +{b}")
    
    if not hint:
        scores["medium"] += 20
        reasoning.append("No preference → medium +20")
    
    selected = max(scores, key=scores.get)
    daily = round(sum(tiers[selected]["daily"]) / 2 * mult, 2)
    
    return json.dumps({
        "step": 2, "name": "budget_selection", "selected_tier": selected,
        "daily_budget": daily, "season_multiplier": mult,
        "details": tiers[selected], "scores": scores, "reasoning": reasoning
    })


# ============================================================================
# STEP 3: AUTO-SELECT DURATION AND GROUP SIZE
# ============================================================================
@tool
def auto_select_trip_params(season: str, budget_tier: str, user_hint: str = "") -> str:
    """
    STEP 3: Auto-select duration (3,5,7,10,14 days) and group size (1,2,4,6).
    Args:
        season: Selected season
        budget_tier: Selected budget tier
        user_hint: Optional hint like "weekend", "week", "solo", "couple"
    """
    durations = {3: "Long Weekend", 5: "Short Trip", 7: "One Week", 10: "Extended", 14: "Two Weeks"}
    groups = {1: "Solo", 2: "Couple", 4: "Small Group", 6: "Large Group"}
    
    dur_scores = {3: 20, 5: 25, 7: 30, 10: 15, 14: 10}
    grp_scores = {1: 20, 2: 35, 4: 30, 6: 15}
    reasoning = []
    hint = user_hint.lower()
    
    dur_boosts = {"weekend": {3: 40}, "short": {3: 30, 5: 20}, "week": {7: 40}, "long": {10: 30, 14: 25}}
    grp_boosts = {"solo": {1: 50}, "alone": {1: 45}, "couple": {2: 50}, "romantic": {2: 45}, "friends": {4: 40}, "family": {4: 35, 6: 25}}
    
    for kw, bm in dur_boosts.items():
        if kw in hint:
            for d, b in bm.items():
                dur_scores[d] += b
                reasoning.append(f"'{kw}' → {d} days +{b}")
    
    for kw, bm in grp_boosts.items():
        if kw in hint:
            for g, b in bm.items():
                grp_scores[g] += b
                reasoning.append(f"'{kw}' → group {g} +{b}")
    
    if budget_tier == "budget":
        dur_scores[7] += 15
        reasoning.append("Budget tier → longer trip +15")
    elif budget_tier == "luxury":
        dur_scores[3] += 15
        reasoning.append("Luxury tier → shorter trip +15")
    
    sel_dur = max(dur_scores, key=dur_scores.get)
    sel_grp = max(grp_scores, key=grp_scores.get)
    
    return json.dumps({
        "step": 3, "name": "trip_params_selection",
        "selected_duration_days": sel_dur, "selected_group_size": sel_grp,
        "duration_name": durations[sel_dur], "group_name": groups[sel_grp],
        "reasoning": reasoning or ["Default selection"]
    })


# ============================================================================
# STEP 4: SEARCH DESTINATIONS
# ============================================================================
@tool
def search_destinations(budget_per_day: float, duration: int, season: str, interests: str = "sightseeing") -> str:
    """
    STEP 4: Search destinations based on auto-selected parameters.
    Args:
        budget_per_day: Daily budget
        duration: Trip duration in days
        season: Travel season
        interests: Travel interests
    """
    db = {
        "St. Augustine, Florida, USA": {
            "cost": {"budget": 120, "medium": 250, "luxury": 500},
            "seasons": ["fall", "spring", "winter"], "type": "Historic City",
            "activities": ["history", "architecture", "beaches", "ghost tours", "food"],
            "highlights": ["Oldest US city", "Spanish fort", "Lighthouses"], "rating": 4.5
        },
        "Lisbon, Portugal": {
            "cost": {"budget": 70, "medium": 140, "luxury": 280},
            "seasons": ["spring", "fall"], "type": "European Capital",
            "activities": ["history", "culture", "food", "architecture", "nightlife"],
            "highlights": ["Historic trams", "Pastéis de nata", "Fado music"], "rating": 4.6
        },
        "Kyoto, Japan": {
            "cost": {"budget": 90, "medium": 180, "luxury": 400},
            "seasons": ["spring", "fall"], "type": "Cultural City",
            "activities": ["temples", "culture", "food", "gardens", "history"],
            "highlights": ["Ancient temples", "Geisha district", "Bamboo forest"], "rating": 4.8
        },
        "Barcelona, Spain": {
            "cost": {"budget": 85, "medium": 170, "luxury": 350},
            "seasons": ["spring", "fall", "summer"], "type": "Beach City",
            "activities": ["architecture", "beaches", "food", "nightlife", "art"],
            "highlights": ["Gaudí architecture", "La Rambla", "Beaches"], "rating": 4.5
        },
        "Marrakech, Morocco": {
            "cost": {"budget": 50, "medium": 120, "luxury": 300},
            "seasons": ["spring", "fall", "winter"], "type": "Exotic City",
            "activities": ["culture", "shopping", "food", "history"],
            "highlights": ["Medina souks", "Jardin Majorelle", "Moroccan cuisine"], "rating": 4.4
        }
    }
    
    tier = "budget" if budget_per_day < 100 else "medium" if budget_per_day < 200 else "luxury"
    candidates = []
    
    for name, info in db.items():
        score = 0
        reasons = []
        
        if season.lower() in [s.lower() for s in info["seasons"]]:
            score += 30
            reasons.append(f"Good for {season}")
        
        daily = info["cost"][tier]
        if daily <= budget_per_day * 1.1:
            score += 25
            reasons.append("Within budget")
        
        for act in info["activities"]:
            if act in interests.lower():
                score += 10
                reasons.append(f"Matches: {act}")
        
        score += int(info["rating"] * 5)
        
        if score > 20:
            candidates.append({
                "destination": name, "type": info["type"],
                "daily_cost": daily, "total_cost": daily * duration,
                "highlights": info["highlights"], "rating": info["rating"],
                "score": score, "reasons": reasons
            })
    
    candidates.sort(key=lambda x: x["score"], reverse=True)
    
    return json.dumps({
        "step": 4, "name": "destination_search",
        "params": {"budget_per_day": budget_per_day, "tier": tier, "duration": duration, "season": season},
        "found": len(candidates), "destinations": candidates[:5]
    })


# ============================================================================
# STEP 5: SELECT ONE DESTINATION
# ============================================================================
@tool
def select_destination(candidates_json: str) -> str:
    """
    STEP 5: Reason through candidates and select ONE best destination.
    Args:
        candidates_json: JSON string from search_destinations
    """
    try:
        data = json.loads(candidates_json)
        candidates = data.get("destinations", data if isinstance(data, list) else [data])
    except:
        return json.dumps({"error": "Invalid JSON", "selected": None})
    
    if not candidates:
        return json.dumps({"error": "No candidates", "selected": None})
    
    selected = candidates[0]
    reasoning = [f"Evaluated {len(candidates)} candidates"]
    for i, c in enumerate(candidates[:3], 1):
        reasoning.append(f"{i}. {c['destination']}: Score {c.get('score', 'N/A')}, ${c.get('daily_cost', '?')}/day")
    reasoning.append(f"Selected: {selected['destination']} - {', '.join(selected.get('reasons', []))}")
    
    return json.dumps({
        "step": 5, "name": "destination_selection",
        "selected_destination": selected["destination"],
        "destination_details": selected,
        "alternatives": [c["destination"] for c in candidates[1:3]],
        "reasoning": reasoning
    })


# ============================================================================
# STEP 6: GET DESTINATION DETAILS
# ============================================================================
@tool
def get_destination_details(destination: str) -> str:
    """
    STEP 6: Get comprehensive details about selected destination.
    Args:
        destination: Name of selected destination
    """
    details = {
        "St. Augustine, Florida, USA": {
            "overview": {"founded": "1565", "claim": "Oldest US city", "best_time": "Oct-Nov"},
            "weather": {"fall": "70-85°F, pleasant", "spring": "70-80°F", "winter": "55-70°F"},
            "attractions": [
                {"name": "Castillo de San Marcos", "cost": 15, "duration": "1.5h"},
                {"name": "St. George Street", "cost": 0, "duration": "2h"},
                {"name": "Lightner Museum", "cost": 17, "duration": "1.5h"},
                {"name": "St. Augustine Lighthouse", "cost": 15, "duration": "1.5h"},
                {"name": "Flagler College", "cost": 15, "duration": "1h"},
                {"name": "Fountain of Youth", "cost": 19, "duration": "1.5h"},
                {"name": "Ghost Tours", "cost": 25, "duration": "1.5h"}
            ],
            "restaurants": [
                {"name": "Columbia Restaurant", "cuisine": "Spanish", "price": "$$"},
                {"name": "The Floridian", "cuisine": "Southern", "price": "$$"},
                {"name": "Cap's on the Water", "cuisine": "Seafood", "price": "$$$"}
            ],
            "tips": ["Walk downtown", "Book ghost tours early", "Visit Castillo at opening", "Try datil pepper sauce"]
        },
        "Lisbon, Portugal": {
            "overview": {"claim": "City of seven hills", "best_time": "Apr-Jun, Sep-Oct"},
            "attractions": [
                {"name": "Belém Tower", "cost": 10, "duration": "1h"},
                {"name": "Jerónimos Monastery", "cost": 12, "duration": "1.5h"},
                {"name": "Alfama District", "cost": 0, "duration": "3h"},
                {"name": "Tram 28", "cost": 3, "duration": "1h"}
            ],
            "tips": ["Wear comfortable shoes", "Get Viva Viagem card", "Day trip to Sintra"]
        }
    }
    
    info = details.get(destination, {"overview": {"name": destination}, "tips": ["Research local customs"]})
    return json.dumps({"step": 6, "name": "destination_details", "destination": destination, "details": info})


# ============================================================================
# STEP 7: GENERATE DAILY ITINERARY
# ============================================================================
@tool
def generate_daily_itinerary(destination: str, day_number: int, total_days: int, daily_budget: float, group_size: int) -> str:
    """
    STEP 7: Generate itinerary for ONE specific day. Call once per day.
    Args:
        destination: Selected destination
        day_number: Which day (1, 2, 3...)
        total_days: Total trip duration
        daily_budget: Budget per day
        group_size: Number of travelers
    """
    itineraries = {
        "St. Augustine, Florida, USA": {
            1: {
                "theme": "Arrival & Historic Downtown",
                "schedule": [
                    {"time": "10:00 AM", "activity": "Arrive & check in", "cost": 0},
                    {"time": "11:30 AM", "activity": "Old Town Trolley Tour", "cost": 40},
                    {"time": "1:00 PM", "activity": "Lunch at Columbia Restaurant", "cost": 35},
                    {"time": "3:00 PM", "activity": "Castillo de San Marcos", "cost": 15},
                    {"time": "5:00 PM", "activity": "St. George Street exploration", "cost": 0},
                    {"time": "7:30 PM", "activity": "Dinner at The Floridian", "cost": 45},
                    {"time": "9:30 PM", "activity": "Ghost Tour", "cost": 25}
                ],
                "total": 160
            },
            2: {
                "theme": "Gilded Age & Maritime",
                "schedule": [
                    {"time": "8:30 AM", "activity": "Breakfast at Blue Hen Cafe", "cost": 20},
                    {"time": "10:00 AM", "activity": "Flagler College Tour", "cost": 15},
                    {"time": "11:30 AM", "activity": "Lightner Museum", "cost": 17},
                    {"time": "1:30 PM", "activity": "Lunch at Cafe Alcazar", "cost": 25},
                    {"time": "3:00 PM", "activity": "St. Augustine Lighthouse", "cost": 15},
                    {"time": "5:30 PM", "activity": "Beach time", "cost": 0},
                    {"time": "8:00 PM", "activity": "Dinner at Cap's on the Water", "cost": 55}
                ],
                "total": 147
            },
            3: {
                "theme": "Origins & Departure",
                "schedule": [
                    {"time": "8:00 AM", "activity": "Breakfast at The Kookaburra", "cost": 18},
                    {"time": "9:30 AM", "activity": "Fountain of Youth", "cost": 19},
                    {"time": "12:00 PM", "activity": "Hotel checkout", "cost": 0},
                    {"time": "12:30 PM", "activity": "Lunch on Aviles Street", "cost": 30},
                    {"time": "2:30 PM", "activity": "Last shopping/exploring", "cost": 20},
                    {"time": "4:00 PM", "activity": "Depart", "cost": 0}
                ],
                "total": 87
            }
        }
    }
    
    dest_itins = itineraries.get(destination, {})
    if day_number in dest_itins:
        itin = dest_itins[day_number]
    else:
        itin = {
            "theme": f"Day {day_number} Exploration",
            "schedule": [
                {"time": "9:00 AM", "activity": "Breakfast", "cost": 20},
                {"time": "10:30 AM", "activity": "Morning attraction", "cost": 25},
                {"time": "1:00 PM", "activity": "Lunch", "cost": 30},
                {"time": "3:00 PM", "activity": "Afternoon activity", "cost": 20},
                {"time": "7:00 PM", "activity": "Dinner", "cost": 45}
            ],
            "total": 140
        }
    
    return json.dumps({
        "step": 7, "name": f"daily_itinerary_day_{day_number}",
        "day": day_number, "total_days": total_days,
        "theme": itin["theme"], "schedule": itin["schedule"],
        "day_total": itin["total"], "group_total": itin["total"] * group_size
    })


# ============================================================================
# STEP 8: COMPILE FINAL ITINERARY
# ============================================================================
@tool
def compile_final_itinerary(destination: str, duration: int, group_size: int, season: str, 
                            budget_tier: str, daily_budget: float, daily_itineraries_json: str) -> str:
    """
    STEP 8: Compile all info into final itinerary.
    Args:
        destination: Selected destination
        duration: Trip duration
        group_size: Number of travelers
        season: Travel season
        budget_tier: Budget tier
        daily_budget: Daily budget
        daily_itineraries_json: JSON of all daily itineraries
    """
    try:
        days = json.loads(daily_itineraries_json)
        if not isinstance(days, list):
            days = [days]
    except:
        days = []
    
    total_cost = sum(d.get("day_total", 0) for d in days)
    total_budget = daily_budget * duration
    
    return json.dumps({
        "step": 8, "name": "final_compilation", "status": "complete",
        "itinerary": {
            "title": f"{duration}-Day {destination} Itinerary",
            "trip_overview": {
                "destination": destination, "duration": duration, "travelers": group_size,
                "season": season, "budget_tier": budget_tier
            },
            "budget_summary": {
                "daily_budget": daily_budget, "total_budget": total_budget,
                "estimated_cost": total_cost, "remaining": max(0, total_budget - total_cost)
            },
            "daily_breakdown": days,
            "tips": ["Book accommodations early", "Reserve popular restaurants", "Arrange airport transport"]
        }
    })


# ============================================================================
# TOOL REGISTRY
# ============================================================================
TOOLS = [auto_select_season, auto_select_budget, auto_select_trip_params, search_destinations,
         select_destination, get_destination_details, generate_daily_itinerary, compile_final_itinerary]
TOOL_MAP = {t.name: t for t in TOOLS}


# ============================================================================
# AGENT STATE
# ============================================================================
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add]
    iterations: int
    user_input: dict
    gathered_info: dict
    is_complete: bool


# ============================================================================
# LLM
# ============================================================================
_llm = None

def get_llm():
    global _llm
    if _llm is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        _llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=api_key, temperature=0.3).bind_tools(TOOLS)
    return _llm


# ============================================================================
# NODES
# ============================================================================
def reasoning_node(state: AgentState) -> dict:
    print(f"\n{'='*60}\n🧠 [Iter {state['iterations']+1}] REASONING\n{'='*60}")
    
    if state["iterations"] >= MAX_ITERATIONS:
        return {"iterations": state["iterations"] + 1, "is_complete": True}
    
    g = state.get("gathered_info", {})
    user = state["user_input"]
    
    # Progress tracking
    progress = []
    if g.get("selected_season"): progress.append(f"✓ Step 1: Season = {g['selected_season']}")
    if g.get("budget_tier"): progress.append(f"✓ Step 2: Budget = {g['budget_tier']} (${g.get('daily_budget', '?')}/day)")
    if g.get("duration"): progress.append(f"✓ Step 3: {g['duration']} days, {g.get('group_size', '?')} travelers")
    if g.get("destinations"): progress.append(f"✓ Step 4: Found {len(g['destinations'])} destinations")
    if g.get("selected_destination"): progress.append(f"✓ Step 5: Selected {g['selected_destination']}")
    if g.get("destination_details"): progress.append("✓ Step 6: Got details")
    daily = g.get("daily_itineraries", [])
    dur = g.get("duration", 0)
    if daily: progress.append(f"✓ Step 7: Itineraries {len(daily)}/{dur} days")
    if g.get("final_itinerary"): progress.append("✓ Step 8: COMPLETE!")
    
    prompt = f"""You are a travel planner using ReAct. Follow these 8 steps IN ORDER:

1. auto_select_season - Select season (pass user_hint from preferences)
2. auto_select_budget - Select budget tier (pass season from step 1)
3. auto_select_trip_params - Select duration & group size (pass season, budget_tier)
4. search_destinations - Search places (pass budget_per_day, duration, season, interests)
5. select_destination - Pick ONE destination (pass the search results JSON)
6. get_destination_details - Get details (pass destination name)
7. generate_daily_itinerary - Generate EACH day (call {dur or 'N'} times, once per day!)
8. compile_final_itinerary - Compile final output

USER PREFERENCES: {user.get('preferences', '')}
USER INTERESTS: {user.get('interests', '')}
USER HINTS: {user.get('hints', '')}

PROGRESS:
{chr(10).join(progress) if progress else 'Starting fresh...'}

Daily itineraries: {len(daily)}/{dur if dur else '?'}

Call the NEXT incomplete step. For step 7, call once per day until all {dur or 'N'} days done."""

    try:
        response = get_llm().invoke(state["messages"] + [HumanMessage(content=prompt)])
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        return {"iterations": state["iterations"] + 1, "is_complete": True}
    
    if hasattr(response, 'tool_calls') and response.tool_calls:
        print(f"🔧 Calling: {[tc['name'] for tc in response.tool_calls]}")
    
    return {"messages": [response], "iterations": state["iterations"] + 1}


def should_continue(state: AgentState) -> Literal["act", "finalize"]:
    if state.get("is_complete") or state["iterations"] >= MAX_ITERATIONS:
        return "finalize"
    last = state["messages"][-1] if state["messages"] else None
    if last and hasattr(last, 'tool_calls') and last.tool_calls:
        return "act"
    return "finalize"


def action_node(state: AgentState) -> dict:
    print(f"\n{'='*60}\n⚡ [Iter {state['iterations']}] ACTION\n{'='*60}")
    
    last = state["messages"][-1]
    if not hasattr(last, 'tool_calls') or not last.tool_calls:
        return {"is_complete": True}
    
    results = []
    g = dict(state.get("gathered_info", {}))
    if "daily_itineraries" not in g:
        g["daily_itineraries"] = []
    
    for tc in last.tool_calls:
        name, args, tid = tc["name"], tc["args"], tc["id"]
        print(f"→ {name}")
        
        tool_fn = TOOL_MAP.get(name)
        if not tool_fn:
            results.append(ToolMessage(tool_call_id=tid, name=name, content='{"error":"Unknown tool"}'))
            continue
        
        # Special handling for compile
        if name == "compile_final_itinerary":
            args["daily_itineraries_json"] = json.dumps(g.get("daily_itineraries", []))
        
        try:
            result = tool_fn.invoke(args)
        except Exception as e:
            result = json.dumps({"error": str(e)})
        
        # Parse and store
        try:
            data = json.loads(result)
        except:
            data = {"raw": result}
        
        # Update gathered info based on tool
        if name == "auto_select_season":
            g["selected_season"] = data.get("selected_season")
            print(f"  ✓ Season: {g['selected_season']}")
        elif name == "auto_select_budget":
            g["budget_tier"] = data.get("selected_tier")
            g["daily_budget"] = data.get("daily_budget")
            print(f"  ✓ Budget: {g['budget_tier']} (${g['daily_budget']}/day)")
        elif name == "auto_select_trip_params":
            g["duration"] = data.get("selected_duration_days")
            g["group_size"] = data.get("selected_group_size")
            print(f"  ✓ Duration: {g['duration']} days, Group: {g['group_size']}")
        elif name == "search_destinations":
            g["destinations"] = data.get("destinations", [])
            g["search_results"] = data
            print(f"  ✓ Found {len(g['destinations'])} destinations")
        elif name == "select_destination":
            g["selected_destination"] = data.get("selected_destination")
            print(f"  ✓ Selected: {g['selected_destination']}")
        elif name == "get_destination_details":
            g["destination_details"] = data.get("details")
            print(f"  ✓ Got destination details")
        elif name == "generate_daily_itinerary":
            g["daily_itineraries"].append(data)
            print(f"  ✓ Day {data.get('day', '?')} itinerary")
        elif name == "compile_final_itinerary":
            g["final_itinerary"] = data.get("itinerary", data)
            print(f"  ✓ Final itinerary compiled!")
        
        results.append(ToolMessage(tool_call_id=tid, name=name, content=result))
    
    is_done = "compile_final_itinerary" in [tc["name"] for tc in last.tool_calls]
    return {"messages": results, "gathered_info": g, "is_complete": is_done}


def finalize_node(state: AgentState) -> dict:
    print(f"\n{'='*60}\n🎉 FINAL RESULT ({state['iterations']} iterations)\n{'='*60}")
    g = state.get("gathered_info", {})
    
    if "final_itinerary" in g:
        print(json.dumps(g["final_itinerary"], indent=2))
    else:
        print("⚠️ Incomplete. Gathered:")
        for k, v in g.items():
            if k != "daily_itineraries":
                print(f"  {k}: {v if not isinstance(v, (list, dict)) else '...'}")
            else:
                print(f"  daily_itineraries: {len(v)} days")
    
    return {"is_complete": True}


# ============================================================================
# GRAPH
# ============================================================================
def build_graph():
    g = StateGraph(AgentState)
    g.add_node("reason", reasoning_node)
    g.add_node("act", action_node)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "reason")
    g.add_conditional_edges("reason", should_continue, {"act": "act", "finalize": "finalize"})
    g.add_edge("act", "reason")
    g.add_edge("finalize", END)
    return g.compile()


# ============================================================================
# MAIN
# ============================================================================
def run_travel_agent(preferences: str = "relaxing trip", interests: str = "history, food", hints: str = ""):
    print(f"\n{'='*60}\n🌍 REACT TRAVEL PLANNER\n{'='*60}")
    print(f"Preferences: {preferences}\nInterests: {interests}\nHints: {hints or 'none'}\n")
    
    agent = build_graph()
    initial = {
        "messages": [HumanMessage(content=f"Plan trip. Prefs: {preferences}. Interests: {interests}")],
        "iterations": 0,
        "user_input": {"preferences": preferences, "interests": interests, "hints": hints},
        "gathered_info": {},
        "is_complete": False
    }
    
    try:
        final = agent.invoke(initial)
        print(f"\n✅ Complete in {final.get('iterations', '?')} iterations")
        return final.get("gathered_info", {}).get("final_itinerary")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    load_dotenv()
    run_travel_agent(
        preferences="relaxing cultural trip",
        interests="history, food, architecture, ghost tours",
        hints="avoid crowds, moderate budget, couple"
    )