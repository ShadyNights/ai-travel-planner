-- ==================== FIX POSTGRESQL TRIGGERS ====================
-- Run this if triggers are missing or broken

-- Drop existing triggers (if any)
DROP TRIGGER IF EXISTS trigger_update_metrics_on_itinerary ON itineraries;
DROP TRIGGER IF EXISTS trigger_auto_training_data ON itineraries;

-- Verify functions exist (these should already be in your database)
-- If not, you need to run database_setup_fixed.sql first

-- Recreate triggers (without IF NOT EXISTS - PostgreSQL doesn't support it)
CREATE TRIGGER trigger_update_metrics_on_itinerary
AFTER INSERT OR UPDATE ON itineraries
FOR EACH ROW
EXECUTE FUNCTION update_system_metrics();

CREATE TRIGGER trigger_auto_training_data
AFTER INSERT OR UPDATE OF rating ON itineraries
FOR EACH ROW
EXECUTE FUNCTION auto_create_training_data();

-- Verify triggers were created
SELECT 
    trigger_name,
    event_manipulation,
    event_object_table
FROM information_schema.triggers 
WHERE trigger_schema = 'public'
ORDER BY trigger_name;

-- Success message
\echo '✅ Triggers fixed successfully!'
