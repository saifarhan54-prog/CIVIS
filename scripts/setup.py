"""
Complete CIVIS setup script
"""
import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*80}")
    print(f"⚙️  {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, 
                              capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        print(e.stderr)
        return False

def main():
    """Run complete setup"""
    print("="*80)
    print("🚀 CIVIS Complete Setup")
    print("="*80)
    
    steps = [
        ("python scripts/init_db.py", "Initializing database"),
        ("python scripts/download_models.py", "Downloading AI models"),
        ("python scripts/generate_demo_videos.py", "Generating demo videos"),
    ]
    
    results = []
    for cmd, desc in steps:
        success = run_command(cmd, desc)
        results.append((desc, success))
    
    print("\n" + "="*80)
    print("Setup Summary")
    print("="*80)
    
    for desc, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {desc}")
    
    if all(s for _, s in results):
        print("\n🎉 CIVIS setup completed successfully!")
        print("\nNext steps:")
        print("1. cd backend")
        print("2. uvicorn main_enhanced:app --reload")
        print("3. Open http://localhost:8000/docs")
    else:
        print("\n⚠️  Some setup steps failed. Check errors above.")

if __name__ == "__main__":
    main()
