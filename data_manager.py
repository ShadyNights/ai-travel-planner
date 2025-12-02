"""
Ultimate Data Manager - Complete Access to JSON & PostgreSQL
All-in-one tool for viewing, exporting, searching, and backing up data
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_s0XZcOJvyT6n@ep-solitary-wildflower-a19w99a3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

from src.database.db_manager import DatabaseManager

class DataManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.export_dir = Path("exports")
        self.export_dir.mkdir(exist_ok=True)
    
    def show_menu(self):
        """Main menu."""
        print("\n" + "="*80)
        print("🗄️  ULTIMATE DATA MANAGER - PostgreSQL & JSON")
        print("="*80)
        print("\n📊 VIEW DATA:")
        print("  1. List all itineraries (summary)")
        print("  2. View specific itinerary (full text)")
        print("  3. View all data (complete dump)")
        print("  4. Show statistics")
        print("\n🔍 SEARCH & FILTER:")
        print("  5. Search by destination")
        print("  6. Filter by rating (4-5 stars)")
        print("  7. Recent itineraries (last 10)")
        print("\n💾 EXPORT & BACKUP:")
        print("  8. Export all to JSON")
        print("  9. Export specific itinerary to JSON")
        print("  10. Create complete backup")
        print("  11. View local JSON files")
        print("\n🧠 TRAINING DATA:")
        print("  12. View training data")
        print("  13. Training statistics")
        print("\n📂 ADVANCED:")
        print("  14. PostgreSQL direct query")
        print("  15. Bulk export (CSV)")
        print("\n  0. Exit")
        print("="*80)
    
    def list_itineraries(self):
        """List all itineraries (summary)."""
        query = """
            SELECT 
                i.id, 
                t.destination, 
                t.duration, 
                t.budget_level,
                i.rating, 
                i.word_count,
                i.created_at
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            ORDER BY i.created_at DESC
        """
        results = self.db.execute_query(query, fetch=True)
        
        print(f"\n📋 Found {len(results)} itineraries:\n")
        print(f"{'ID':<5} {'Destination':<20} {'Days':<6} {'Budget':<12} {'Rating':<15} {'Words':<8} {'Created'}")
        print("-" * 100)
        
        for r in results:
            rating = "⭐" * (r['rating'] or 0) if r['rating'] else "Not rated"
            created = r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else 'N/A'
            print(f"{r['id']:<5} {r['destination']:<20} {r['duration']:<6} {r['budget_level']:<12} {rating:<15} {r['word_count']:<8} {created}")
        
        print()
    
    def view_itinerary(self, itin_id=None):
        """View specific itinerary with full details."""
        if itin_id is None:
            itin_id = input("\nEnter itinerary ID: ").strip()
            if not itin_id.isdigit():
                print("❌ Invalid ID")
                return
            itin_id = int(itin_id)
        
        query = """
            SELECT 
                i.id, i.itinerary_text, i.word_count, i.character_count,
                i.rating, i.feedback_comments, i.quality_score,
                i.generation_time_ms, i.created_at, i.rated_at,
                t.destination, t.duration, t.budget_level,
                t.interests, t.travel_style, t.include_food, t.include_transport
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            WHERE i.id = %s
        """
        result = self.db.execute_query(query, (itin_id,), fetch=True)
        
        if not result:
            print(f"\n❌ Itinerary #{itin_id} not found")
            return
        
        itin = result[0]
        
        print("\n" + "="*80)
        print(f"ITINERARY #{itin['id']} - {itin['destination'].upper()}")
        print("="*80)
        print(f"\n📍 TRIP DETAILS:")
        print(f"   Destination: {itin['destination']}")
        print(f"   Duration: {itin['duration']} days")
        print(f"   Budget: {itin['budget_level']}")
        print(f"   Interests: {', '.join(itin['interests'])}")
        print(f"   Travel Style: {', '.join(itin['travel_style'])}")
        print(f"   Food: {'Yes' if itin['include_food'] else 'No'}")
        print(f"   Transport: {'Yes' if itin['include_transport'] else 'No'}")
        
        print(f"\n📊 METRICS:")
        print(f"   Word Count: {itin['word_count']}")
        print(f"   Character Count: {itin['character_count']}")
        print(f"   Generation Time: {itin['generation_time_ms']}ms")
        print(f"   Quality Score: {itin['quality_score']:.2f}" if itin['quality_score'] else "   Quality Score: N/A")
        
        print(f"\n⭐ RATING:")
        if itin['rating']:
            print(f"   {'⭐' * itin['rating']} ({itin['rating']}/5)")
            if itin['feedback_comments']:
                print(f"   Feedback: {itin['feedback_comments']}")
            print(f"   Rated: {itin['rated_at']}")
        else:
            print("   Not rated yet")
        
        print(f"\n📅 DATES:")
        print(f"   Created: {itin['created_at']}")
        
        print(f"\n📝 FULL ITINERARY:")
        print("-"*80)
        print(itin['itinerary_text'])
        print("\n" + "="*80 + "\n")
        
        # Ask if export
        export = input("Export this to JSON? (y/n): ").strip().lower()
        if export == 'y':
            self.export_single_itinerary(itin_id)
    
    def view_all_data(self):
        """Complete data dump."""
        query = """
            SELECT 
                i.id, i.itinerary_text, i.rating, i.created_at,
                t.destination, t.duration, t.budget_level
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            ORDER BY i.created_at DESC
        """
        results = self.db.execute_query(query, fetch=True)
        
        print(f"\n📊 COMPLETE DATA DUMP ({len(results)} itineraries)\n")
        
        for idx, itin in enumerate(results, 1):
            print(f"\n{'='*80}")
            print(f"[{idx}/{len(results)}] ITINERARY #{itin['id']} - {itin['destination']}")
            print(f"{'='*80}")
            print(f"Duration: {itin['duration']} days | Budget: {itin['budget_level']}")
            rating = f"{'⭐' * itin['rating']}" if itin['rating'] else "Not rated"
            print(f"Rating: {rating} | Created: {itin['created_at']}")
            print(f"\n{itin['itinerary_text']}\n")
    
    def show_statistics(self):
        """Show comprehensive statistics."""
        stats = self.db.get_statistics()
        
        print("\n" + "="*80)
        print("📊 SYSTEM STATISTICS")
        print("="*80)
        
        print(f"\n📈 OVERVIEW:")
        print(f"   Total Trips: {stats.get('total_trips', 0)}")
        print(f"   Total Itineraries: {stats.get('total_itineraries', 0)}")
        print(f"   Total Ratings: {stats.get('total_ratings', 0)}")
        print(f"   Average Rating: {stats.get('avg_rating', 0):.1f}⭐")
        print(f"   Average Quality Score: {stats.get('avg_quality_score', 0):.2f}")
        
        print(f"\n🧠 TRAINING:")
        print(f"   Training Cycles: {stats.get('training_cycles_completed', 0)}")
        print(f"   High Quality Samples: {stats.get('high_quality_samples', 0)}")
        
        if stats.get('top_cities'):
            print(f"\n🌍 TOP DESTINATIONS:")
            for city, count in stats['top_cities']:
                print(f"   • {city}: {count} trip(s)")
        
        if stats.get('rating_distribution'):
            print(f"\n⭐ RATING DISTRIBUTION:")
            for rating in sorted(stats['rating_distribution'].keys(), reverse=True):
                count = stats['rating_distribution'][rating]
                stars = "⭐" * rating
                print(f"   {stars} ({rating}): {count} rating(s)")
        
        print("\n" + "="*80 + "\n")
    
    def search_destination(self):
        """Search by destination."""
        dest = input("\nEnter destination to search: ").strip()
        if not dest:
            return
        
        query = """
            SELECT i.id, t.destination, t.duration, i.rating, i.created_at
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            WHERE LOWER(t.destination) LIKE LOWER(%s)
            ORDER BY i.created_at DESC
        """
        results = self.db.execute_query(query, (f"%{dest}%",), fetch=True)
        
        print(f"\n🔍 Found {len(results)} results for '{dest}':\n")
        for r in results:
            rating = "⭐" * (r['rating'] or 0) if r['rating'] else "Not rated"
            print(f"  #{r['id']} - {r['destination']} ({r['duration']}d) - {rating}")
        print()
    
    def filter_by_rating(self):
        """Filter by high ratings."""
        query = """
            SELECT i.id, t.destination, t.duration, i.rating, i.created_at
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            WHERE i.rating >= 4
            ORDER BY i.rating DESC, i.created_at DESC
        """
        results = self.db.execute_query(query, fetch=True)
        
        print(f"\n⭐ Found {len(results)} itineraries with 4-5 stars:\n")
        for r in results:
            rating = "⭐" * r['rating']
            print(f"  #{r['id']} - {r['destination']} ({r['duration']}d) - {rating}")
        print()
    
    def recent_itineraries(self):
        """Show recent itineraries."""
        results = self.db.get_recent_itineraries(10)
        
        print(f"\n📋 Last 10 itineraries:\n")
        for r in results:
            rating = "⭐" * (r['rating'] or 0) if r['rating'] else "Not rated"
            print(f"  #{r['id']} - {r['destination']} ({r['duration']}d) - {rating}")
        print()
    
    def export_all(self):
        """Export all data to JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print("\n📥 EXPORTING ALL DATA...\n")
        
        # Export itineraries
        query = """
            SELECT 
                i.id, i.trip_id, i.itinerary_text, i.word_count,
                i.rating, i.feedback_comments, i.quality_score,
                i.created_at, i.rated_at,
                t.destination, t.duration, t.budget_level,
                t.interests, t.travel_style
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            ORDER BY i.created_at DESC
        """
        itineraries = self.db.execute_query(query, fetch=True)
        
        itineraries_data = []
        for itin in itineraries:
            itin_dict = dict(itin)
            itin_dict['created_at'] = str(itin_dict['created_at'])
            itin_dict['rated_at'] = str(itin_dict['rated_at']) if itin_dict['rated_at'] else None
            itineraries_data.append(itin_dict)
        
        filename = self.export_dir / f"itineraries_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(itineraries_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(itineraries_data)} itineraries to: {filename}")
        
        # Complete backup
        complete_backup = {
            "export_date": str(datetime.now()),
            "stats": dict(self.db.get_statistics()),
            "itineraries": itineraries_data
        }
        
        backup_file = self.export_dir / f"complete_backup_{timestamp}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(complete_backup, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Complete backup saved to: {backup_file}\n")
    
    def export_single_itinerary(self, itin_id=None):
        """Export specific itinerary."""
        if itin_id is None:
            itin_id = input("\nEnter itinerary ID to export: ").strip()
            if not itin_id.isdigit():
                print("❌ Invalid ID")
                return
            itin_id = int(itin_id)
        
        query = """
            SELECT i.*, t.*
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            WHERE i.id = %s
        """
        result = self.db.execute_query(query, (itin_id,), fetch=True)
        
        if not result:
            print(f"\n❌ Itinerary #{itin_id} not found")
            return
        
        itin = dict(result[0])
        itin['created_at'] = str(itin['created_at'])
        itin['rated_at'] = str(itin['rated_at']) if itin['rated_at'] else None
        
        filename = f"itinerary_{itin_id}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(itin, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Exported to: {filename}\n")
    
    def create_backup(self):
        """Create complete backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path("backups") / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📦 CREATING BACKUP...")
        print(f"Location: {backup_dir}\n")
        
        # Export everything
        self.export_all()
        
        # Copy to backup dir
        import shutil
        for file in self.export_dir.glob("*"):
            shutil.copy(file, backup_dir)
        
        # Create info file
        info = f"""
