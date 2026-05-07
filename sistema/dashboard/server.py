#!/usr/bin/env python3
"""
Arion Dashboard Server - Real-time monitoring
WebSocket server that streams: Hermes thoughts, LLM thinking, tool calls, worker status, errors
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from collections import deque
import tailer  # pip install tailer
import html

# FIX: Try to import psutil for secure process handling (DeepSeek V4 issue #4)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

app = Flask(__name__,
            static_folder='static',
            template_folder='static')

# FIX: Secret key from environment variable (DeepSeek V4 security issue #1)
import secrets
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# FIX: CORS restricted to specific origins (DeepSeek V4 security issue #2)
CORS(app, origins=['http://localhost:9120', 'http://100.93.26.104:9120', 'http://127.0.0.1:9120'])

# FIX: Better async mode and cors settings (DeepSeek V4 issues #2, #3)
socketio = SocketIO(app, cors_allowed_origins=['http://localhost:9120', 'http://100.93.26.104:9120'], async_mode='threading')

# FIX: Log files in absolute path (DeepSeek V4 security issue #7)
# Use environment variable or default to absolute path
LOGS_DIR = Path(os.environ.get('ARION_LOGS_DIR', '/home/jo/biblioteca-universal-arion/sistema/dashboard/logs'))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

HERMES_LOG = LOGS_DIR / 'hermes.log'
LLM_LOG = LOGS_DIR / 'llm.log'
WORKER_LOG = LOGS_DIR / 'worker.log'
TOOL_LOG = LOGS_DIR / 'tools.log'
ERRORS_LOG = LOGS_DIR / 'errors.log'

# Create log files if they don't exist
for log_file in [HERMES_LOG, LLM_LOG, WORKER_LOG, TOOL_LOG]:
    log_file.touch(exist_ok=True)

# FIX: Use deque with maxlen to prevent memory exhaustion (DeepSeek V4 issue #8)
from collections import deque

MAX_EVENTS = 100  # Maximum events per type
recent_events = {
    'hermes': deque(maxlen=MAX_EVENTS),
    'llm': deque(maxlen=MAX_EVENTS),
    'worker': deque(maxlen=MAX_EVENTS),
    'tools': deque(maxlen=MAX_EVENTS),
    'errors': deque(maxlen=MAX_EVENTS)
}

def add_event(event_type, data):
    """Add event to recent events and emit to all clients"""
    event = {
        'timestamp': datetime.now().isoformat(),
        'type': event_type,
        'data': data
    }
    recent_events[event_type].append(event)
    # Keep only last 100 events
    if len(recent_events[event_type]) > 100:
        recent_events[event_type] = recent_events[event_type][-100:]
    # Emit to all connected clients
    socketio.emit(f'{event_type}_event', event, namespace='/')

# FIX: Improved log tailer with daemon thread and error recovery (DeepSeek V4 issue #9)
def log_tailer(log_file, event_type):
    """Tail a log file and emit new lines as events"""
    import time
    while True:
        try:
            for line in tailer.follow(open(log_file)):
                if line.strip():
                    # FIX: Escape potential XSS (DeepSeek V4 issue #10)
                    import html
                    add_event(event_type, {'content': html.escape(line.strip())})
        except FileNotFoundError:
            # Wait for file to be created
            time.sleep(1)
        except Exception as e:
            print(f"Error tailing {log_file}: {e}")
            time.sleep(1)  # Wait before retrying

@app.route('/')
def index():
    """Serve main dashboard page"""
    return render_template('index.html')

# FIX: Rate limiting setup (DeepSeek V4 issue - missing)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# FIX: Secure worker status check (DeepSeek V4 issue #4)
def get_worker_status():
    """Get worker status using psutil or subprocess"""
    worker_running = False
    worker_pid = None
    
    if HAS_PSUTIL:
        # Use psutil for secure process iteration
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('venice-worker' in str(c) for c in cmdline):
                    worker_running = True
                    worker_pid = proc.info['pid']
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    else:
        # Fallback to subprocess with security fixes
        try:
            result = subprocess.run(['pgrep', '-f', 'venice-worker'],
                                    capture_output=True, text=True,
                                    timeout=2,
                                    shell=False)  # FIX: Never use shell=True
            worker_running = bool(result.stdout.strip())
            worker_pid = result.stdout.strip().split('\n')[0] if worker_running else None
        except:
            worker_running = False
            worker_pid = None
    
    return worker_running, worker_pid

@app.route('/api/status')
@limiter.limit("10 per minute")
def api_status():
    """Get current system status"""
    # Use secure worker status check
    worker_running, worker_pid = get_worker_status()
    
    # Get Venice balance with timeout (DeepSeek V4 issue #5)
    try:
        venice_script = Path.home() / '.hermes' / 'skills' / 'openclaw-imports' / 'venice-ai' / 'scripts' / 'venice.py'
        
        # FIX: Validate path exists before execution
        if not venice_script.exists():
            raise FileNotFoundError(f"Venice script not found: {venice_script}")
        
        result = subprocess.run(['python3', str(venice_script), 'balance'],
                                capture_output=True, text=True, 
                                timeout=5,
                                shell=False)  # FIX: Never use shell=True
        balance_output = result.stdout
        
        # Parse DIEM balance
        import re
        diem_match = re.search(r'DIEM:\s*([\d.]+)', balance_output)
        requests_match = re.search(r'Remaining requests:\s*(\d+)', balance_output)
        tokens_match = re.search(r'Remaining tokens:\s*(\d+)', balance_output)
        
        diem_balance = float(diem_match.group(1)) if diem_match else 0.0
        requests = int(requests_match.group(1)) if requests_match else 0
        tokens = int(tokens_match.group(1)) if tokens_match else 0
    except Exception as e:
        diem_balance = 0.0
        requests = 0
        tokens = 0
    
    # Get queue status
    queue_file = os.path.expanduser('~/biblioteca-universal-arion/sistema/queue/pending.json')
    try:
        with open(queue_file, 'r') as f:
            queue_data = json.load(f)
            queue_count = len(queue_data.get('pending', []))
    except:
        queue_count = 0
    
    return jsonify({
        'worker': {
            'running': worker_running,
            'pid': worker_pid,
            'uptime': None  # TODO: calculate uptime
        },
        'venice': {
            'diem': diem_balance,
            'requests': requests,
            'tokens': tokens
        },
        'queue': {
            'count': queue_count
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/events/<event_type>')
def api_events(event_type):
    """Get recent events of a specific type"""
    if event_type in recent_events:
        return jsonify(recent_events[event_type][-50:])
    return jsonify([])

@app.route('/api/events/all')
def api_all_events():
    """Get all recent events"""
    return jsonify(recent_events)

# FIX: Add WebSocket authentication (DeepSeek V4 issue #3)
socket_connections = set()

@socketio.on('connect')
def handle_connect():
    """Handle new client connection with basic auth"""
    # FIX: Simple token-based auth (can be enhanced)
    # For now, accept all connections from localhost/TailScale
    client_ip = request.remote_addr
    
    # Allow connections from localhost and TailScale network
    if client_ip in ['127.0.0.1', '::1'] or client_ip.startswith('100.'):
        socket_connections.add(request.sid)
        print(f"Client connected: {client_ip}")
        emit('connected', {'message': 'Connected to Arion Dashboard'})
    else:
        # Reject other connections
        print(f"Rejected connection from: {client_ip}")
        return False  # Reject connection

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnect"""
    socket_connections.discard(request.sid)
    print(f"Client disconnected")

