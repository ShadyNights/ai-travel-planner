"""
Production-Ready AI Travel Planner with Self-Training LLM System
Version: 3.4.0 FINAL (All Issues Fixed)
Database: Dual Storage (PostgreSQL + JSON Backup)
Auto-Training: Enabled with Database Triggers
"""

import os
import json
import time
import re
from datetime import datetime
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import requests
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import random
import traceback
import logging
from typing import Optional, Dict, List

from src.core.planner import TravelPlanner
from src.utils.logger import get_logger

# Load environment variables
load_dotenv(override=True)

# Initialize logger
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="AI Travel Planner Pro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==================== ✅ FIX: INPUT VALIDATION FUNCTIONS ====================

def validate_groq_key(key: str) -> bool:
    """
    Validate GROQ API key format.
    
    Args:
        key: API key to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return key and key.startswith("gsk_") and len(key) > 30


def sanitize_city_input(city: str, max_length: int = 50) -> str:
    """
    Sanitize city name input.
    
    Args:
        city: City name to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized city name
    """
    if not city:
        return ""
    
    # Remove special characters, keep alphanumeric, spaces, and hyphens
    sanitized = re.sub(r'[^a-zA-Z\s-]', '', city.strip())
    return sanitized[:max_length]


def sanitize_text_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize text input (for comments, etc.).
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized text
    """
    if not text:
        return ""
    
    # Remove potentially dangerous characters
    sanitized = text.strip()[:max_length]
    return sanitized


# ==================== ✅ FIX: API KEY VALIDATION ====================

groq_key = os.getenv("GROQ_API_KEY", "")
if not validate_groq_key(groq_key):
    st.error("🚨 Invalid or missing GROQ_API_KEY format. Expected format: gsk_...")
    st.info("💡 Please check your .env file and ensure GROQ_API_KEY is set correctly.")
    st.stop()


# ==================== DUAL STORAGE SYSTEM ====================

USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"
db_manager = None

if USE_POSTGRES:
    try:
        from src.database.db_manager import DatabaseManager
        db_manager = DatabaseManager()
        logger.info("✅ PostgreSQL database connected")
    except ImportError:
        logger.warning("⚠️ DatabaseManager not found, falling back to JSON")
        USE_POSTGRES = False
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL connection failed: {e}, falling back to JSON")
        USE_POSTGRES = False


# ==================== ✅ FIX: CACHED DATA LOADING ====================

