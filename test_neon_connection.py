"""
Test Neon PostgreSQL Cloud Connection
"""

import os
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()

print("\n" + "="*70)
print("🧪 TESTING NEON CLOUD DATABASE CONNECTION")
print("="*70 + "\n")

# Check if DATABASE_URL is loaded
database_url = os.getenv("DATABASE_URL", "")
if database_url:
    print(f"✅ DATABASE_URL found")
    print(f"   Host: {database_url.split('@')[1].split('/')[0]}")
else:
    print("❌ DATABASE_URL not found in .env file")
    print("\n⚠️  Please add to .env:")
    print('   DATABASE_URL=postgresql://neondb_owner:npg_s0XZcOJvyT6n@ep-solitary-wildflower-a19w99a3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')
    exit(1)

print("\n📡 Attempting connection...")

try:
    from src.database.db_manager import DatabaseManager
    
    # Initialize database manager
    db = DatabaseManager()
    print("✅ Connection successful!\n")
    
    # Test query - Check tables
    print("📊 Checking database tables...")
    result = db.execute_query("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """, fetch=True)
    
    if result:
        print(f"\n✅ Found {len(result)} tables:")
        for table in result:
            print(f"   • {table['table_name']}")
    
    # Test query - Check triggers
    print("\n🔧 Checking database triggers...")
    triggers = db.execute_query("""
        SELECT trigger_name, event_manipulation 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public'
        ORDER BY trigger_name
    """, fetch=True)
    
    if triggers:
        print(f"\n✅ Found {len(triggers)} triggers:")
        for trigger in triggers:
            print(f"   • {trigger['trigger_name']} ({trigger['event_manipulation']})")
    
    # Test query - Get stats
    print("\n📈 Database Statistics:")
    stats = db.get_statistics()
    print(f"   Total Trips: {stats.get('total_trips', 0)}")
    print(f"   Total Itineraries: {stats.get('total_itineraries', 0)}")
    print(f"   Total Ratings: {stats.get('total_ratings', 0)}")
    print(f"   Training Cycles: {stats.get('training_cycles_completed', 0)}")
    
    # Close connection
    db.close()
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED! Neon database is ready for production!")
    print("="*70 + "\n")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}\n")
    import traceback
    traceback.print_exc()
    print("\n💡 TIP: Make sure your .env file has DATABASE_URL set correctly\n")
