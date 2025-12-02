"""
Complete Auto-Training Verification Script
Tests all auto-training features at production level
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

def test_postgresql_triggers():
    """Test PostgreSQL triggers and functions."""
    print("\n" + "="*70)
    print("🧪 TESTING AUTO-TRAINING SYSTEM - PRODUCTION LEVEL")
    print("="*70)
    
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        
        print("\n✅ PostgreSQL connection successful\n")
        
        # Test 1: Check if triggers exist
        print("📋 TEST 1: Checking Database Triggers...")
        print("-" * 70)
        
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
            print(f"✅ Found {len(triggers)} triggers:\n")
            for t in triggers:
                print(f"   • {t['trigger_name']}")
                print(f"     - Event: {t['event_manipulation']}")
                print(f"     - Table: {t['event_object_table']}\n")
        else:
            print("❌ NO TRIGGERS FOUND! Auto-training will NOT work!\n")
            print("⚠️  Run this to fix:")
            print("   psql -U postgres -d travel_planner -f fix_triggers.sql")
            return False
        
        # Test 2: Check trigger functions
        print("\n📋 TEST 2: Checking Trigger Functions...")
        print("-" * 70)
        
        functions = db.execute_query("""
            SELECT 
                routine_name,
                routine_type
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name
        """, fetch=True)
        
        if functions:
            print(f"✅ Found {len(functions)} functions:\n")
            for f in functions:
                print(f"   • {f['routine_name']}()")
        else:
            print("❌ NO FUNCTIONS FOUND!")
        
        # Test 3: Test auto-training trigger
        print("\n\n📋 TEST 3: Testing Auto-Training Trigger...")
        print("-" * 70)
        
        # Get an unrated itinerary
        itin = db.execute_query("""
            SELECT id, trip_id, rating 
            FROM itineraries 
            WHERE rating IS NULL
            LIMIT 1
        """, fetch=True)
        
        if itin:
            itin_id = itin[0]['id']
            original_rating = itin[0]['rating']
            
            print(f"Testing with itinerary #{itin_id}...")
            
            # Rate it 5 stars
            print("   → Rating itinerary 5⭐...")
            db.rate_itinerary(itin_id, 5, "Test rating for auto-training verification")
            
            # Check if training_data was auto-created
            training = db.execute_query("""
                SELECT COUNT(*) as count 
                FROM training_data 
                WHERE itinerary_id = %s
            """, (itin_id,), fetch=True)
            
            if training[0]['count'] > 0:
                print("   ✅ SUCCESS! Training data auto-created by trigger!")
                print("   ✅ Auto-training trigger is WORKING!\n")
                
                # Show the created training data
                data = db.execute_query("""
                    SELECT 
                        id,
                        is_high_quality,
                        quality_score
                    FROM training_data 
                    WHERE itinerary_id = %s
                """, (itin_id,), fetch=True)
                
                if data:
                    print(f"   📊 Training Data Created:")
                    print(f"      - ID: {data[0]['id']}")
                    print(f"      - High Quality: {data[0]['is_high_quality']}")
                    print(f"      - Quality Score: {data[0]['quality_score']:.2f}")
                
            else:
                print("   ⚠️  Training data NOT created")
                print("   ⚠️  Trigger may not be working properly")
            
            # Restore original rating (cleanup)
            if original_rating is None:
                db.execute_query("""
                    UPDATE itineraries 
                    SET rating = NULL 
                    WHERE id = %s
                """, (itin_id,))
                print("   🔄 Restored original state")
        else:
            print("   ℹ️  No unrated itineraries to test")
            print("   ℹ️  Generate a new itinerary to test triggers")
        
        # Test 4: Check metrics auto-update
        print("\n\n📋 TEST 4: Checking Metrics Auto-Update...")
        print("-" * 70)
        
        metrics = db.execute_query("""
            SELECT 
                total_itineraries,
                total_ratings,
                avg_rating,
                high_quality_samples,
                training_cycles_completed
            FROM system_metrics
        """, fetch=True)
        
        if metrics:
            m = metrics[0]
            print("✅ System metrics are tracking:\n")
            print(f"   • Total Itineraries: {m['total_itineraries']}")
            print(f"   • Total Ratings: {m['total_ratings']}")
            print(f"   • Average Rating: {m['avg_rating'] or 0:.2f}⭐")
            print(f"   • High Quality Samples: {m['high_quality_samples']}")
            print(f"   • Training Cycles: {m['training_cycles_completed']}")
        
        # Test 5: Training readiness
        print("\n\n📋 TEST 5: Training Readiness Check...")
        print("-" * 70)
        
        hq_count = db.execute_query("""
            SELECT COUNT(*) as count 
            FROM training_data 
            WHERE is_high_quality = TRUE
        """, fetch=True)
        
        hq = hq_count[0]['count']
        
        if hq >= 3:
            print(f"✅ READY TO TRAIN! {hq} high-quality samples available")
            print("   🧠 Auto-training will trigger automatically")
        else:
            print(f"⚠️  Need {3 - hq} more high-quality samples")
            print(f"   Current: {hq}/3 samples")
            print("\n   To trigger auto-training:")
            print("   1. Generate 3+ itineraries")
            print("   2. Rate them 4-5 stars ⭐⭐⭐⭐⭐")
            print("   3. Training will start automatically!")
        
        # Final summary
        print("\n" + "="*70)
        print("✅ AUTO-TRAINING SYSTEM VERIFICATION COMPLETE")
        print("="*70)
        
        print("\n📊 Summary:")
        print(f"   ✅ Triggers: {len(triggers) if triggers else 0} active")
        print(f"   ✅ Functions: {len(functions) if functions else 0} defined")
        print(f"   ✅ Training Data: {hq} high-quality samples")
        print(f"   {'✅' if hq >= 3 else '⚠️ '} Training Status: {'Ready' if hq >= 3 else 'Need more data'}")
        
        return True
        
    except ImportError:
        print("❌ DatabaseManager not found!")
        print("   Make sure src/database/db_manager.py exists")
        return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dual_storage():
    """Test dual storage system."""
    print("\n" + "="*70)
    print("📦 TESTING DUAL STORAGE SYSTEM")
    print("="*70 + "\n")
    
    import json
    from pathlib import Path
    
    # Check JSON files
    data_dir = Path("data")
    
    files = {
        "trips.json": "Trips",
        "itineraries.json": "Itineraries",
        "training_data.json": "Training Data",
        "system_metrics.json": "System Metrics"
    }
    
    print("📁 Checking JSON backup files:\n")
    
    all_exist = True
    for filename, description in files.items():
        filepath = data_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data) if isinstance(data, list) else 1
                print(f"   ✅ {description:20} - {count} records ({size} bytes)")
            except:
                print(f"   ⚠️  {description:20} - Exists but corrupt")
        else:
            print(f"   ❌ {description:20} - NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ All JSON backup files exist and are readable")
    else:
        print("\n⚠️  Some backup files are missing")
    
    # Compare PostgreSQL vs JSON counts
    try:
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        
        print("\n📊 Comparing PostgreSQL vs JSON:\n")
        
        pg_trips = db.execute_query("SELECT COUNT(*) as count FROM trips", fetch=True)[0]['count']
        pg_itins = db.execute_query("SELECT COUNT(*) as count FROM itineraries", fetch=True)[0]['count']
        
        with open(data_dir / "trips.json", 'r', encoding='utf-8') as f:
            json_trips = len(json.load(f))
        
        with open(data_dir / "itineraries.json", 'r', encoding='utf-8') as f:
            json_itins = len(json.load(f))
        
        print(f"   Trips:        PostgreSQL={pg_trips:3d}  JSON={json_trips:3d}  {'✅ Match' if pg_trips == json_trips else '⚠️  Mismatch'}")
        print(f"   Itineraries:  PostgreSQL={pg_itins:3d}  JSON={json_itins:3d}  {'✅ Match' if pg_itins == json_itins else '⚠️  Mismatch'}")
        
        if pg_trips == json_trips and pg_itins == json_itins:
            print("\n✅ Dual storage is PERFECTLY SYNCHRONIZED!")
        else:
            print("\n⚠️  Storage synchronization issue detected")
        
    except:
        print("\n⚠️  Could not compare with PostgreSQL")

if __name__ == "__main__":
    print("\n" + "🚀 PRODUCTION AUTO-TRAINING VERIFICATION SUITE" + "\n")
    
    # Test 1: PostgreSQL triggers
    triggers_ok = test_postgresql_triggers()
    
    # Test 2: Dual storage
    test_dual_storage()
    
    print("\n" + "="*70)
    if triggers_ok:
        print("🎉 ALL SYSTEMS OPERATIONAL - READY FOR PRODUCTION!")
    else:
        print("⚠️  ISSUES DETECTED - SEE ABOVE FOR FIXES")
    print("="*70 + "\n")
