-- ==================== COMPLETE DATABASE VIEWER ====================
-- Fix encoding for special characters (₹, €, etc.)
\encoding UTF8

-- 1. OVERVIEW - System Metrics
SELECT 
    '📊 SYSTEM METRICS' as section,
    total_trips || ' trips' as trips,
    total_itineraries || ' itineraries' as itineraries,
    total_ratings || ' ratings' as ratings,
    ROUND(CAST(avg_rating AS NUMERIC), 2) || '⭐' as avg_rating,
    training_cycles_completed || ' cycles' as training,
    high_quality_samples || ' samples' as hq_samples
FROM system_metrics;

-- 2. ALL TRIPS - Recent first
SELECT 
    '📍 ALL TRIPS' as section;
    
SELECT 
    id,
    destination,
    array_to_string(interests, ', ') as interests,
    duration || ' days' as duration,
    budget_level,
    array_to_string(travel_style, ', ') as style,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM trips
ORDER BY created_at DESC
LIMIT 20;

-- 3. ALL ITINERARIES - With ratings
SELECT 
    '⭐ ALL ITINERARIES' as section;

SELECT 
    i.id,
    t.destination,
    i.word_count || ' words' as length,
    CASE 
        WHEN i.rating IS NULL THEN 'Not rated'
        ELSE repeat('⭐', i.rating)
    END as rating,
    CASE 
        WHEN i.feedback_comments IS NULL OR i.feedback_comments = '' THEN 'No feedback'
        ELSE LEFT(i.feedback_comments, 50) || '...'
    END as feedback,
    TO_CHAR(i.created_at, 'YYYY-MM-DD HH24:MI') as created
FROM itineraries i
JOIN trips t ON t.id = i.trip_id  -- ✅ FIXED: Was t.trip_id = i.id
ORDER BY i.created_at DESC
LIMIT 20;

-- 4. TRAINING DATA - High quality only
SELECT 
    '🧠 TRAINING DATA' as section;

SELECT 
    id,
    itinerary_id,
    CASE 
        WHEN is_high_quality THEN '✅ High Quality'
        ELSE '⚠️ Low Quality'
    END as quality,
    ROUND(CAST(quality_score AS NUMERIC), 2) as score,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created
FROM training_data
ORDER BY quality_score DESC
LIMIT 20;

-- 5. TRAINING CYCLES - Completed
SELECT 
    '🔄 TRAINING CYCLES' as section;

SELECT 
    cycle_number,
    high_quality_samples || ' samples' as samples,
    ROUND(CAST(improvement_score AS NUMERIC), 2) as improvement,
    status,
    TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI') as completed
FROM training_cycles
ORDER BY cycle_number DESC;

-- 6. POPULAR DESTINATIONS
SELECT 
    '🌍 POPULAR DESTINATIONS' as section;

SELECT * FROM popular_destinations LIMIT 10;

-- 7. RATING DISTRIBUTION
SELECT 
    '📊 RATING DISTRIBUTION' as section;

SELECT 
    repeat('⭐', rating) as stars,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) || '%' as percentage
FROM itineraries
WHERE rating IS NOT NULL
GROUP BY rating
ORDER BY rating DESC;

-- 8. BUDGET PERFORMANCE (FIXED JOIN)
SELECT 
    '💰 BUDGET PERFORMANCE' as section;

SELECT 
    t.budget_level,
    COUNT(*) as trips,
    ROUND(CAST(AVG(i.rating) AS NUMERIC), 2) as avg_rating,
    ROUND(CAST(AVG(i.quality_score) AS NUMERIC), 2) as avg_quality
FROM trips t
JOIN itineraries i ON t.id = i.trip_id  -- ✅ FIXED JOIN
WHERE i.rating IS NOT NULL
GROUP BY t.budget_level
ORDER BY avg_rating DESC;

-- 9. RECENT ACTIVITY - Last 10 events
SELECT 
    '📅 RECENT ACTIVITY' as section;

SELECT 
    'Trip Created' as event,
    destination as details,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as timestamp
FROM trips
UNION ALL
SELECT 
    'Itinerary Rated' as event,
    repeat('⭐', rating) as details,
    TO_CHAR(rated_at, 'YYYY-MM-DD HH24:MI') as timestamp
FROM itineraries
WHERE rating IS NOT NULL
ORDER BY timestamp DESC
LIMIT 10;

-- 10. DATABASE HEALTH CHECK
SELECT 
    '🏥 DATABASE HEALTH' as section;

SELECT 
    'Tables' as check_type,
    COUNT(*) || ' tables exist' as status
FROM information_schema.tables
WHERE table_schema = 'public'
UNION ALL
SELECT 
    'Triggers',
    COUNT(*) || ' triggers active' as status
FROM information_schema.triggers
WHERE trigger_schema = 'public'
UNION ALL
SELECT 
    'Functions',
    COUNT(*) || ' functions defined' as status
FROM information_schema.routines
WHERE routine_schema = 'public' AND routine_type = 'FUNCTION';
