-- ==================== FIX TRAINING CYCLE FUNCTION ====================

CREATE OR REPLACE FUNCTION trigger_training_cycle()
RETURNS VOID AS $$
DECLARE
    total_samples INT;
    high_quality_count INT;
    new_cycle_number INT;
BEGIN
    -- Count training samples (REMOVED used_for_training check)
    SELECT 
        COUNT(*), 
        COUNT(*) FILTER (WHERE is_high_quality = TRUE)
    INTO total_samples, high_quality_count
    FROM training_data;
    
    -- Need at least 3 high-quality samples
    IF high_quality_count >= 3 THEN
        -- Get next cycle number
        SELECT COALESCE(MAX(cycle_number), 0) + 1 
        INTO new_cycle_number 
        FROM training_cycles;
        
        -- Create training cycle record
        INSERT INTO training_cycles (
            cycle_number,
            data_used,
            high_quality_samples,
            avg_rating_before,
            avg_rating_after,
            improvement_score,
            insights_generated,
            patterns_learned,
            status,
            started_at,
            completed_at,
            execution_time_ms
        ) VALUES (
            new_cycle_number,
            total_samples,
            high_quality_count,
            (SELECT AVG(quality_score) FROM training_data WHERE is_high_quality = FALSE),
            (SELECT AVG(quality_score) FROM training_data WHERE is_high_quality = TRUE),
            5.0, -- Placeholder improvement score
            jsonb_build_object(
                'high_quality_destinations', (
                    SELECT jsonb_agg(DISTINCT t.destination)
                    FROM training_data td
                    JOIN itineraries i ON td.itinerary_id = i.id
                    JOIN trips t ON i.trip_id = t.id
                    WHERE td.is_high_quality = TRUE
                ),
                'avg_quality_score', (
                    SELECT ROUND(AVG(quality_score)::numeric, 2)
                    FROM training_data
                    WHERE is_high_quality = TRUE
                ),
                'total_samples', high_quality_count
            ),
            jsonb_build_object(
                'pattern_type', 'quality_analysis',
                'cycle', new_cycle_number
            ),
            'completed',
            NOW(),
            NOW(),
            100 -- Placeholder execution time
        );
        
        -- Update system metrics
        UPDATE system_metrics
        SET training_cycles_completed = new_cycle_number,
            high_quality_samples = high_quality_count,
            last_training_cycle = NOW();
        
        RAISE NOTICE 'Training cycle % completed with % high-quality samples', new_cycle_number, high_quality_count;
    ELSE
        RAISE NOTICE 'Not enough high-quality samples: % of 3 needed', high_quality_count;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Test the function
SELECT trigger_training_cycle();

-- Verify it worked
SELECT 
    cycle_number,
    high_quality_samples,
    status,
    TO_CHAR(completed_at, 'YYYY-MM-DD HH24:MI') as completed
FROM training_cycles
ORDER BY cycle_number DESC;