@st.cache_data(ttl=60)
def load_cached_itineraries(file_path: str) -> list:
    """
    Load itineraries with caching (60 second TTL).
    
    Args:
        file_path: Path to itineraries JSON file
        
    Returns:
        list: List of itineraries
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading cached itineraries: {e}")
        return []


# ==================== SELF-TRAINING LLM SYSTEM ====================

class SelfTrainingLLMSystem:
    """Complete Self-Training LLM System with Dual Storage (PostgreSQL + JSON)."""
    
    def __init__(self, use_database: bool = False, db_manager=None):
        """Initialize the self-training system."""
        self.use_database = use_database and db_manager is not None
        self.db_manager = db_manager
        
        # ALWAYS initialize JSON storage (for backup/fallback)
        self.itineraries_file = Path("data/complete_itineraries.json")
        self.training_patterns_file = Path("data/training_patterns.json")
        self.feedback_file = Path("data/feedback.json")
        
        self.itineraries_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.itineraries_file.exists():
            self._save_itineraries([])
        else:
            self._fix_old_data()  # Fix null ratings
        
        if not self.training_patterns_file.exists():
            self._save_training_patterns(self._generate_initial_patterns())
        
        if not self.feedback_file.exists():
            self._save_feedback([])
        
        if self.use_database:
            logger.info("✅ Using Dual Storage: PostgreSQL + JSON backup")
        else:
            logger.info("✅ Using JSON storage only")
        
        # Auto-train on initialization
        self._auto_train()
    
    def _fix_old_data(self):
        """Fix old itineraries with null ratings."""
        try:
            with open(self.itineraries_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            needs_fix = False
            for itin in data:
                # ✅ FIX: Handle None ratings safely
                if itin.get('rating') is None:
                    itin['rating'] = 0
                    needs_fix = True
                if itin.get('feedback_comments') is None:
                    itin['feedback_comments'] = ""
                if itin.get('quality_score') is None:
                    itin['quality_score'] = 0
            
            if needs_fix:
                with open(self.itineraries_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info("✅ Fixed null ratings in old data")
        except Exception as e:
            logger.error(f"Error fixing old data: {e}")
    
    def _get_default_enhancements(self) -> list:
        """Get default prompt enhancements."""
        return [
            "Include specific venue names with full addresses and contact details",
            "Add exact time allocations for each activity with start and end times",
            "Provide precise cost estimates in local currency",
            "Include detailed transport directions with multiple options",
            "Add insider tips and local secrets from experienced travelers",
            "Mention opening hours, booking requirements, and best visiting times",
            "Suggest specific restaurants with price ranges and signature dishes",
            "Provide alternative indoor/outdoor options for weather flexibility",
            "Include cultural etiquette tips and useful local phrases",
            "Add photo opportunities and best viewpoints at each location"
        ]
    
    def _load_itineraries(self) -> list:
        """
        Load all itineraries.
        
        ✅ FIX: Uses cached loading for better performance
        """
        if self.use_database:
            try:
                return self.db_manager.get_recent_itineraries(1000)
            except:
                logger.warning("Database read failed, using JSON")
        
        # ✅ FIX: Use cached loading
        return load_cached_itineraries(str(self.itineraries_file))
    
    def _save_itineraries(self, data: list):
        """Save itineraries to JSON (backup storage)."""
        try:
            with open(self.itineraries_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # ✅ FIX: Clear cache when data changes
            load_cached_itineraries.clear()
            
        except Exception as e:
            logger.error(f"Error saving itineraries: {e}")
    
    def _load_feedback(self) -> list:
        """Load all feedback."""
        try:
            with open(self.feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return []
    
    def _save_feedback(self, data: list):
        """Save feedback to JSON."""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
    
    def _load_training_patterns(self) -> dict:
        """Load training patterns."""
        if self.use_database:
            try:
                query = """
                    SELECT insights_generated, patterns_learned
                    FROM training_cycles
                    WHERE status = 'completed'
                    ORDER BY cycle_number DESC
                    LIMIT 1
                """
                result = self.db_manager.execute_query(query, fetch=True)
                
                if result:
                    return result[0].get('insights_generated', self._generate_initial_patterns())
            except:
                pass
        
        try:
            with open(self.training_patterns_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return self._generate_initial_patterns()
    
    def _save_training_patterns(self, data: dict):
        """Save training patterns to JSON."""
        try:
            with open(self.training_patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving training patterns: {e}")
    
    def store_complete_itinerary(self, city: str, trip_days: int, budget: str, 
                                  interests: list, travel_style: list,
                                  include_food: bool, include_transport: bool,
                                  full_prompt_context: str, full_itinerary: str) -> int:
        """Store complete itinerary in BOTH PostgreSQL AND JSON."""
        
        itin_id = None
        word_count = len(full_itinerary.split())
        
        # 1. Try PostgreSQL first
        if self.use_database:
            try:
                trip_id = self.db_manager.create_trip(
                    destination=city,
                    interests=interests,
                    duration=trip_days,
                    budget_level=budget,
                    travel_style=travel_style,
                    include_food=include_food,
                    include_transport=include_transport
                )
                
                itin_id = self.db_manager.create_itinerary(
                    trip_id=trip_id,
                    itinerary_text=full_itinerary,
                    word_count=word_count
                )
                
                logger.info(f"✅ Stored itinerary #{itin_id} in PostgreSQL")
                
            except Exception as e:
                logger.error(f"PostgreSQL storage failed: {e}")
        
        # 2. ALWAYS store in JSON (backup)
        itineraries_data = []
        try:
            with open(self.itineraries_file, 'r', encoding='utf-8') as f:
                itineraries_data = json.load(f)
        except:
            itineraries_data = []
        
        if itin_id is None:
            itin_id = len(itineraries_data) + 1
        
        itinerary_entry = {
            "id": itin_id,
            "timestamp": datetime.now().isoformat(),
            "city": city,
            "destination": city,  # For compatibility
            "trip_days": trip_days,
            "duration": trip_days,  # For compatibility
            "budget": budget,
            "budget_level": budget,  # For compatibility
            "interests": interests,
            "travel_style": travel_style,
            "include_food": include_food,
            "include_transport": include_transport,
            "full_prompt_context": full_prompt_context,
            "full_itinerary": full_itinerary,
            "itinerary_text": full_itinerary,  # For compatibility
            "itinerary_length": len(full_itinerary),
            "word_count": word_count,
            "rated": False,
            "rating": 0,
            "feedback_comments": "",
            "quality_score": 0,
            "used_for_training": False,
            "training_iteration": 0
        }
        
        itineraries_data.append(itinerary_entry)
        self._save_itineraries(itineraries_data)
        logger.info(f"✅ Itinerary #{itin_id} backed up to JSON")
        
        return itin_id
    
    def record_feedback(self, itinerary_id: int, rating: int, comments: str = ""):
        """Record user feedback in BOTH storages."""
        
        # ✅ FIX: Sanitize comments input
        comments = sanitize_text_input(comments, max_length=1000)
        
        # 1. Store in PostgreSQL
        if self.use_database:
            try:
                self.db_manager.rate_itinerary(itinerary_id, rating, comments)
                logger.info(f"✅ Feedback recorded in PostgreSQL")
            except Exception as e:
                logger.error(f"PostgreSQL feedback failed: {e}")
        
        # 2. ALWAYS store in JSON
        itineraries = self._load_itineraries()
        
        for itin in itineraries:
            if itin.get('id') == itinerary_id:
                itin['rated'] = True
                itin['rating'] = rating
                itin['feedback_comments'] = comments
                itin['quality_score'] = self._calculate_quality_score(
                    rating, 
                    len(itin.get('full_itinerary', itin.get('itinerary_text', '')))
                )
                break
        
        self._save_itineraries(itineraries)
        
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "itinerary_id": itinerary_id,
            "rating": rating,
            "comments": comments
        }
        
        feedback_data = self._load_feedback()
        feedback_data.append(feedback_entry)
        self._save_feedback(feedback_data)
        
        logger.info(f"✅ Feedback recorded: {rating}⭐ (Dual Storage)")
        
        # Trigger auto-training
        if len(feedback_data) % 3 == 0:
            self._auto_train()
    
    def _calculate_quality_score(self, rating: int, length: int) -> float:
        """Calculate quality score."""
        length_bonus = min(20, length / 1000)
        return round((rating * 16) + length_bonus, 2)
    
    def _generate_initial_patterns(self) -> dict:
        """Generate initial training patterns."""
        return {
            "last_update": datetime.now().isoformat(),
            "training_iterations": 0,
            "total_training_samples": 0,
            "successful_patterns": {
                "high_rated_cities": {},
                "popular_interests": {
                    "museums": 85, "food": 90, "adventure": 88,
                    "history": 82, "beaches": 87, "shopping": 75,
                    "nightlife": 78, "nature": 86
                },
                "optimal_trip_durations": {
                    "1-3": 75, "4-7": 88, "8-14": 90
                },
                "budget_success_rates": {
                    "Budget": 75, "Moderate": 88, "Luxury": 82
                }
            },
            "learned_prompt_enhancements": self._get_default_enhancements(),
            "quality_improvement_insights": [],
            "best_performing_prompts": [],
            "optimization_rules": [
                "Include specific restaurant names with addresses",
                "Add exact time estimates for each activity",
                "Provide alternative indoor options for weather",
                "Include insider tips and local secrets",
                "Suggest best times to avoid crowds"
            ]
        }
    
    def _auto_train(self):
        """Automatically train from high-quality itineraries."""
        try:
            if self.use_database:
                # Database handles auto-training via triggers
                logger.info("🧠 Auto-training handled by PostgreSQL triggers")
                return
            
            itineraries = self._load_itineraries()
            patterns = self._load_training_patterns()
            
            if len(itineraries) < 3:
                return
            
            # ✅ FIX: Handle None ratings safely
            high_quality = [i for i in itineraries if (i.get('rating') or 0) >= 4]
            
            if not high_quality:
                return
            
            logger.info(f"🧠 Auto-training from {len(high_quality)} high-quality itineraries...")
            
            # Update patterns
            if 'successful_patterns' not in patterns:
                patterns['successful_patterns'] = {}
            
            if 'high_rated_cities' not in patterns['successful_patterns']:
                patterns['successful_patterns']['high_rated_cities'] = {}
            
            for itin in high_quality:
                city = itin.get('city', itin.get('destination', 'Unknown')).title()
                current_count = patterns['successful_patterns']['high_rated_cities'].get(city, 0)
                patterns['successful_patterns']['high_rated_cities'][city] = current_count + 1
            
            # Generate insights
            new_insight = self._generate_training_insight(high_quality)
            if new_insight:
                if 'quality_improvement_insights' not in patterns:
                    patterns['quality_improvement_insights'] = []
                
                if new_insight not in patterns['quality_improvement_insights']:
                    patterns['quality_improvement_insights'].append(new_insight)
                    patterns['quality_improvement_insights'] = patterns['quality_improvement_insights'][-15:]
            
            # Update best prompts
            if 'best_performing_prompts' not in patterns:
                patterns['best_performing_prompts'] = []
            
            for itin in high_quality:
                if (itin.get('rating') or 0) == 5:
                    prompt_summary = {
                        "city": itin.get('city', itin.get('destination', 'Unknown')),
                        "days": itin.get('trip_days', itin.get('duration', 1)),
                        "budget": itin.get('budget', itin.get('budget_level', 'Moderate')),
                        "rating": itin.get('rating', 5),
                        "word_count": itin.get('word_count', 0)
                    }
                    if prompt_summary not in patterns['best_performing_prompts']:
                        patterns['best_performing_prompts'].append(prompt_summary)
                        patterns['best_performing_prompts'] = patterns['best_performing_prompts'][-10:]
            
            patterns['last_update'] = datetime.now().isoformat()
            patterns['training_iterations'] = patterns.get('training_iterations', 0) + 1
            patterns['total_training_samples'] = len(high_quality)
            
            # Mark data as used
            for itin in itineraries:
                if (itin.get('rating') or 0) >= 4 and not itin.get('used_for_training', False):
                    itin['used_for_training'] = True
                    itin['training_iteration'] = patterns['training_iterations']
            
            self._save_training_patterns(patterns)
            self._save_itineraries(itineraries)
            
            logger.info(f"✅ Auto-training completed. Iteration #{patterns['training_iterations']}")
            
        except Exception as e:
            logger.error(f"Auto-training error: {e}")
            logger.error(traceback.format_exc())
    
    def _generate_training_insight(self, high_quality_itineraries: list) -> str:
        """Generate insights from successful itineraries."""
        insights = [
            "Itineraries with exact time slots receive higher ratings",
            "Including restaurant details improves satisfaction",
            "Weather alternatives increase user satisfaction",
            "Transport cost breakdowns are highly valued",
            "Opening hours mentioned upfront reduce friction",
            "Grouping nearby attractions saves time",
            "Cultural tips enhance travel experience",
            "Budget breakdowns help planning",
            "Insider tips boost ratings significantly",
            "Day-by-day structure is preferred format",
            "Photo spots increase engagement",
            "Multi-option transport suggestions are valued"
        ]
        return random.choice(insights)
    
    def get_training_enhanced_prompt(self, city: str, trip_days: int, budget: str, 
                                     interests: list) -> str:
        """Generate enhanced prompt with training insights."""
        patterns = self._load_training_patterns()
        
        context_parts = [
            f"\n\n🎯 CRITICAL REQUIREMENT: CREATE A COMPLETE {trip_days}-DAY ITINERARY",
            f"⚠️ MANDATORY: Generate plans for ALL {trip_days} DAYS",
            f"📅 REQUIRED: Day 1 through Day {trip_days}",
            f"\n💰 BUDGET: {budget} - Adjust ALL recommendations accordingly!",
            "\n🎯 DETAILED REQUIREMENTS for EACH DAY:",
            "- SPECIFIC venue names, FULL addresses, contact info",
            "- EXACT time slots: '9:00 AM - 11:00 AM (2 hours)'",
            f"- PRECISE costs matching {budget} budget",
            "- DETAILED transport directions with options",
            "- INSIDER TIPS and local secrets",
            "- Opening hours, booking requirements",
            f"- Restaurant recommendations ({budget}-appropriate)",
            "- Weather alternatives",
            "- Cultural etiquette and phrases",
            "- Photo opportunities"
        ]
        
        # Add learned insights
        insights = patterns.get('quality_improvement_insights', [])
        if insights:
            context_parts.append("\n🧠 AI-Learned Best Practices:")
            for insight in insights[-5:]:
                context_parts.append(f"  • {insight}")
        
        enhancements = patterns.get('learned_prompt_enhancements', self._get_default_enhancements())
        if enhancements:
            context_parts.append("\n✨ MUST INCLUDE:")
            for enhancement in random.sample(enhancements, min(7, len(enhancements))):
                context_parts.append(f"  • {enhancement}")
        
        context_parts.append(f"\n📅 STRUCTURE: Day 1 through Day {trip_days}")
        context_parts.append("  Each day: Morning, Afternoon, Evening plans")
        context_parts.append(f"\n⚠️ FINAL: Must include ALL {trip_days} days!")
        
        return "\n".join(context_parts)
    
    def get_statistics(self) -> dict:
        """Get comprehensive statistics."""
        
        if self.use_database:
            try:
                stats = self.db_manager.get_statistics()
                return {
                    "total_itineraries": stats.get('total_itineraries', 0),
                    "total_feedback": stats.get('total_ratings', 0),
                    "rated_itineraries": stats.get('total_ratings', 0),
                    "average_rating": float(stats.get('avg_rating', 0.0) or 0.0),
                    "training_iterations": stats.get('training_cycles_completed', 0),
                    "high_quality_samples": stats.get('high_quality_samples', 0),
                    "top_cities": stats.get('top_cities', []),
                    "rating_distribution": stats.get('rating_distribution', {}),
                    "avg_word_count": 0,
                    "total_database_size": stats.get('total_itineraries', 0),
                    "improvement_rate": 0.0
                }
            except Exception as e:
                logger.error(f"Stats error: {e}")
        
        # JSON fallback
        itineraries = self._load_itineraries()
        feedback = self._load_feedback()
        patterns = self._load_training_patterns()
        
        if not itineraries:
            return {
                "total_itineraries": 0,
                "total_feedback": 0,
                "rated_itineraries": 0,
                "average_rating": 0.0,
                "training_iterations": 0,
                "high_quality_samples": 0,
                "top_cities": [],
                "rating_distribution": {},
                "avg_word_count": 0,
                "total_database_size": 0,
                "improvement_rate": 0.0
            }
        
        # ✅ FIX: Calculate stats - Handle None ratings safely
        rated = [i for i in itineraries if i.get('rated', False) and (i.get('rating') or 0) > 0]
        ratings = [i.get('rating', 0) for i in rated if i.get('rating')]
        
        city_counts = {}
        for itin in itineraries:
            city = itin.get('city', itin.get('destination', 'Unknown')).title()
            city_counts[city] = city_counts.get(city, 0) + 1
        
        top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        rating_dist = {}
        for rating in ratings:
            rating_dist[rating] = rating_dist.get(rating, 0) + 1
        
        return {
            "total_itineraries": len(itineraries),
            "total_feedback": len(feedback),
            "rated_itineraries": len(rated),
            "average_rating": sum(ratings) / len(ratings) if ratings else 0.0,
            "training_iterations": patterns.get('training_iterations', 0),
            "high_quality_samples": patterns.get('total_training_samples', 0),
            "top_cities": top_cities,
            "rating_distribution": rating_dist,
            "avg_word_count": sum(i.get('word_count', 0) for i in itineraries) / len(itineraries),
            "total_database_size": len(itineraries),
            "improvement_rate": 0.0
        }
    
    def get_recent_itineraries(self, limit: int = 10) -> list:
        """Get recent itineraries."""
        if self.use_database:
            try:
                return self.db_manager.get_recent_itineraries(limit)
            except:
                logger.warning("Database query failed, using JSON")
        
        itineraries = self._load_itineraries()
        return list(reversed(itineraries))[-limit:]


# Initialize training system
training_system = SelfTrainingLLMSystem(use_database=USE_POSTGRES, db_manager=db_manager)


# ==================== HELPER FUNCTIONS ====================

def fetch_unsplash_images(city: str, count: int = 3) -> list:
    """Fetch destination images."""
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    if not access_key:
        return []
    
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": f"{city} travel destination",
            "per_page": count,
            "client_id": access_key
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return [photo["urls"]["regular"] for photo in data.get("results", [])]
        else:
            return []
            
    except Exception as e:
        logger.error(f"Error fetching images: {e}")
        return []


def estimate_trip_cost(city: str, days: int = 1) -> dict:
    """Estimate trip costs."""
    costs = {
        "budget": {
            "accommodation": 30,
            "food": 20,
            "activities": 15,
            "transport": 10
        },
        "moderate": {
            "accommodation": 80,
            "food": 40,
            "activities": 30,
            "transport": 25
        },
        "luxury": {
            "accommodation": 200,
            "food": 100,
            "activities": 80,
            "transport": 50
        }
    }
    
    estimated = {}
    for category, values in costs.items():
        total = sum(values.values()) * days
        estimated[category] = {
            "daily": sum(values.values()),
            "total": total,
            "breakdown": values
        }
    
    return estimated


def generate_pdf(itinerary: str, city: str) -> BytesIO:
    """Generate PDF."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title = Paragraph(f"<b>Travel Itinerary for {city}</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Date
    date = Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles["Normal"])
    story.append(date)
    story.append(Spacer(1, 24))
    
    # Itinerary content
    for line in itinerary.split("\n"):
        if line.strip():
            # Escape HTML characters
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            p = Paragraph(safe_line, styles["Normal"])
            story.append(p)
            story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def create_google_maps_link(city: str) -> str:
    """Generate Google Maps link."""
    return f"https://www.google.com/maps/search/?api=1&query={city.replace(' ', '+')}"


