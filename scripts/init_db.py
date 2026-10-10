"""
Initialize CIVIS database
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database.db_manager import DatabaseManager

def main():
    """Initialize database with schema"""
    print("="*80)
    print("CIVIS Database Initialization")
    print("="*80)
    
    db = DatabaseManager()
    
    print("📊 Creating database tables...")
    db.init_database()
    
    print("\n✅ Database initialized successfully!")
    print(f"   Location: {db.db_path}")
    print("\nTables created:")
    print("  - events")
    print("  - zones")
    print("  - vehicles")
    print("  - faces")
    print("  - access_logs")
    print("  - behavioral_events")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
