"""Dual Storage Manager - Stores data in both PostgreSQL AND JSON simultaneously."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from src.database.db_manager import DatabaseManager
    POSTGRES_AVAILABLE = True
except:
    POSTGRES_AVAILABLE = False

class DualStorageManager:
    """Production-level dual storage: PostgreSQL + JSON backup."""
    
    def __init__(self):
        """Initialize both storage systems."""
        self.use_postgres = POSTGRES_AVAILABLE and os.getenv("USE_POSTGRES", "true").lower() == "true"
        self.db_manager = None
        
        # JSON storage paths
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.trips_file = self.data_dir / "trips.json"
        self.itineraries_file = self.data_dir / "itineraries.json"
        self.training_file = self.data_dir / "training_data.json"
        
        # Initialize PostgreSQL if available
        if self.use_postgres:
            try:
                self.db_manager = DatabaseManager()
                logger.info("✅ Dual storage initialized: PostgreSQL + JSON")
            except Exception as e:
                logger.warning(f"⚠️ PostgreSQL unavailable, using JSON only: {e}")
                self.use_postgres = False
        else:
            logger.info("✅ Using JSON storage only")
        
        # Initialize JSON files
        self._init_json_files()
    
    def _init_json_files(self):
        """Initialize JSON storage files."""
        for file in [self.trips_file, self.itineraries_file, self.training_file]:
            if not file.exists():
                file.write_text("[]", encoding='utf-8')
    
    def _load_json(self, file: Path) -> List[Dict]:
        """Load data from JSON file."""
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_json(self, file: Path, data: List[Dict]):
        """Save data to JSON file."""
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
    
    def create_trip(self, destination: str, interests: List[str], duration: int, 
                    budget_level: str, travel_style: List[str], 
                    include_food: bool = True, include_transport: bool = True) -> int:
        """Store trip in BOTH PostgreSQL AND JSON."""
        
        trip_data = {
            "destination": destination,
            "interests": interests,
            "duration": duration,
            "budget_level": budget_level,
            "travel_style": travel_style,
            "include_food": include_food,
            "include_transport": include_transport,
            "created_at": datetime.now().isoformat()
        }
        
        trip_id = None
        
        # Store in PostgreSQL
        if self.use_postgres and self.db_manager:
            try:
                trip_id = self.db_manager.create_trip(
                    destination, interests, duration, budget_level,
                    travel_style, include_food, include_transport
                )
                logger.info(f"✅ Trip #{trip_id} stored in PostgreSQL")
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}")
        
        # ALWAYS store in JSON (backup)
        trips = self._load_json(self.trips_file)
        if trip_id is None:
            trip_id = len(trips) + 1
        
        trip_data["id"] = trip_id
        trips.append(trip_data)
        self._save_json(self.trips_file, trips)
        logger.info(f"✅ Trip #{trip_id} backed up to JSON")
        
        return trip_id
    
    def create_itinerary(self, trip_id: int, itinerary_text: str, 
                         word_count: int) -> int:
        """Store itinerary in BOTH PostgreSQL AND JSON."""
        
        itin_data = {
            "trip_id": trip_id,
            "itinerary_text": itinerary_text,
            "word_count": word_count,
            "character_count": len(itinerary_text),
            "created_at": datetime.now().isoformat()
        }
        
        itin_id = None
        
        # Store in PostgreSQL
        if self.use_postgres and self.db_manager:
            try:
                itin_id = self.db_manager.create_itinerary(trip_id, itinerary_text, word_count)
                logger.info(f"✅ Itinerary #{itin_id} stored in PostgreSQL")
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}")
        
        # ALWAYS store in JSON (backup)
        itineraries = self._load_json(self.itineraries_file)
        if itin_id is None:
            itin_id = len(itineraries) + 1
        
        itin_data["id"] = itin_id
        itineraries.append(itin_data)
        self._save_json(self.itineraries_file, itineraries)
        logger.info(f"✅ Itinerary #{itin_id} backed up to JSON")
        
        return itin_id
    
    def rate_itinerary(self, itinerary_id: int, rating: int, comments: str = ""):
        """Rate itinerary in BOTH storages."""
        
        # Update PostgreSQL
        if self.use_postgres and self.db_manager:
            try:
                self.db_manager.rate_itinerary(itinerary_id, rating, comments)
                logger.info(f"✅ Rating stored in PostgreSQL")
            except Exception as e:
                logger.error(f"PostgreSQL error: {e}")
        
        # Update JSON
        itineraries = self._load_json(self.itineraries_file)
        for itin in itineraries:
            if itin.get("id") == itinerary_id:
                itin["rating"] = rating
                itin["feedback_comments"] = comments
                itin["rated_at"] = datetime.now().isoformat()
                break
        
        self._save_json(self.itineraries_file, itineraries)
        logger.info(f"✅ Rating backed up to JSON")
    
    def get_statistics(self) -> Dict:
        """Get stats from primary storage (PostgreSQL if available, else JSON)."""
        if self.use_postgres and self.db_manager:
            try:
                return self.db_manager.get_statistics()
            except:
                pass
        
        # Fallback to JSON
        trips = self._load_json(self.trips_file)
        itineraries = self._load_json(self.itineraries_file)
        rated = [i for i in itineraries if i.get("rating")]
        
        return {
            "total_trips": len(trips),
            "total_itineraries": len(itineraries),
            "total_ratings": len(rated),
            "avg_rating": sum(i["rating"] for i in rated) / len(rated) if rated else 0
        }
