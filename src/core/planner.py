"""
Enhanced TravelPlanner with trip_days and budget support.
"""

import os
from groq import Groq
from typing import Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ✅ FIX: Model name as constant
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 8000


class TravelPlanner:
    """Travel planner with proper trip_days and budget handling."""
    
    def __init__(
        self, 
        city: str, 
        interests: list, 
        trip_days: int = 1, 
        budget: str = "Moderate"
    ):
        """
        Initialize TravelPlanner.
        
        Args:
            city: Destination city
            interests: List of interests
            trip_days: Number of days for the trip (CRITICAL!)
            budget: Budget level (Budget/Moderate/Luxury)
        """
        self.city = city
        self.interests = interests if isinstance(interests, list) else [interests]
        
        # ✅ FIX: Validate trip_days range
        self.trip_days = max(1, min(trip_days, 30))
        if trip_days != self.trip_days:
            logger.warning(f"Trip days adjusted from {trip_days} to {self.trip_days}")
        
        self.budget = budget
        self.client = self._initialize_client()
        
        logger.info(
            f"Initialized TravelPlanner for {city=}, {trip_days=}, {budget=}, "
            f"interests={self.interests[:3]}"
        )
    
    def _initialize_client(self) -> Groq:
        """
        Initialize Groq client.
        
        Returns:
            Groq: Configured Groq client
            
        Raises:
            ValueError: If GROQ_API_KEY not found
        """
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        return Groq(api_key=api_key)
    
    def create_itinerary(self) -> str:
        """
        Generate complete itinerary for ALL trip days.
        
        Returns:
            Complete itinerary as string
            
        Raises:
            RuntimeError: If generation fails
        """
        try:
            logger.info(
                f"Generating itinerary for city={self.city}, "
                f"trip_days={self.trip_days}, budget={self.budget}"
            )
            
            # Format interests
            interests_str = ", ".join(self.interests)
            
            # Build comprehensive prompt with ALL requirements
            prompt = f"""You are an expert travel planner. Create a COMPLETE {self.trip_days}-day itinerary for {self.city}.

CRITICAL REQUIREMENTS:
1. YOU MUST CREATE PLANS FOR ALL {self.trip_days} DAYS - DO NOT STOP AT 1-3 DAYS!
2. Budget Level: {self.budget} - Adjust ALL recommendations accordingly
3. Cover: {interests_str}

MANDATORY DAY STRUCTURE (ALL {self.trip_days} DAYS):
Generate detailed plans for Day 1, Day 2, Day 3, ... through Day {self.trip_days}

For EACH of the {self.trip_days} days, include:
- Morning activities (9 AM - 12 PM) with exact timing
- Afternoon activities (12 PM - 5 PM) with exact timing
- Evening activities (5 PM - 10 PM) with exact timing

For EVERY activity provide:
- Specific venue name, full address, phone number
- Exact time allocation (e.g., "9:00 AM - 11:00 AM (2 hours)")
- Precise costs in local currency (matching {self.budget} budget level)
- Transport directions with costs and time
- Insider tips and local secrets
- Opening hours and booking requirements
- Restaurant recommendations with {self.budget}-appropriate prices
- Weather alternatives
- Cultural tips

IMPORTANT REMINDERS:
- Generate COMPLETE itinerary for ALL {self.trip_days} days
- DO NOT truncate at Day 1-3
- Ensure each day has morning, afternoon, and evening plans
- Match {self.budget} budget level for ALL recommendations
- Provide 4-5 activities per day
- Include travel time between locations

Start with Day 1 and continue through Day {self.trip_days}.
Generate the complete {self.trip_days}-day itinerary now:"""
            
            # ✅ FIX: Use constant for model
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,  # Use constant
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=MAX_TOKENS,
                top_p=0.9,
                stream=False
            )
            
            itinerary = response.choices[0].message.content.strip()
            
            # ✅ FIX: Better validation for empty response
            if not itinerary or len(itinerary) < 100:
                raise RuntimeError(
                    f"Generated itinerary is too short or empty (length: {len(itinerary)})"
                )
            
            logger.info(
                f"Itinerary generated successfully - {len(itinerary)} chars, "
                f"{len(itinerary.split())} words"
            )
            
            # ✅ FIX: More robust validation
            days_found = sum(
                1 for i in range(1, self.trip_days + 1)
                if f"Day {i}" in itinerary or f"**Day {i}**" in itinerary
            )
            
            if days_found < self.trip_days:
                logger.warning(
                    f"⚠️  Only {days_found}/{self.trip_days} days found in itinerary - "
                    "may be truncated"
                )
            else:
                logger.info(f"✅ All {self.trip_days} days generated successfully!")
            
            return itinerary
            
        except Exception as e:
            logger.error(f"Error generating itinerary: {e}", exc_info=True)
            # ✅ FIX: Raise exception instead of returning error string
            raise RuntimeError(f"Unable to generate itinerary: {str(e)}") from e
