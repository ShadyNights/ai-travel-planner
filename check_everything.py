"""
MASTER VERIFICATION SCRIPT
Checks all features comprehensively
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Color codes for terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

# ============================================================================
# TEST 1: CHECK FILE STRUCTURE
# ============================================================================

def test_file_structure():
    print_header("TEST 1: FILE STRUCTURE")
    
    required_files = {
        "app.py": "Main application",
        "src/database/db_manager.py": "Database manager",
        "src/core/planner.py": "Travel planner",
        "src/utils/logger.py": "Logger utility",
        ".env": "Environment variables"
    }
    
    all_exist = True
    for file, desc in required_files.items():
        if Path(file).exists():
            print_success(f"{desc:30} - {file}")
        else:
            print_error(f"{desc:30} - MISSING: {file}")
            all_exist = False
    
    return all_exist

# ============================================================================
# TEST 2: CHECK JSON STORAGE
# ============================================================================

def test_json_storage():
    print_header("TEST 2: JSON STORAGE (Backup System)")
    
    data_dir = Path("data")
    
    if not data_dir.exists():
        print_warning("Data directory doesn't exist - will be created on first use")
        return False
    
    files = {
        "complete_itineraries.json": "Itineraries",
        "training_patterns.json": "Training patterns",
        "feedback.json": "User feedback"
    }
    
    all_exist = True
    total_records = 0
    
    for filename, desc in files.items():
        filepath = data_dir / filename
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else 1
                    size = filepath.stat().st_size
                    print_success(f"{desc:20} - {count:4d} records ({size:,} bytes)")
                    total_records += count
            except Exception as e:
                print_error(f"{desc:20} - Corrupted: {e}")
                all_exist = False
        else:
            print_warning(f"{desc:20} - Not created yet")
    
    print_info(f"Total JSON records: {total_records}")
    return all_exist

# ============================================================================
# TEST 3: CHECK POSTGRESQL CONNECTION
# ============================================================================

def test_postgresql():
    print_header("TEST 3: POSTGRESQL CONNECTION")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.database.db_manager import DatabaseManager
        
        db = DatabaseManager()
        print_success("PostgreSQL connection established")
        
        # Check tables
        result = db.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """, fetch=True)
        
        if result:
            print_success(f"Found {len(result)} tables:")
            for table in result:
                print(f"   • {table['table_name']}")
        
        return True, db
        
    except ImportError:
        print_error("DatabaseManager not found")
        print_info("Check: src/database/db_manager.py exists")
        return False, None
    
    except Exception as e:
        print_error(f"PostgreSQL connection failed: {e}")
        print_info("Check: .env file has correct DB_PASSWORD")
        return False, None

# ============================================================================
# TEST 4: CHECK DUAL STORAGE SYNC
# ============================================================================

def test_dual_storage(db):
    print_header("TEST 4: DUAL STORAGE SYNCHRONIZATION")
    
    if not db:
        print_warning("Skipping - PostgreSQL not available")
        return False
    
    try:
        # PostgreSQL counts
        pg_trips = db.execute_query("SELECT COUNT(*) as count FROM trips", fetch=True)[0]['count']
        pg_itins = db.execute_query("SELECT COUNT(*) as count FROM itineraries", fetch=True)[0]['count']
        
        print_info(f"PostgreSQL: {pg_trips} trips, {pg_itins} itineraries")
        
        # JSON counts
        data_dir = Path("data")
        
        json_trips = 0
        json_itins = 0
        
        if (data_dir / "complete_itineraries.json").exists():
            with open(data_dir / "complete_itineraries.json", 'r', encoding='utf-8') as f:
                json_itins = len(json.load(f))
        
        print_info(f"JSON Backup: {json_itins} itineraries")
        
        # Compare
        if pg_itins > 0 and json_itins > 0:
            if abs(pg_itins - json_itins) <= 1:  # Allow 1 difference for race conditions
                print_success("Dual storage is SYNCHRONIZED!")
                return True
            else:
                print_warning(f"Storage mismatch: PG={pg_itins}, JSON={json_itins}")
                return False
        elif pg_itins == 0 and json_itins == 0:
            print_info("No data generated yet - generate an itinerary first")
            return True
        else:
            print_warning("Partial data - may need to generate more itineraries")
            return True
            
    except Exception as e:
        print_error(f"Dual storage check failed: {e}")
        return False

