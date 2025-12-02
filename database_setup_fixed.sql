-- ==================== SIMPLIFIED DATABASE SCHEMA ====================
-- Production-Ready Self-Training LLM Travel Planner
-- Version: 1.0.1 (Without Vector Extension)

-- ==================== USERS TABLE ====================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    username TEXT,
    password_hash TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ==================== TRIPS TABLE ====================
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    destination TEXT NOT NULL,
    interests TEXT[] NOT NULL,
    duration INT NOT NULL CHECK (duration > 0),
    budget_level TEXT NOT NULL CHECK (budget_level IN ('Budget', 'Moderate', 'Luxury')),
    travel_style TEXT[] NOT NULL,
    include_food BOOLEAN DEFAULT TRUE,
    include_transport BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trips_user_id ON trips(user_id);
CREATE INDEX IF NOT EXISTS idx_trips_destination ON trips(destination);
CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at DESC);

-- ==================== ITINERARIES TABLE ====================
CREATE TABLE IF NOT EXISTS itineraries (
    id SERIAL PRIMARY KEY,
    trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
    itinerary_text TEXT NOT NULL,
    itinerary_json JSONB,
    word_count INT,
    character_count INT,
    rating INT CHECK (rating >= 0 AND rating <= 5),
    feedback_comments TEXT,
    quality_score FLOAT,
    generated_by_model TEXT DEFAULT 'llama-3.3-70b-versatile',
    generation_time_ms INT,
    used_for_training BOOLEAN DEFAULT FALSE,
    training_cycle_id INT,
    created_at TIMESTAMP DEFAULT NOW(),
    rated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_itineraries_trip_id ON itineraries(trip_id);
CREATE INDEX IF NOT EXISTS idx_itineraries_rating ON itineraries(rating DESC);
CREATE INDEX IF NOT EXISTS idx_itineraries_quality_score ON itineraries(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_itineraries_used_for_training ON itineraries(used_for_training);

-- ==================== TRAINING DATA TABLE (Simplified) ====================
CREATE TABLE IF NOT EXISTS training_data (
    id SERIAL PRIMARY KEY,
    trip_id INT REFERENCES trips(id) ON DELETE CASCADE,
    itinerary_id INT REFERENCES itineraries(id) ON DELETE CASCADE,
    raw_input JSONB NOT NULL,
    raw_output JSONB NOT NULL,
    input_hash TEXT UNIQUE,
    quality_score FLOAT,
    is_high_quality BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_data_trip_id ON training_data(trip_id);
CREATE INDEX IF NOT EXISTS idx_training_data_quality ON training_data(quality_score DESC);
CREATE INDEX IF NOT EXISTS idx_training_data_high_quality ON training_data(is_high_quality);

-- ==================== AUTO TRAINING CYCLES TABLE ====================
CREATE TABLE IF NOT EXISTS training_cycles (
    id SERIAL PRIMARY KEY,
    cycle_number INT UNIQUE NOT NULL,
    data_used INT NOT NULL,
    high_quality_samples INT NOT NULL,
    avg_rating_before FLOAT,
    avg_rating_after FLOAT,
    improvement_score FLOAT,
    insights_generated JSONB,
    patterns_learned JSONB,
    status TEXT DEFAULT 'completed' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    execution_time_ms INT
);

CREATE INDEX IF NOT EXISTS idx_training_cycles_cycle_number ON training_cycles(cycle_number DESC);
CREATE INDEX IF NOT EXISTS idx_training_cycles_status ON training_cycles(status);

-- ==================== METRICS TABLE ====================
CREATE TABLE IF NOT EXISTS metrics (
    id SERIAL PRIMARY KEY,
    metric_type TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at DESC);

-- ==================== SYSTEM METRICS AGGREGATE ====================
CREATE TABLE IF NOT EXISTS system_metrics (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    total_data INT DEFAULT 0,
    total_trips INT DEFAULT 0,
    total_itineraries INT DEFAULT 0,
    total_ratings INT DEFAULT 0,
    training_cycles_completed INT DEFAULT 0,
    avg_rating FLOAT DEFAULT 0.0,
    avg_quality_score FLOAT DEFAULT 0.0,
    high_quality_samples INT DEFAULT 0,
    last_training_cycle TIMESTAMP,
    last_updated TIMESTAMP DEFAULT NOW()
);

INSERT INTO system_metrics (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ==================== VIEWS ====================

CREATE OR REPLACE VIEW popular_destinations AS
SELECT 
    destination,
    COUNT(*) as trip_count,
    AVG(COALESCE(i.rating, 0)) as avg_rating
FROM trips t
LEFT JOIN itineraries i ON t.id = i.trip_id
GROUP BY destination
ORDER BY trip_count DESC, avg_rating DESC;

-- ==================== TRIGGERS ====================

CREATE OR REPLACE FUNCTION update_system_metrics()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE system_metrics SET
        total_itineraries = (SELECT COUNT(*) FROM itineraries),
        total_ratings = (SELECT COUNT(*) FROM itineraries WHERE rating > 0),
        avg_rating = (SELECT AVG(rating) FROM itineraries WHERE rating > 0),
        avg_quality_score = (SELECT AVG(quality_score) FROM itineraries WHERE quality_score IS NOT NULL),
        high_quality_samples = (SELECT COUNT(*) FROM training_data WHERE is_high_quality = TRUE),
        last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_update_metrics_on_itinerary
AFTER INSERT OR UPDATE ON itineraries
FOR EACH ROW
EXECUTE FUNCTION update_system_metrics();

CREATE OR REPLACE FUNCTION auto_create_training_data()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.rating >= 4 AND NEW.rating IS NOT NULL THEN
        INSERT INTO training_data (
            trip_id,
            itinerary_id,
            raw_input,
            raw_output,
            input_hash,
            quality_score,
            is_high_quality
        )
        SELECT 
            NEW.trip_id,
            NEW.id,
            jsonb_build_object(
                'destination', t.destination,
                'interests', t.interests,
                'duration', t.duration,
                'budget_level', t.budget_level,
                'travel_style', t.travel_style
            ),
            jsonb_build_object(
                'itinerary', NEW.itinerary_text,
                'rating', NEW.rating,
                'feedback', NEW.feedback_comments
            ),
            md5(t.destination || array_to_string(t.interests, ',') || t.duration::text),
            NEW.quality_score,
            NEW.rating >= 4
        FROM trips t
        WHERE t.id = NEW.trip_id
        ON CONFLICT (input_hash) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS trigger_auto_training_data
AFTER INSERT OR UPDATE OF rating ON itineraries
FOR EACH ROW
EXECUTE FUNCTION auto_create_training_data();

-- ==================== INITIAL DATA ====================

INSERT INTO users (id, email, username) 
VALUES (1, 'anonymous@travelplanner.ai', 'Anonymous User')
ON CONFLICT (id) DO NOTHING;

COMMIT;
