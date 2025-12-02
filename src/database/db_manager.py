"""
Database Manager for PostgreSQL Integration.
Production-ready with Cloud Database Support (Neon, Supabase, etc.)
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from typing import Optional, Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Production-ready PostgreSQL database manager with cloud support."""
    
    def __init__(self):
        """Initialize database connection pool."""
        self.pool = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """
        Create connection pool with cloud database support.
        
        Supports both:
        - Cloud databases (DATABASE_URL) - Neon, Supabase, etc.
        - Local PostgreSQL (DB_HOST, DB_PASSWORD, etc.)
        
        Raises:
            ValueError: If database credentials are not set
            Exception: If connection fails
        """
        try:
            # ✅ PRIORITY 1: Check for DATABASE_URL (cloud deployment)
            database_url = os.getenv("DATABASE_URL", "")
            
            if database_url:
                # Parse DATABASE_URL for cloud hosting (Neon, Supabase, etc.)
                logger.info("🌍 Connecting to cloud database...")
                import urllib.parse as urlparse
                url = urlparse.urlparse(database_url)
                
                # ✅ FIX: Remove options parameter for Neon compatibility
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=url.hostname,
                    port=url.port or 5432,
                    database=url.path[1:],  # Remove leading /
                    user=url.username,
                    password=url.password,
                    sslmode='require',  # Required for cloud databases
                    connect_timeout=10
                    # ❌ Removed: options parameter (not supported by Neon pooler)
                )
                
                logger.info(f"✅ Cloud database connected: {url.hostname}")
                
            else:
                # ✅ FALLBACK: Local PostgreSQL (original code)
                logger.info("🏠 Connecting to local PostgreSQL...")
                
                db_password = os.getenv("DB_PASSWORD", "")
                if not db_password:
                    raise ValueError(
                        "DB_PASSWORD environment variable is required. "
                        "Please set it in your .env file."
                    )
                
                self.pool = SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=os.getenv("DB_HOST", "localhost"),
                    port=os.getenv("DB_PORT", "5432"),
                    database=os.getenv("DB_NAME", "travel_planner"),
                    user=os.getenv("DB_USER", "postgres"),
                    password=db_password,
                    connect_timeout=10,  # Connection timeout in seconds
                    options="-c statement_timeout=30000"  # Query timeout (30s) - OK for local
                )
                
                logger.info("✅ Local database connected")
            
        except ValueError as e:
            # Re-raise validation errors
            logger.error(f"❌ Database configuration error: {e}")
            raise
            
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            
            # ✅ FIX: Cleanup on error
            if self.pool:
                try:
                    self.pool.closeall()
                except:
                    pass
                self.pool = None
            
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Get database connection from pool with proper error handling.
        Sets statement timeout after connection for cloud databases.
        
        Yields:
            Connection: Database connection
        """
        conn = None
        try:
            conn = self.pool.getconn()
            
            # ✅ Set statement timeout after connection (for cloud databases)
            with conn.cursor() as cursor:
                cursor.execute("SET statement_timeout = '30s'")
            
            yield conn
            conn.commit()
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
            
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def execute_query(
        self, 
        query: str, 
        params: tuple = None, 
        fetch: bool = False
    ) -> Optional[List[Dict]]:
        """
        Execute SQL query with proper error handling.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, None otherwise
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                
                if fetch:
                    return cursor.fetchall()
                
                return None
    
    def create_trip(
        self,
        destination: str,
        interests: List[str],
        duration: int,
        budget_level: str,
        travel_style: List[str],
        include_food: bool = True,
        include_transport: bool = True,
        user_id: int = 1
    ) -> int:
        """
        Create new trip record.
        
        Args:
            destination: Destination city
            interests: List of interests
            duration: Trip duration in days
            budget_level: Budget level (Budget/Moderate/Luxury)
            travel_style: Travel style preferences
            include_food: Include food recommendations
            include_transport: Include transport details
            user_id: User ID (default: 1)
            
        Returns:
            int: Created trip ID
        """
        query = """
            INSERT INTO trips (
                user_id, destination, interests, duration, 
                budget_level, travel_style, include_food, include_transport
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.execute_query(
            query,
            (
                user_id, destination, interests, duration,
                budget_level, travel_style, include_food, include_transport
            ),
            fetch=True
        )
        
        trip_id = result[0]["id"]
        logger.info(f"✅ Created trip #{trip_id} for {destination}")
        
        return trip_id
    
    def create_itinerary(
        self,
        trip_id: int,
        itinerary_text: str,
        word_count: int,
        generation_time_ms: int = 0
    ) -> int:
        """
        Create new itinerary record.
        
        Args:
            trip_id: Associated trip ID
            itinerary_text: Full itinerary text
            word_count: Number of words
            generation_time_ms: Generation time in milliseconds
            
        Returns:
            int: Created itinerary ID
        """
        query = """
            INSERT INTO itineraries (
                trip_id, itinerary_text, word_count, 
                character_count, generation_time_ms
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        
        result = self.execute_query(
            query,
            (trip_id, itinerary_text, word_count, len(itinerary_text), generation_time_ms),
            fetch=True
        )
        
        itin_id = result[0]["id"]
        logger.info(f"✅ Created itinerary #{itin_id}")
        
        return itin_id
    
    def rate_itinerary(self, itinerary_id: int, rating: int, comments: str):
        """
        Add rating to itinerary.
        
        Args:
            itinerary_id: Itinerary ID to rate
            rating: Rating (1-5)
            comments: Feedback comments
        """
        query = """
            UPDATE itineraries 
            SET rating = %s,
                feedback_comments = %s,
                rated_at = NOW(),
                quality_score = (%s * 16.0) + (character_count / 1000.0)
            WHERE id = %s
        """
        
        self.execute_query(query, (rating, comments, rating, itinerary_id))
        logger.info(f"✅ Rated itinerary #{itinerary_id}: {rating}⭐")
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive system statistics.
        
        Returns:
            Dict: System statistics
        """
        query = """
            SELECT 
                total_data,
                total_trips,
                total_itineraries,
                total_ratings,
                training_cycles_completed,
                avg_rating,
                avg_quality_score,
                high_quality_samples
            FROM system_metrics
            WHERE id = 1
        """
        
        result = self.execute_query(query, fetch=True)
        
        if result:
            stats = dict(result[0])
            
            # Get top cities
            city_query = """
                SELECT destination, COUNT(*) as count
                FROM trips
                GROUP BY destination
                ORDER BY count DESC
                LIMIT 5
            """
            cities = self.execute_query(city_query, fetch=True)
            stats["top_cities"] = [(c["destination"], c["count"]) for c in cities]
            
            # Get rating distribution
            rating_query = """
                SELECT rating, COUNT(*) as count
                FROM itineraries
                WHERE rating IS NOT NULL
                GROUP BY rating
                ORDER BY rating DESC
            """
            ratings = self.execute_query(rating_query, fetch=True)
            stats["rating_distribution"] = {r["rating"]: r["count"] for r in ratings}
            
            return stats
        
        return {}
    
    def get_recent_itineraries(self, limit: int = 10) -> List[Dict]:
        """
        Get recent itineraries with trip details.
        
        Args:
            limit: Number of itineraries to return
            
        Returns:
            List of itinerary dictionaries
        """
        query = """
            SELECT 
                i.id,
                i.itinerary_text,
                i.rating,
                i.feedback_comments,
                i.created_at,
                t.destination,
                t.duration,
                t.budget_level
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            ORDER BY i.created_at DESC
            LIMIT %s
        """
        
        return self.execute_query(query, (limit,), fetch=True)
    
    def close(self):
        """Close database connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connections closed")
    
    def __del__(self):
        """✅ FIX: Ensure cleanup on deletion."""
        self.close()