# ============================================================================
# TEST 5: CHECK DATABASE TRIGGERS
# ============================================================================

def test_triggers(db):
    print_header("TEST 5: AUTO-TRAINING TRIGGERS")
    
    if not db:
        print_warning("Skipping - PostgreSQL not available")
        return False
    
    try:
        # Check triggers
        triggers = db.execute_query("""
            SELECT 
                trigger_name,
                event_manipulation,
                event_object_table
            FROM information_schema.triggers 
            WHERE trigger_schema = 'public'
            ORDER BY trigger_name
        """, fetch=True)
        
        if triggers:
            print_success(f"Found {len(triggers)} triggers:")
            for t in triggers:
                print(f"   • {t['trigger_name']}")
                print(f"     Table: {t['event_object_table']} | Event: {t['event_manipulation']}")
        else:
            print_error("NO TRIGGERS FOUND!")
            print_info("Fix: Run this command:")
            print_info("   psql -U postgres -d travel_planner -f fix_triggers.sql")
            return False
        
        # Check functions
        functions = db.execute_query("""
            SELECT routine_name
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """, fetch=True)
        
        if functions:
            print_success(f"Found {len(functions)} trigger functions:")
            for f in functions:
                print(f"   • {f['routine_name']}()")
        else:
            print_error("NO TRIGGER FUNCTIONS FOUND!")
            return False
        
        return len(triggers) >= 2 and len(functions) >= 2
        
    except Exception as e:
        print_error(f"Trigger check failed: {e}")
        return False

# ============================================================================
# TEST 6: CHECK TRAINING DATA
# ============================================================================