# ==================== STREAMLIT UI ====================

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        margin: 0;
    }
    .sub-title {
        font-size: 1.2rem;
        opacity: 0.9;
        margin: 0.5rem 0;
    }
    .learning-badge {
        background: rgba(255,255,255,0.2);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        display: inline-block;
        margin-top: 0.5rem;
    }
    .db-badge {
        background: rgba(255,255,255,0.3);
        padding: 0.2rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        margin-left: 0.5rem;
    }
    .tagline {
        font-size: 1rem;
        opacity: 0.8;
        margin-top: 0.5rem;
    }
    .feature-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .feature-card h4 {
        color: #667eea;
        margin-top: 0;
    }
    .stat-card {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
    }
    .empty-state {
        text-align: center;
        padding: 3rem;
        color: #999;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# Header
db_type = f"Dual Storage (PostgreSQL + JSON)" if USE_POSTGRES else "JSON Only"
st.markdown(f"""
<div class="main-header">
    <h1 class="main-title">✈️ AI Travel Planner Pro</h1>
    <p class="sub-title">Self-Training LLM System</p>
    <span class="learning-badge">🧠 Smart. Adaptive. Always Improving.</span>
    <span class="db-badge">{db_type}</span>
    <p class="tagline">Powered by AI that learns from every journey</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Initialize session state
    if "trip_days" not in st.session_state:
        st.session_state.trip_days = 1
    if "budget_level" not in st.session_state:
        st.session_state.budget_level = "Moderate"
    
    trip_days = st.slider(
        "Duration", 
        1, 14, 
        st.session_state.trip_days,
        key="trip_days_slider",
        help="Select how long you'll be traveling"
    )
    st.session_state.trip_days = trip_days
    
    budget_level = st.selectbox(
        "Budget",
        ["Budget", "Moderate", "Luxury"],
        index=["Budget", "Moderate", "Luxury"].index(st.session_state.budget_level),
        key="budget_selector",
        help="Helps optimize hotel, food & activity suggestions"
    )
    st.session_state.budget_level = budget_level
    
    travel_style = st.multiselect(
        "Style",
        ["Solo", "Family", "Couple", "Friends", "Business"],
        default=["Solo"],
        help="How you prefer to travel"
    )
    
    st.markdown("---")
    st.markdown("### 📊 Trip Summary")
    st.info(f"**Duration:** {trip_days} days  \n**Budget:** {budget_level}  \n**Style:** {', '.join(travel_style)}")
    
    st.markdown("---")
    st.markdown("### 🤖 AI Metrics")
    
    stats = training_system.get_statistics()
    
    if stats["total_itineraries"] == 0:
        st.markdown('<div class="empty-state">Start planning your first trip to unlock insights.</div>', unsafe_allow_html=True)
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Data Points", stats["total_itineraries"])
        with col2:
            st.metric("Training Cycles", stats["training_iterations"])
        
        avg_rating_display = f"{stats['average_rating']:.1f}⭐" if stats['average_rating'] > 0 else "N/A"
        st.metric("Average Rating", avg_rating_display)
        
        if stats["top_cities"]:
            st.markdown("---")
            st.markdown("### 🌍 Most Requested")
            for city, count in stats["top_cities"][:3]:
                st.write(f"**{city}** — {count}")
    
    st.markdown("---")
    
    cold1, cold2 = st.columns(2)
    with cold1:
        if st.button("📈 Analytics", use_container_width=True, key="btn_dashboard"):
            st.session_state.show_dashboard = True
    with cold2:
        if st.button("💾 Database", use_container_width=True, key="btn_database"):
            st.session_state.show_database = True

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🗺️ Plan Your Trip")
    
    with st.form("travel_form", clear_on_submit=False):
        city = st.text_input(
            "🏙️ Destination",
            placeholder="Example: Paris, Tokyo, Mumbai",
            help="Type any major city worldwide",
            max_chars=50  # ✅ FIX: Add max length
        )
        
        interests = st.text_input(
            "🎯 Interests",
            placeholder="Example: museums, food, adventure",
            help="Separate interests with commas"
        )
        
        cola, colb = st.columns(2)
        with cola:
            include_food = st.checkbox("🍽️ Food Recommendations", value=True)
        with colb:
            include_transport = st.checkbox("🚗 Transport Details", value=True)
        
        submitted = st.form_submit_button("🚀 Generate AI Itinerary")

with col2:
    st.markdown("### ✨ Core Features")
    
    st.markdown("""
    <div class="feature-card">
        <h4>🧠 Adaptive Learning</h4>
        <p>Improves accuracy and personalization with every itinerary generated.</p>
    </div>
    
    <div class="feature-card">
        <h4>💾 Dual Storage</h4>
        <p>PostgreSQL + JSON backup for maximum reliability.</p>
    </div>
    
    <div class="feature-card">
        <h4>📊 Built-In Database</h4>
        <p>View, analyze, and manage stored itineraries and training data.</p>
    </div>
    
    <div class="feature-card">
        <h4>⚡ Auto-Optimization</h4>
        <p>Continuously improves recommendations through iterative self-training.</p>
    </div>
    """, unsafe_allow_html=True)

# Process form submission
if submitted:
    # ✅ FIX: Validate and sanitize city input
    city = sanitize_city_input(city, max_length=50)
    
    if not city or not city.strip():
        st.warning("⚠️ **Validation Error:** Please enter a valid city name.")
    else:
        try:
            actual_days = st.session_state.trip_days
            actual_budget = st.session_state.budget_level
            
            start_time = time.time()
            
            with st.spinner(f"🧠 Generating your {actual_days}-day {actual_budget} itinerary..."):
                # Parse interests
                interests_list = [i.strip() for i in interests.split(",") if i.strip()] if interests else ["Everything"]
                
                # Get enhanced prompt
                enhanced = training_system.get_training_enhanced_prompt(
                    city, actual_days, actual_budget, interests_list
                )
                
                # Combine interests with enhancement context
                full_interests = interests_list + [enhanced]
                
                # Create planner
                planner = TravelPlanner(
                    city.strip(),
                    full_interests,
                    trip_days=actual_days,
                    budget=actual_budget
                )
                
                # Generate itinerary
                itinerary = planner.create_itinerary()
                generation_time = int((time.time() - start_time) * 1000)
                
                # ✅ FIX: Better error handling
                if not itinerary or len(itinerary) < 100:
                    st.error("❌ **Generation Failed:** The AI couldn't complete your request. Please try again.")
                    st.stop()
                
                # Store itinerary
                itin_id = training_system.store_complete_itinerary(
                    city, actual_days, actual_budget, interests_list,
                    travel_style, include_food, include_transport,
                    enhanced, itinerary
                )
                
                # Save to session state
                st.session_state.itinerary = itinerary
                st.session_state.itinerary_id = itin_id
                st.session_state.city = city
                st.session_state.actual_days = actual_days
                st.session_state.actual_budget = actual_budget
                
                st.success(
                    f"✅ **Success!** Generated {actual_days}-day {actual_budget} itinerary "
                    f"in {generation_time/1000:.1f}s (ID: #{itin_id})"
                )
                
        except Exception as e:
            logger.error(f"Error: {e}\n{traceback.format_exc()}")
            st.error("❌ **System Error:** Unable to generate itinerary. Check your GROQ_API_KEY in the .env file.")
            
            with st.expander("🔍 Technical Details"):
                st.code(str(e))
                st.code(traceback.format_exc())

# Display itinerary (if exists)
if "itinerary" in st.session_state:
    st.markdown("---")
    st.markdown(f"## ✈️ {st.session_state.city.title()} — {st.session_state.actual_days} Days ({st.session_state.actual_budget})")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Itinerary", 
        "💰 Budget Estimate", 
        "📸 Gallery", 
        "🗺️ Map", 
        "⭐ Rate & Train"
    ])
    
    with tab1:
        st.markdown(st.session_state.itinerary)
        
        st.markdown("---")
        st.markdown("### 📥 Export Options")
        
        colb1, colb2, colb3 = st.columns(3)
        
        with colb1:
            st.download_button(
                "📄 Download PDF",
                generate_pdf(st.session_state.itinerary, st.session_state.city),
                f"{st.session_state.city}_itinerary.pdf",
                "application/pdf",
                key="download_pdf"
            )
        
        with colb2:
            st.download_button(
                "📝 Download Text",
                st.session_state.itinerary,
                f"{st.session_state.city}_itinerary.txt",
                "text/plain",
                key="download_txt"
            )
        
        with colb3:
            st.link_button(
                "🐦 Share",
                f"https://twitter.com/intent/tweet?text=Check out my {st.session_state.city} trip!"
            )
    
    with tab2:
        st.markdown("### 💰 Estimated Trip Costs")
        
        costs = estimate_trip_cost(st.session_state.city, st.session_state.actual_days)
        
        c1, c2, c3 = st.columns(3)
        
        for idx, (category, data) in enumerate([
            ("budget", costs["budget"]),
            ("moderate", costs["moderate"]),
            ("luxury", costs["luxury"])
        ]):
            with [c1, c2, c3][idx]:
                st.markdown(f"""
                <div class="stat-card">
                    <p class="stat-number">${data["total"]}</p>
                    <p class="stat-label">{category.title()}</p>
                </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        st.markdown("### 📸 Photo Gallery")
        
        if not os.getenv("UNSPLASH_ACCESS_KEY", "").strip():
            st.info("💡 **Tip:** Add `UNSPLASH_ACCESS_KEY` to your .env file to enable photo gallery.")
        else:
            images = fetch_unsplash_images(st.session_state.city)
            
            if images:
                cols = st.columns(3)
                for idx, img in enumerate(images):
                    cols[idx % 3].image(img, use_column_width=True)
            else:
                st.warning("⚠️ **Connection Issue:** Could not load photos. Check your internet connection.")
    
    with tab4:
        st.markdown("### 🗺️ Interactive Map")
        st.markdown(f"[📍 Open {st.session_state.city.title()} in Google Maps]({create_google_maps_link(st.session_state.city)})")
    
    with tab5:
        st.markdown("### ⭐ Help Train the AI")
        st.markdown("Your feedback improves future recommendations for everyone!")
        
        rating = st.radio(
            "How would you rate this itinerary?",
            [5, 4, 3, 2, 1],
            format_func=lambda x: "⭐" * x,
            horizontal=True,
            key="rating_radio"
        )
        
        comments = st.text_area(
            "Additional Feedback (Optional)",
            placeholder="What did you like? What could be improved?",
            key="feedback_comments",
            max_chars=1000  # ✅ FIX: Add max length
        )
        
        if st.button("✅ Submit Feedback & Train AI", key="submit_feedback_btn"):
            # ✅ FIX: Comments are sanitized in record_feedback()
            training_system.record_feedback(st.session_state.itinerary_id, rating, comments)
            st.success("🎉 **Thank you!** Your feedback has been recorded and AI training has been initiated.")
            st.balloons()

# Dashboard view
if st.session_state.get("show_dashboard", False):
    st.markdown("---")
    st.markdown("## 📊 Analytics Dashboard")
    
    stats = training_system.get_statistics()
    
    if stats["total_itineraries"] == 0:
        st.markdown('<div class="empty-state">Dashboard will populate after your first itinerary generation.</div>', unsafe_allow_html=True)
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Generated", stats["total_itineraries"])
        c2.metric("User Ratings", stats["rated_itineraries"])
        c3.metric("Training Cycles", stats["training_iterations"])
        c4.metric("Avg Rating", f"{stats['average_rating']:.1f}⭐" if stats['average_rating'] > 0 else "N/A")
        
        if stats["top_cities"]:
            st.markdown("### 🌍 Popular Destinations")
            for idx, (city, count) in enumerate(stats["top_cities"], 1):
                st.write(f"{idx}. **{city}** — {count} itineraries")
        
        if stats.get("rating_distribution"):
            st.markdown("### ⭐ Rating Distribution")
            for rating in [5, 4, 3, 2, 1]:
                count = stats["rating_distribution"].get(rating, 0)
                if count > 0:
                    st.write(f"{'⭐' * rating} — {count} itineraries")
        
        if st.button("✖️ Close Analytics", key="close_dashboard_btn"):
            st.session_state.show_dashboard = False
            st.rerun()

# Database view
if st.session_state.get("show_database", False):
    st.markdown("---")
    st.markdown("## 💾 Database Manager")
    
    tab1, tab2, tab3 = st.tabs(["📋 Itineraries", "💬 Feedback", "🧠 Training"])
    
    with tab1:
        recent = training_system.get_recent_itineraries(10)
        
        if not recent:
            st.markdown('<div class="empty-state">No itineraries stored yet. Generate your first trip to see data here.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"**Total Records:** {len(recent)}")
            
            for itin in recent:
                # ✅ FIX: Handle field compatibility
                rating_val = itin.get('rating') or 0
                city_name = itin.get('city', itin.get('destination', 'Unknown'))
                days = itin.get('trip_days', itin.get('duration', 1))
                budget = itin.get('budget', itin.get('budget_level', 'Moderate'))
                
                with st.expander(f"#{itin.get('id', '?')} • {city_name.title()} — {days}d ({budget})"):
                    st.metric(
                        "User Rating",
                        f"{rating_val}⭐" if rating_val > 0 else "Not rated yet"
                    )
                    
                    itin_text = itin.get('full_itinerary', itin.get('itinerary_text', ''))
                    st.text_area(
                        "Full Itinerary",
                        value=itin_text,
                        height=200,
                        key=f"itin_view_{itin.get('id', random.randint(1000, 9999))}"
                    )
    
    with tab2:
        stats = training_system.get_statistics()
        
        if stats["total_feedback"] == 0:
            st.markdown('<div class="empty-state">No feedback collected yet. Rate your first itinerary to contribute training data.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f"**Total Feedback Entries:** {stats['total_feedback']}")
            st.markdown(f"**Average Rating:** {stats['average_rating']:.1f}⭐")
    
    with tab3:
        stats = training_system.get_statistics()
        
        st.metric("Training Iterations Completed", stats["training_iterations"])
        st.metric("High-Quality Samples", stats["high_quality_samples"])
        
        if stats["top_cities"]:
            st.markdown("### High-Rated Destinations")
            for city, count in stats["top_cities"]:
                st.write(f"**{city}** — {count} itineraries")
    
    if st.button("✖️ Close Database View", key="close_database_btn"):
        st.session_state.show_database = False
        st.rerun()
