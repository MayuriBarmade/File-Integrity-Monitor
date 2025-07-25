#!/usr/bin/env python3
"""
FIM System Startup Script
Starts both the web dashboard and desktop notification service
"""

import os
import sys
import time
import threading
import subprocess
import platform
from pathlib import Path

def start_web_dashboard():
    """Start the Flask web dashboard"""
    print("🌐 Starting FIM Web Dashboard...")
    try:
        # Run app.py
        subprocess.run([sys.executable, "app.py"], check=True)
    except KeyboardInterrupt:
        print("🛑 Web dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting web dashboard: {e}")

def start_desktop_notifier():
    """Start the desktop notification service"""
    print("🔔 Starting Desktop Notification Service...")
    time.sleep(3)  # Wait for web dashboard to create data directory
    
    try:
        # Run desktop_notifier.py
        subprocess.run([sys.executable, "desktop_notifier.py"], check=True)
    except KeyboardInterrupt:
        print("🛑 Desktop notifier stopped by user")
    except Exception as e:
        print(f"❌ Error starting desktop notifier: {e}")

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = ["flask", "watchdog"]
    system = platform.system()
    
    if system == "Windows":
        required_packages.extend(["win10toast", "plyer"])
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Missing")
    
    if missing_packages:
        print(f"\n📦 Installing missing packages: {', '.join(missing_packages)}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages, check=True)
            print("✅ All packages installed successfully!")
        except Exception as e:
            print(f"❌ Failed to install packages: {e}")
            print("💡 Try running manually: pip install " + " ".join(missing_packages))
            return False
    
    return True

def create_directory_structure():
    """Create necessary directories"""
    directories = ["templates", "data"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Directory created/verified: {directory}")

def check_files():
    """Check if all required files exist"""
    required_files = {
        "app.py": "Main Flask application",
        "templates/dashboard.html": "Web dashboard template",
        "desktop_notifier.py": "Desktop notification service"
    }
    
    missing_files = []
    
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            print(f"✅ {file_path} - {description}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path} - Missing {description}")
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        print("💡 Make sure you have created all the required files")
        return False
    
    return True

def show_usage_instructions():
    """Show instructions for using the FIM system"""
    print("\n" + "="*60)
    print("🛡️  FILE INTEGRITY MONITOR - USAGE INSTRUCTIONS")
    print("="*60)
    print("📊 Web Dashboard: http://localhost:5000")
    print("🔔 Desktop notifications will appear system-wide")
    print("📁 Test folder: ~/Documents/test_fim")
    print("")
    print("🎯 How to test:")
    print("1. Create files in your test folder")
    print("2. Modify existing files")
    print("3. Delete files")
    print("4. Watch for notifications!")
    print("")
    print("⌨️  Keyboard shortcuts (in web dashboard):")
    print("• Ctrl+S: Toggle sound alerts")
    print("• Ctrl+L: Toggle live alert feed")
    print("• Escape: Close popup alerts")
    print("")
    print("📱 Notification levels:")
    print("• 🚨 Critical: Full popup + desktop + sound")
    print("• ⚠️  High: Desktop notification + sound")  
    print("• ℹ️  Medium: Desktop notification only")
    print("• ✅ Low: Toast notification only")
    print("")
    print("🛑 To stop: Press Ctrl+C in this terminal")
    print("="*60 + "\n")

def main():
    """Main startup function"""
    print("🚀 FIM SYSTEM STARTUP")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Create directories
    create_directory_structure()
    
    # Check required files
    if not check_files():
        print("\n💡 Please create the missing files and try again.")
        return
    
    # Show usage instructions
    show_usage_instructions()
    
    try:
        # Start web dashboard in a separate thread
        web_thread = threading.Thread(target=start_web_dashboard, daemon=True)
        web_thread.start()
        
        # Wait a moment for web server to start
        time.sleep(2)
        
        # Start desktop notifier (this will run in main thread)
        start_desktop_notifier()
        
    except KeyboardInterrupt:
        print("\n🛑 FIM System shutdown requested")
        print("✅ All services stopped")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("FIM System Startup Script")
            print("Usage:")
            print("  python start_fim.py          # Start FIM system")
            print("  python start_fim.py --help   # Show this help")
            print("")
            print("This script will:")
            print("• Check and install dependencies")
            print("• Start the web dashboard (Flask)")
            print("• Start desktop notification service")
            print("• Show usage instructions")
        else:
            print("Unknown argument. Use --help for usage information.")
    else:
        main()