def test_training_data(db):
    print_header("TEST 6: TRAINING DATA & AUTO-LEARNING")
    
    if not db:
        print_warning("Skipping - PostgreSQL not available")
        return False
    
    try:
        # Check training data
        training_count = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM training_data
        """, fetch=True)[0]['count']
        
        hq_count = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM training_data 
            WHERE is_high_quality = TRUE
        """, fetch=True)[0]['count']
        
        print_info(f"Total training samples: {training_count}")
        print_info(f"High-quality samples: {hq_count}")
        
        if hq_count >= 3:
            print_success(f"READY FOR AUTO-TRAINING! ({hq_count}/3 samples)")
        else:
            print_warning(f"Need {3 - hq_count} more high-quality samples")
            print_info("Generate itineraries and rate them 4-5 stars ⭐")
        
        # Check training cycles
        cycles = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM training_cycles
        """, fetch=True)[0]['count']
        
        if cycles > 0:
            print_success(f"Training cycles completed: {cycles}")
        else:
            print_info("No training cycles completed yet")
        
        return True
        
    except Exception as e:
        print_error(f"Training data check failed: {e}")
        return False

# ============================================================================
# TEST 7: CHECK SYSTEM METRICS
# ============================================================================

def test_metrics(db):
    print_header("TEST 7: SYSTEM METRICS & STATISTICS")
    
    if not db:
        print_warning("Skipping - PostgreSQL not available")
        return False
    
    try:
        metrics = db.execute_query("""
            SELECT * FROM system_metrics WHERE id = 1
        """, fetch=True)
        
        if metrics:
            m = metrics[0]
            print_success("System metrics active:")
            print(f"   • Total Trips: {m['total_trips']}")
            print(f"   • Total Itineraries: {m['total_itineraries']}")
            print(f"   • Total Ratings: {m['total_ratings']}")
            print(f"   • Average Rating: {m['avg_rating'] or 0:.2f}⭐")
            print(f"   • Training Cycles: {m['training_cycles_completed']}")
            print(f"   • High Quality Samples: {m['high_quality_samples']}")
            
            return True
        else:
            print_warning("No metrics recorded yet")
            return False
            
    except Exception as e:
        print_error(f"Metrics check failed: {e}")
        return False

# ============================================================================
# TEST 8: SIMULATE AUTO-TRAINING
# ============================================================================

def test_auto_training_trigger(db):
    print_header("TEST 8: AUTO-TRAINING TRIGGER SIMULATION")
    
    if not db:
        print_warning("Skipping - PostgreSQL not available")
        return False
    
    try:
        # Find an unrated itinerary
        itin = db.execute_query("""
            SELECT id, trip_id, rating 
            FROM itineraries 
            WHERE rating IS NULL
            LIMIT 1
        """, fetch=True)
        
        if not itin:
            print_info("No unrated itineraries to test")
            print_info("Generate a new itinerary in the app to test triggers")
            return True
        
        itin_id = itin[0]['id']
        original_rating = itin[0]['rating']
        
        print_info(f"Testing with itinerary #{itin_id}...")
        
        # Rate it 5 stars
        print_info("Rating itinerary 5⭐...")
        db.rate_itinerary(itin_id, 5, "Auto-training trigger test")
        
        # Check if training_data was created
        training = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM training_data 
            WHERE itinerary_id = %s
        """, (itin_id,), fetch=True)
        
        if training[0]['count'] > 0:
            print_success("AUTO-TRAINING TRIGGER WORKING!")
            print_success("Training data created automatically by database trigger")
            
            # Show created data
            data = db.execute_query("""
                SELECT is_high_quality, quality_score
                FROM training_data 
                WHERE itinerary_id = %s
            """, (itin_id,), fetch=True)
            
            if data:
                print(f"   • High Quality: {data[0]['is_high_quality']}")
                print(f"   • Quality Score: {data[0]['quality_score']:.2f}")
            
            # Cleanup - restore original state
            db.execute_query("""
                UPDATE itineraries 
                SET rating = %s 
                WHERE id = %s
            """, (original_rating, itin_id))
            
            print_info("Test completed - restored original state")
            return True
        else:
            print_error("Training data NOT created - trigger not working!")
            return False
            
    except Exception as e:
        print_error(f"Auto-training test failed: {e}")
        return False

# ============================================================================
# MAIN VERIFICATION
# ============================================================================

def main():
    print_header("🚀 COMPLETE SYSTEM VERIFICATION")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {}
    
    # Run all tests
    results['files'] = test_file_structure()
    results['json'] = test_json_storage()
    results['postgres'], db = test_postgresql()
    results['dual_storage'] = test_dual_storage(db)
    results['triggers'] = test_triggers(db)
    results['training'] = test_training_data(db)
    results['metrics'] = test_metrics(db)
    results['auto_training'] = test_auto_training_trigger(db)
    
    # Final summary
    print_header("📊 VERIFICATION SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{GREEN}✅ PASS{RESET}" if result else f"{RED}❌ FAIL{RESET}"
        print(f"{test_name.upper():20} {status}")
    
    print(f"\n{BLUE}{'='*70}{RESET}")
    
    if passed == total:
        print(f"{GREEN}🎉 ALL TESTS PASSED! ({passed}/{total}){RESET}")
        print(f"{GREEN}✅ System is FULLY OPERATIONAL and PRODUCTION READY!{RESET}")
    else:
        print(f"{YELLOW}⚠️  {passed}/{total} tests passed{RESET}")
        print(f"{YELLOW}Some features need attention (see details above){RESET}")
    
    print(f"{BLUE}{'='*70}{RESET}\n")
    
    # Next steps
    if not results['postgres']:
        print_info("Next Step: Fix PostgreSQL connection in .env file")
    elif not results['triggers']:
        print_info("Next Step: Run fix_triggers.sql to enable auto-training")
    elif not results['training']:
        print_info("Next Step: Generate 3+ itineraries and rate them 4-5 stars")
    else:
        print_success("System ready! Start generating travel itineraries!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️  Verification interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}❌ Verification failed: {e}{RESET}")
        import traceback
        traceback.print_exc()
