#!venv/Scripts/python.exe
"""Quick cloud database stats check."""

import os
import sys

# Ensure we're using venv
venv_python = os.path.join(os.path.dirname(__file__), 'venv', 'Scripts', 'python.exe')
if sys.executable != venv_python and os.path.exists(venv_python):
    import subprocess
    subprocess.run([venv_python, __file__])
    sys.exit()

# Set Neon connection
os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_s0XZcOJvyT6n@ep-solitary-wildflower-a19w99a3-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

from src.database.db_manager import DatabaseManager

db = DatabaseManager()
stats = db.get_statistics()

print('\n📊 Cloud Database Stats:')
print(f'   Total Trips: {stats.get("total_trips", 0)}')
print(f'   Total Itineraries: {stats.get("total_itineraries", 0)}')
print(f'   Total Ratings: {stats.get("total_ratings", 0)}')
print(f'   Training Cycles: {stats.get("training_cycles_completed", 0)}')

db.close()
print()
