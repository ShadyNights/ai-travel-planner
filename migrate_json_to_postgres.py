"""Migrate existing JSON data to PostgreSQL."""

import json
from pathlib import Path
from src.database.db_manager import DatabaseManager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data():
    """Migrate all JSON data to PostgreSQL."""
    db = DatabaseManager()
    
    # Load JSON files
    itineraries_file = Path("data/complete_itineraries.json")
    
    if not itineraries_file.exists():
        logger.warning("No JSON data found to migrate")
        return
    
    with open(itineraries_file, 'r', encoding='utf-8') as f:
        itineraries_data = json.load(f)
    
    logger.info(f"📦 Found {len(itineraries_data)} itineraries to migrate")
    
    migrated = 0
    for itin in itineraries_data:
        try:
            # Create trip
            trip_id = db.create_trip(
                destination=itin['city'],
                interests=itin.get('interests', ['Everything']),
                duration=itin.get('trip_days', 1),
                budget_level=itin.get('budget', 'Moderate'),
                travel_style=itin.get('travel_style', ['Solo']),
                include_food=itin.get('include_food', True),
                include_transport=itin.get('include_transport', True)
            )
            
            # Create itinerary
            itin_id = db.create_itinerary(
                trip_id=trip_id,
                itinerary_text=itin.get('full_itinerary', ''),
                word_count=itin.get('word_count', 0)
            )
            
            # Add rating if exists
            rating = itin.get('rating')
            if rating and rating > 0:
                db.rate_itinerary(
                    itinerary_id=itin_id,
                    rating=rating,
                    comments=itin.get('feedback_comments', '')
                )
            
            migrated += 1
            logger.info(f"✅ Migrated itinerary {migrated}/{len(itineraries_data)}")
            
        except Exception as e:
            logger.error(f"❌ Migration error: {e}")
    
    logger.info(f"🎉 Migration complete! Migrated {migrated} itineraries")
    
    # Backup old data
    backup_file = itineraries_file.with_suffix('.json.backup')
    itineraries_file.rename(backup_file)
    logger.info(f"📁 Backed up original data to {backup_file}")

if __name__ == "__main__":
    migrate_data()
