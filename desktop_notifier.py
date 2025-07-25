#!/usr/bin/env python3
"""
Desktop Notification Service for FIM
Runs as a background service to show system-level notifications
"""

import os
import sys
import time
import json
import threading
import platform
from datetime import datetime

# Cross-platform notification imports
try:
    if platform.system() == "Windows":
        import win10toast
        from plyer import notification
    elif platform.system() == "Darwin":  # macOS
        import subprocess
    else:  # Linux
        import subprocess
except ImportError as e:
    print(f"Installing required packages: {e}")
    os.system("pip install win10toast plyer")

class DesktopNotifier:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.events_file = os.path.join(data_dir, "events.json")
        self.last_event_count = 0
        self.running = False
        self.system = platform.system()
        
        # Initialize Windows toast notifier
        if self.system == "Windows":
            try:
                self.toaster = win10toast.ToastNotifier()
            except:
                self.toaster = None
                print("Windows Toast notifications not available, using fallback")
    
    def show_notification(self, title, message, severity="medium", duration=10):
        """Show system notification based on OS"""
        
        # Define icons based on severity
        icon_map = {
            "critical": "🚨",
            "high": "⚠️", 
            "medium": "ℹ️",
            "low": "✅"
        }
        
        icon = icon_map.get(severity, "ℹ️")
        full_title = f"{icon} FIM Alert - {severity.upper()}"
        
        if self.system == "Windows":
            self._show_windows_notification(full_title, message, severity, duration)
        elif self.system == "Darwin":
            self._show_macos_notification(full_title, message, duration)
        else:
            self._show_linux_notification(full_title, message, duration)
    
    def _show_windows_notification(self, title, message, severity, duration):
        """Windows notification using win10toast and plyer"""
        try:
            # Try win10toast first (better for Windows 10/11)
            if self.toaster:
                self.toaster.show_toast(
                    title=title,
                    msg=message,
                    duration=duration,
                    icon_path=None,  # Uses default system icon
                    threaded=True
                )
            else:
                # Fallback to plyer
                notification.notify(
                    title=title,
                    message=message,
                    timeout=duration,
                    app_name="FIM Security Monitor"
                )
        except Exception as e:
            print(f"Windows notification error: {e}")
            self._show_console_notification(title, message)
    
    def _show_macos_notification(self, title, message, duration):
        """macOS notification using osascript"""
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(["osascript", "-e", script], check=True)
        except Exception as e:
            print(f"macOS notification error: {e}")
            self._show_console_notification(title, message)
    
    def _show_linux_notification(self, title, message, duration):
        """Linux notification using notify-send"""
        try:
            # Try notify-send first
            subprocess.run([
                "notify-send", 
                "--urgency=critical" if "CRITICAL" in title else "--urgency=normal",
                "--expire-time=" + str(duration * 1000),
                "--app-name=FIM Security Monitor",
                title, 
                message
            ], check=True)
        except FileNotFoundError:
            try:
                # Fallback to zenity
                subprocess.run([
                    "zenity", "--notification", 
                    "--text=" + f"{title}\n{message}"
                ], check=True)
            except FileNotFoundError:
                print("No notification system found on Linux")
                self._show_console_notification(title, message)
        except Exception as e:
            print(f"Linux notification error: {e}")
            self._show_console_notification(title, message)
    
    def _show_console_notification(self, title, message):
        """Fallback console notification with visual alert"""
        print("\n" + "="*60)
        print(f"🚨 {title}")
        print("-" * 60)
        print(message)
        print("="*60 + "\n")
        
        # Console beep for audio alert
        try:
            if self.system == "Windows":
                import winsound
                winsound.Beep(1000, 500)  # 1000 Hz for 500ms
            else:
                print("\a")  # Terminal bell
        except:
            pass
    
    def load_events(self):
        """Load events from JSON file"""
        try:
            if os.path.exists(self.events_file):
                with open(self.events_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading events: {e}")
            return []
    
    def check_for_new_events(self):
        """Check for new events and show notifications"""
        events = self.load_events()
        
        if len(events) > self.last_event_count:
            new_events = events[self.last_event_count:]
            
            for event in new_events:
                file_path = event.get('file_path', 'Unknown file')
                event_type = event.get('event_type', 'unknown')
                severity = event.get('severity', 'medium')
                timestamp = event.get('timestamp', datetime.now().isoformat())
                
                # Extract filename for cleaner notification
                filename = os.path.basename(file_path)
                
                # Create notification message
                message = f"""File: {filename}
Event: {event_type.upper()}
Time: {datetime.fromisoformat(timestamp).strftime('%H:%M:%S')}
Path: {file_path}"""
                
                # Show notification based on severity
                if severity in ['critical', 'high']:
                    duration = 15 if severity == 'critical' else 10
                else:
                    duration = 5
                
                self.show_notification(
                    title=f"File {event_type.title()}",
                    message=message,
                    severity=severity,
                    duration=duration
                )
                
                print(f"📢 Notification sent: {event_type} - {filename} ({severity})")
            
            self.last_event_count = len(events)
    
    def start_monitoring(self):
        """Start the notification monitoring service"""
        print("🚀 Starting FIM Desktop Notification Service...")
        print(f"📍 Platform: {self.system}")
        print(f"📁 Monitoring: {self.events_file}")
        print("🔔 Desktop notifications enabled")
        print("Press Ctrl+C to stop\n")
        
        self.running = True
        
        # Initial load
        self.last_event_count = len(self.load_events())
        
        try:
            while self.running:
                self.check_for_new_events()
                time.sleep(2)  # Check every 2 seconds
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping notification service...")
            self.running = False
        except Exception as e:
            print(f"❌ Error in monitoring: {e}")
    
    def stop_monitoring(self):
        """Stop the monitoring service"""
        self.running = False

def install_dependencies():
    """Install required dependencies based on platform"""
    system = platform.system()
    
    if system == "Windows":
        os.system("pip install win10toast plyer")
    elif system == "Linux":
        print("For Linux notifications, ensure 'notify-send' or 'zenity' is installed:")
        print("Ubuntu/Debian: sudo apt-get install libnotify-bin zenity")
        print("Fedora/RHEL: sudo dnf install libnotify zenity")
        print("Arch: sudo pacman -S libnotify zenity")
    elif system == "Darwin":
        print("macOS notifications use built-in osascript - no additional packages needed")

def run_as_service():
    """Run the notifier as a background service"""
    print("🔧 FIM Desktop Notification Service v1.0")
    print("=" * 50)
    
    # Check if data directory exists
    if not os.path.exists("data"):
        print("❌ Data directory not found. Make sure FIM app is running first.")
        print("💡 Start app.py first to create the data directory.")
        return
    
    notifier = DesktopNotifier()
    
    try:
        notifier.start_monitoring()
    except Exception as e:
        print(f"❌ Failed to start notification service: {e}")
        print("💡 Try running: pip install win10toast plyer")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        install_dependencies()
    else:
        run_as_service()