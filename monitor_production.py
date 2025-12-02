"""Monitor production app in real-time."""

import os
import time
from datetime import datetime

os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_s0XZcOJvyT6n@ep-solitary-wildflower-a19w99a3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

from src.database.db_manager import DatabaseManager

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

print("🔴 LIVE PRODUCTION MONITORING - Press Ctrl+C to stop\n")
time.sleep(2)

previous_stats = {}

try:
    while True:
        clear_screen()
        
        print("="*70)
        print(f"📊 LIVE PRODUCTION STATS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        db = DatabaseManager()
        stats = db.get_statistics()
        
        # System metrics
        print("\n📈 SYSTEM METRICS:")
        trips = stats.get('total_trips', 0)
        itins = stats.get('total_itineraries', 0)
        ratings = stats.get('total_ratings', 0)
        cycles = stats.get('training_cycles_completed', 0)
        
        print(f"   Total Trips: {trips}")
        print(f"   Total Itineraries: {itins}", end="")
        if previous_stats.get('itineraries') and itins > previous_stats['itineraries']:
            print(" 🆕 NEW!", end="")
        print()
        
        print(f"   Total Ratings: {ratings}", end="")
        if previous_stats.get('ratings') and ratings > previous_stats['ratings']:
            print(" 🆕 NEW!", end="")
        print()
        
        print(f"   Training Cycles: {cycles}")
        print(f"   High Quality Samples: {stats.get('high_quality_samples', 0)}")
        
        # Training progress
        hq_samples = stats.get('high_quality_samples', 0)
        if hq_samples < 3:
            print(f"\n🧠 AUTO-TRAINING: Waiting ({hq_samples}/3 samples)")
        else:
            print(f"\n🧠 AUTO-TRAINING: Ready! ({hq_samples} samples)")
        
        # Recent activity
        print("\n📋 RECENT ACTIVITY:")
        recent = db.get_recent_itineraries(3)
        if recent:
            for itin in recent:
                rating = "⭐" * (itin['rating'] or 0) if itin['rating'] else "Not rated"
                print(f"   • {itin['destination']} ({itin['duration']}d) - {rating}")
        else:
            print("   No activity yet")
        
        db.close()
        
        # Store for comparison
        previous_stats = {
            'itineraries': itins,
            'ratings': ratings
        }
        
        print("\n" + "="*70)
        print("Refreshing in 10 seconds... (Ctrl+C to stop)")
        
        time.sleep(10)
        
except KeyboardInterrupt:
    print("\n\n✅ Monitoring stopped.\n")
