from flask import Flask, render_template, jsonify, request
import os
import json
import hashlib
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time

app = Flask(__name__)

# Global variables
file_records = {}
change_events = []
monitored_paths = []
observer = None

def load_data():
    """Load data from JSON files"""
    global file_records, change_events, monitored_paths
    
    try:
        with open('data/files.json', 'r') as f:
            file_records = json.load(f)
    except:
        file_records = {}
    
    try:
        with open('data/events.json', 'r') as f:
            change_events = json.load(f)
    except:
        change_events = []
    
    try:
        with open('data/config.json', 'r') as f:
            monitored_paths = json.load(f)
    except:
        monitored_paths = []

def save_data():
    """Save data to JSON files"""
    os.makedirs('data', exist_ok=True)
    
    with open('data/files.json', 'w') as f:
        json.dump(file_records, f, indent=2, default=str)
    
    with open('data/events.json', 'w') as f:
        json.dump(change_events, f, indent=2, default=str)
    
    with open('data/config.json', 'w') as f:
        json.dump(monitored_paths, f, indent=2)

def calculate_hash(file_path):
    """Calculate SHA-256 hash"""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except:
        return None

def get_severity(file_path, event_type):
    """Determine severity based on file path and event type"""
    critical_files = ['/etc/passwd', '/etc/shadow', 'hosts', '.conf', '.key', '.exe', '.dll']
    if any(critical in file_path.lower() for critical in critical_files):
        return 'critical'
    if event_type == 'deleted':
        return 'high'
    if event_type == 'created':
        return 'medium'
    return 'medium'

class FIMHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        
        # Skip temporary files
        if any(temp in event.src_path for temp in ['.tmp', '~', '.swp']):
            return
            
        event_data = {
            'id': len(change_events) + 1,
            'file_path': event.src_path,
            'event_type': event.event_type,
            'timestamp': datetime.now().isoformat(),
            'severity': get_severity(event.src_path, event.event_type),
            'old_hash': file_records.get(event.src_path, {}).get('hash'),
            'new_hash': calculate_hash(event.src_path) if event.event_type != 'deleted' else None
        }
        
        change_events.append(event_data)
        
        # Keep only last 1000 events to prevent memory issues
        if len(change_events) > 1000:
            change_events[:] = change_events[-1000:]
        
        # Update file record
        if event.event_type != 'deleted' and event_data['new_hash']:
            file_records[event.src_path] = {
                'hash': event_data['new_hash'],
                'size': os.path.getsize(event.src_path) if os.path.exists(event.src_path) else 0,
                'last_check': datetime.now().isoformat(),
                'permissions': oct(os.stat(event.src_path).st_mode)[-3:] if os.path.exists(event.src_path) else None
            }
        elif event.event_type == 'deleted' and event.src_path in file_records:
            del file_records[event.src_path]
        
        save_data()
        print(f"🚨 {event_data['severity'].upper()}: {event.event_type} - {os.path.basename(event.src_path)}")

def start_monitoring():
    """Start file monitoring"""
    global observer
    if observer:
        return
    
    observer = Observer()
    handler = FIMHandler()
    
    # Monitor default paths - Windows compatible
    default_paths = [
        os.path.expanduser('~/Documents/test_fim'),  # Our test folder
        os.path.expanduser('~/Downloads'),           # Downloads folder
    ]
    
    for path in default_paths:
        if os.path.exists(path):
            try:
                observer.schedule(handler, path, recursive=True)
                if path not in monitored_paths:
                    monitored_paths.append(path)
                print(f"✅ Monitoring: {path}")
            except Exception as e:
                print(f"❌ Could not monitor {path}: {e}")
    
    try:
        observer.start()
        print("🔍 File monitoring started!")
    except Exception as e:
        print(f"❌ Failed to start monitoring: {e}")
    
    save_data()

# Flask Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/events')
def get_events():
    """Get recent events"""
    return jsonify(change_events[-50:])  # Last 50 events

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    total_files = len(file_records)
    total_events = len(change_events)
    
    # Count by severity
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for event in change_events:
        severity = event.get('severity', 'medium')
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Recent activity (last hour)
    recent_events = [e for e in change_events 
                    if (datetime.now() - datetime.fromisoformat(e['timestamp'])).seconds < 3600]
    
    return jsonify({
        'total_files': total_files,
        'total_events': total_events,
        'monitored_paths': len(monitored_paths),
        'severity_counts': severity_counts,
        'paths': monitored_paths,
        'recent_activity': len(recent_events),
        'system_status': 'active' if observer and observer.is_alive() else 'inactive'
    })

@app.route('/api/add_path', methods=['POST'])
def add_monitoring_path():
    """Add new path to monitor"""
    path = request.json.get('path')
    if not path:
        return jsonify({'success': False, 'error': 'Path is required'})
    
    # Expand user path for Windows
    expanded_path = os.path.expanduser(path)
    
    if not os.path.exists(expanded_path):
        return jsonify({'success': False, 'error': 'Path does not exist'})
    
    if expanded_path in monitored_paths:
        return jsonify({'success': False, 'error': 'Path already monitored'})
    
    try:
        if observer:
            handler = FIMHandler()
            observer.schedule(handler, expanded_path, recursive=True)
        
        monitored_paths.append(expanded_path)
        save_data()
        return jsonify({'success': True, 'path': expanded_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/remove_path', methods=['POST'])
def remove_monitoring_path():
    """Remove path from monitoring"""
    path = request.json.get('path')
    if path in monitored_paths:
        monitored_paths.remove(path)
        save_data()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Path not found'})

@app.route('/api/clear_events', methods=['POST'])
def clear_events():
    """Clear all events"""
    global change_events
    change_events = []
    save_data()
    return jsonify({'success': True})

if __name__ == '__main__':
    print("🚀 Starting File Integrity Monitoring System...")
    
    # Load existing data
    load_data()
    
    # Start monitoring in background thread
    monitoring_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitoring_thread.start()
    
    print("🌐 Web dashboard will be available at: http://localhost:5000")
    print("📁 Create/modify files in your test folder to see alerts!")
    print("📍 Test folder location: ~/Documents/test_fim")
    
    # Start Flask app
    app.run(debug=True, port=5000, use_reloader=False)
app.py