Backup Created: {datetime.now()}
Location: {backup_dir.absolute()}
Files: {len(list(backup_dir.glob('*')))}
"""
        (backup_dir / "backup_info.txt").write_text(info)
        
        print(f"✅ Backup complete: {backup_dir}\n")
    
    def view_local_json(self):
        """View local JSON files."""
        data_dir = Path("data")
        
        if not data_dir.exists():
            print("\n❌ No data directory found\n")
            return
        
        json_files = list(data_dir.glob("*.json"))
        archive_dir = data_dir / "archive"
        if archive_dir.exists():
            json_files.extend(list(archive_dir.glob("*.json")))
        
        print(f"\n📁 Found {len(json_files)} local JSON files:\n")
        
        for json_file in json_files:
            print(f"📄 {json_file.name}")
            print(f"   Path: {json_file}")
            print(f"   Size: {json_file.stat().st_size / 1024:.2f} KB")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    print(f"   Type: Dictionary with {len(data)} entries")
                elif isinstance(data, list):
                    print(f"   Type: List with {len(data)} entries")
                print()
            except Exception as e:
                print(f"   ❌ Error: {e}\n")
    
    def view_training_data(self):
        """View training data."""
        query = """
            SELECT 
                id, itinerary_id, quality_score, is_high_quality, created_at
            FROM training_data
            ORDER BY created_at DESC
            LIMIT 20
        """
        results = self.db.execute_query(query, fetch=True)
        
        print(f"\n🧠 Training Data (last 20):\n")
        print(f"{'ID':<8} {'Itin ID':<10} {'Quality':<10} {'High Quality':<15} {'Created'}")
        print("-" * 70)
        
        for r in results:
            hq = "✅ Yes" if r['is_high_quality'] else "❌ No"
            created = r['created_at'].strftime('%Y-%m-%d') if r['created_at'] else 'N/A'
            print(f"{r['id']:<8} {r['itinerary_id']:<10} {r['quality_score']:<10.2f} {hq:<15} {created}")
        
        print()
    
    def training_statistics(self):
        """Training statistics."""
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_high_quality = TRUE) as high_quality,
                AVG(quality_score) as avg_score
            FROM training_data
        """
        result = self.db.execute_query(query, fetch=True)
        
        if result:
            stats = result[0]
            print(f"\n🧠 TRAINING STATISTICS:")
            print(f"   Total Samples: {stats['total']}")
            print(f"   High Quality: {stats['high_quality']}")
            print(f"   Average Score: {stats['avg_score']:.2f}" if stats['avg_score'] else "   Average Score: N/A")
            
            if stats['total'] > 0:
                hq_percent = (stats['high_quality'] / stats['total']) * 100
                print(f"   Quality Rate: {hq_percent:.1f}%")
            
            # Training readiness
            if stats['high_quality'] >= 3:
                print(f"\n   ✅ Ready for training! ({stats['high_quality']} samples)")
            else:
                print(f"\n   ⏳ Need {3 - stats['high_quality']} more high-quality samples")
        
        print()
    
    def custom_query(self):
        """Execute custom PostgreSQL query."""
        print("\n💡 Enter your SQL query (or 'back' to return):")
        print("Example: SELECT * FROM itineraries LIMIT 5;\n")
        
        query = input("Query: ").strip()
        
        if query.lower() == 'back':
            return
        
        try:
            results = self.db.execute_query(query, fetch=True)
            
            if results:
                print(f"\n✅ Query returned {len(results)} rows:\n")
                print(json.dumps(results[:10], indent=2, default=str))
                if len(results) > 10:
                    print(f"\n... and {len(results) - 10} more rows")
            else:
                print("\n✅ Query executed successfully (no results)")
            
            print()
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
    
    def bulk_export_csv(self):
        """Export to CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"itineraries_{timestamp}.csv"
        
        query = """
            SELECT 
                i.id, t.destination, t.duration, t.budget_level,
                i.rating, i.word_count, i.created_at
            FROM itineraries i
            JOIN trips t ON i.trip_id = t.id
            ORDER BY i.created_at DESC
        """
        results = self.db.execute_query(query, fetch=True)
        
        import csv
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
        
        print(f"\n✅ Exported {len(results)} rows to: {filename}\n")
    
    def run(self):
        """Main loop."""
        print("\n🎉 Welcome to Ultimate Data Manager!")
        
        try:
            while True:
                self.show_menu()
                choice = input("Select option (0-15): ").strip()
                
                if choice == '1':
                    self.list_itineraries()
                elif choice == '2':
                    self.view_itinerary()
                elif choice == '3':
                    self.view_all_data()
                elif choice == '4':
                    self.show_statistics()
                elif choice == '5':
                    self.search_destination()
                elif choice == '6':
                    self.filter_by_rating()
                elif choice == '7':
                    self.recent_itineraries()
                elif choice == '8':
                    self.export_all()
                elif choice == '9':
                    self.export_single_itinerary()
                elif choice == '10':
                    self.create_backup()
                elif choice == '11':
                    self.view_local_json()
                elif choice == '12':
                    self.view_training_data()
                elif choice == '13':
                    self.training_statistics()
                elif choice == '14':
                    self.custom_query()
                elif choice == '15':
                    self.bulk_export_csv()
                elif choice == '0':
                    print("\n👋 Goodbye!\n")
                    break
                else:
                    print("\n❌ Invalid option. Try again.")
        
        finally:
            self.db.close()

if __name__ == "__main__":
    manager = DataManager()
    manager.run()