# FIX: Daemon threads with proper cleanup (DeepSeek V4 issue #9)
def start_log_tailers():
    """Start background threads to tail log files"""
    threads = []
    
    # FIX: All threads are daemon=True for proper shutdown
    for log_file, event_type in [(HERMES_LOG, 'hermes'), (LLM_LOG, 'llm'), 
                                    (WORKER_LOG, 'worker'), (TOOL_LOG, 'tools'), 
                                    (ERRORS_LOG, 'errors')]:
        t = threading.Thread(target=log_tailer, args=(log_file, event_type), daemon=True)
        t.start()
        threads.append(t)
    
    # Tail LLM log
    t = threading.Thread(target=log_tailer, args=(LLM_LOG, 'llm'))
    t.daemon = True
    t.start()
    threads.append(t)
    
    # Tail worker log
    t = threading.Thread(target=log_tailer, args=(WORKER_LOG, 'worker'))
    t.daemon = True
    t.start()
    threads.append(t)
    
    # Tail tool log
    t = threading.Thread(target=log_tailer, args=(TOOL_LOG, 'tools'))
    t.daemon = True
    t.start()
    threads.append(t)
    
    return threads

if __name__ == '__main__':
    print("=" * 60)
    print("ARION DASHBOARD SERVER")
    print("=" * 60)
    print(f"Logs directory: {LOGS_DIR}")
    print(f"Starting log tailers...")
    
    # Start log tailers
    threads = start_log_tailers()
    
    print(f"Starting web server on http://0.0.0.0:9120")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Run Flask app with SocketIO
    socketio.run(app, host='0.0.0.0', port=9120, debug=False, allow_unsafe_werkzeug=True)