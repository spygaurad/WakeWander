"""
Reusable utility functions for budget calculations.
"""
from typing import List, Dict, Any
from app.schemas.schemas import LocationInfo, BudgetAllocation


def allocate_budget(total_budget: float, days: int) -> BudgetAllocation:
    """
    Smart budget allocation based on typical travel spending patterns.
    """
    daily_budget = total_budget / days
    
    return BudgetAllocation(
        total_budget=total_budget,
        duration_days=days,
        daily_budget=daily_budget,
        accommodation_budget=daily_budget * 0.45,
        food_budget=daily_budget * 0.30,
        activities_budget=daily_budget * 0.20,
        transportation_budget=total_budget * 0.15,
        buffer=total_budget * 0.05
    )


def filter_locations_by_budget(
    locations: List[LocationInfo],
    daily_budget: float,
    tolerance: float = 1.2
) -> List[LocationInfo]:
    """Filter locations that fit within daily budget."""
    max_budget = daily_budget * tolerance
    
    filtered = [
        loc for loc in locations
        if loc.avg_daily_cost <= max_budget
    ]
    
    filtered.sort(key=lambda x: abs(x.avg_daily_cost - daily_budget))
    
    return filtered


def check_budget_feasibility(
    hotel_cost: float,
    meal_costs: List[float],
    activity_costs: List[float],
    daily_budget: float
) -> Dict[str, Any]:
    """Check if a day's expenses fit within budget."""
    total = hotel_cost + sum(meal_costs) + sum(activity_costs)
    remaining = daily_budget - total
    percentage = (total / daily_budget * 100) if daily_budget > 0 else 0
    
    return {
        "within_budget": total <= daily_budget,
        "total": total,
        "remaining": remaining,
        "percentage_used": percentage,
        "over_budget": max(0, total - daily_budget)
    }


def calculate_meal_budget(daily_food_budget: float) -> Dict[str, float]:
    """Split daily food budget across meals."""
    return {
        "breakfast": daily_food_budget * 0.20,
        "lunch": daily_food_budget * 0.35,
        "dinner": daily_food_budget * 0.45
    }


def get_season_price_multiplier(season: str, destination_type: str) -> float:
    """
    Get price multiplier based on season and destination.
    
    Args:
        season: winter, spring, summer, fall
        destination_type: beach, mountain, city, tropical
    
    Returns:
        Multiplier (1.0 = normal, 1.3 = 30% more expensive)
    """
    # Beach destinations
    if destination_type == "beach":
        if season in ["summer", "spring"]:
            return 1.3  # Peak season
        elif season == "fall":
            return 1.1  # Shoulder season
        else:  # winter
            return 0.9  # Off season
    
    # Mountain destinations (skiing)
    elif destination_type == "mountain":
        if season == "winter":
            return 1.4  # Ski season
        elif season in ["spring", "fall"]:
            return 1.0  # Normal
        else:  # summer
            return 1.2  # Hiking season
    
    # City destinations
    elif destination_type == "city":
        if season in ["summer", "winter"]:  # Holiday seasons
            return 1.2
        else:
            return 1.0
    
    # Tropical destinations
    elif destination_type == "tropical":
        if season in ["winter", "spring"]:
            return 1.3  # Escape winter
        else:
            return 1.0
    
    return 1.0  # Default
