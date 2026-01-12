---
description: "SocketIO patterns for real-time progress tracking in TickZen automation"
alwaysApply: false
globs:
  - "**/main_portal_app.py"
  - "**/automation_scripts/*.py"
  - "**/*publisher*.py"
  - "**/templates/run_automation*.html"
---

# TickZen SocketIO Patterns

## Architecture Overview

TickZen uses Flask-SocketIO with `async_mode='threading'` for real-time progress updates during:
- Stock analysis automation
- Earnings report generation
- Sports article publishing

## Core Principles

1. **Always emit to user's room** - Never broadcast globally
2. **Use structured progress events** - Consistent JSON schema
3. **Handle disconnections gracefully** - Store state in Firestore
4. **Progress granularity** - Emit every 5-10% or major milestone
5. **Error states visible** - Emit errors immediately with retry options

## Server-Side Patterns

### Import & Configuration
```python
from flask_socketio import SocketIO, emit, join_room, leave_room

# Initialize SocketIO (in main_portal_app.py)
socketio = SocketIO(
    app,
    async_mode='threading',
    cors_allowed_origins='*',
    ping_timeout=60,
    ping_interval=25,
    logger=True,
    engineio_logger=False
)
```

### Connection Handling
```python
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    try:
        # Get user from session (if using Flask-Login)
        user_id = session.get('user_id', 'anonymous')
        
        # Join user-specific room
        join_room(f"user_{user_id}")
        
        app.logger.info(f"Client connected: {request.sid}, User: {user_id}")
        
        emit('connection_status', {
            'status': 'connected',
            'message': 'Connected to TickZen automation server',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Connection error: {e}", exc_info=True)
        emit('error', {'message': 'Connection failed'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    try:
        user_id = session.get('user_id', 'anonymous')
        leave_room(f"user_{user_id}")
        
        app.logger.info(f"Client disconnected: {request.sid}, User: {user_id}")
        
    except Exception as e:
        app.logger.error(f"Disconnect error: {e}", exc_info=True)
```

### Progress Emission Pattern
```python
def emit_progress(user_id, stage, message, percent=None, data=None):
    """
    Standardized progress emission
    
    Args:
        user_id: User identifier
        stage: 'initializing', 'processing', 'publishing', 'complete', 'error'
        message: Human-readable status message
        percent: Progress percentage (0-100)
        data: Additional context (dict)
    """
    try:
        progress_event = {
            'stage': stage,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if percent is not None:
            progress_event['percent'] = min(max(int(percent), 0), 100)
        
        if data:
            progress_event['data'] = data
        
        # Emit to user's room
        socketio.emit(
            'automation_progress',
            progress_event,
            room=f"user_{user_id}"
        )
        
        app.logger.info(f"Progress [{user_id}]: {stage} - {message} ({percent}%)")
        
    except Exception as e:
        app.logger.error(f"Error emitting progress: {e}", exc_info=True)
```

### Automation Workflow Example
```python
def run_stock_automation(user_id, tickers, profile_id):
    """Stock automation with SocketIO progress"""
    try:
        total_tickers = len(tickers)
        
        # Stage 1: Initialization
        emit_progress(user_id, 'initializing', 
                     f'Starting automation for {total_tickers} tickers', 
                     percent=0,
                     data={'total_tickers': total_tickers})
        
        # Stage 2: Processing each ticker
        for idx, ticker in enumerate(tickers):
            current_percent = int((idx / total_tickers) * 80)  # 0-80% for processing
            
            emit_progress(user_id, 'processing',
                         f'Analyzing {ticker}...',
                         percent=current_percent,
                         data={'ticker': ticker, 'index': idx + 1})
            
            try:
                # Generate report
                report_path = generate_stock_report(ticker)
                
                # Publish to WordPress
                emit_progress(user_id, 'publishing',
                             f'Publishing {ticker} to WordPress...',
                             percent=current_percent + 5,
                             data={'ticker': ticker})
                
                post_id = publish_to_wordpress(ticker, report_path, profile_id)
                
                # Update Firestore
                save_ticker_status(user_id, profile_id, ticker, {
                    'status': 'completed',
                    'wordpressPostId': post_id,
                    'publishedDate': firestore.SERVER_TIMESTAMP
                })
                
                emit_progress(user_id, 'processing',
                             f'✓ {ticker} published successfully',
                             percent=current_percent + 10,
                             data={'ticker': ticker, 'post_id': post_id, 'success': True})
                
            except Exception as ticker_error:
                app.logger.error(f"Error processing {ticker}: {ticker_error}")
                
                # Emit error for this ticker
                emit_progress(user_id, 'error',
                             f'✗ Failed to publish {ticker}: {str(ticker_error)}',
                             percent=current_percent,
                             data={'ticker': ticker, 'error': str(ticker_error), 'success': False})
                
                # Continue with next ticker
                continue
        
        # Stage 3: Completion
        emit_progress(user_id, 'complete',
                     f'Automation complete! Processed {total_tickers} tickers',
                     percent=100,
                     data={'total_tickers': total_tickers})
        
    except Exception as e:
        app.logger.error(f"Automation failed: {e}", exc_info=True)
        
        emit_progress(user_id, 'error',
                     f'Automation failed: {str(e)}',
                     percent=0,
                     data={'error': str(e)})
```

### Background Task Pattern
```python
from threading import Thread

@app.route('/start-automation', methods=['POST'])
def start_automation():
    """Start automation in background thread"""
    try:
        user_id = session.get('user_id')
        tickers = request.json.get('tickers', [])
        profile_id = request.json.get('profile_id')
        
        # Validate inputs
        if not tickers:
            return jsonify({'error': 'No tickers provided'}), 400
        
        # Start background thread
        thread = Thread(
            target=run_stock_automation,
            args=(user_id, tickers, profile_id)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'message': f'Automation started for {len(tickers)} tickers'
        })
        
    except Exception as e:
        app.logger.error(f"Error starting automation: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
```

### Custom Event Handlers
```python
@socketio.on('pause_automation')
def handle_pause(data):
    """Pause automation (store state in Firestore)"""
    try:
        user_id = session.get('user_id')
        automation_id = data.get('automation_id')
        
        # Save pause state to Firestore
        save_automation_state(user_id, automation_id, 'paused')
        
        emit('automation_paused', {
            'message': 'Automation paused',
            'automation_id': automation_id
        }, room=f"user_{user_id}")
        
    except Exception as e:
        app.logger.error(f"Pause error: {e}", exc_info=True)
        emit('error', {'message': 'Failed to pause'})

@socketio.on('resume_automation')
def handle_resume(data):
    """Resume automation"""
    try:
        user_id = session.get('user_id')
        automation_id = data.get('automation_id')
        
        # Load state from Firestore
        state = get_automation_state(user_id, automation_id)
        
        if state and state.get('status') == 'paused':
            # Resume from where it stopped
            remaining_tickers = state.get('remaining_tickers', [])
            profile_id = state.get('profile_id')
            
            thread = Thread(
                target=run_stock_automation,
                args=(user_id, remaining_tickers, profile_id)
            )
            thread.daemon = True
            thread.start()
            
            emit('automation_resumed', {
                'message': 'Automation resumed',
                'remaining_count': len(remaining_tickers)
            }, room=f"user_{user_id}")
        
    except Exception as e:
        app.logger.error(f"Resume error: {e}", exc_info=True)
        emit('error', {'message': 'Failed to resume'})
```

## Client-Side Patterns (JavaScript)

### Connection Setup
```javascript
// In run_automation_page.html
<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
<script>
const socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000
});

// Connection events
socket.on('connect', function() {
    console.log('Connected to server');
    updateConnectionStatus('connected');
});

socket.on('disconnect', function() {
    console.log('Disconnected from server');
    updateConnectionStatus('disconnected');
});

socket.on('connect_error', function(error) {
    console.error('Connection error:', error);
    updateConnectionStatus('error');
});
</script>
```

### Progress Handling
```javascript
// Progress bar element
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressLog = document.getElementById('progress-log');

// Listen for progress events
socket.on('automation_progress', function(data) {
    const { stage, message, percent, data: eventData } = data;
    
    // Update progress bar
    if (percent !== undefined) {
        progressBar.style.width = percent + '%';
        progressBar.setAttribute('aria-valuenow', percent);
    }
    
    // Update progress text
    progressText.textContent = message;
    
    // Add to log
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${stage}`;
    logEntry.innerHTML = `
        <span class="timestamp">${new Date(data.timestamp).toLocaleTimeString()}</span>
        <span class="message">${message}</span>
    `;
    progressLog.appendChild(logEntry);
    
    // Auto-scroll to bottom
    progressLog.scrollTop = progressLog.scrollHeight;
    
    // Handle stage-specific UI updates
    switch(stage) {
        case 'initializing':
            progressBar.className = 'progress-bar bg-info';
            break;
        case 'processing':
            progressBar.className = 'progress-bar bg-primary';
            break;
        case 'publishing':
            progressBar.className = 'progress-bar bg-warning';
            break;
        case 'complete':
            progressBar.className = 'progress-bar bg-success';
            showCompletionModal(eventData);
            break;
        case 'error':
            progressBar.className = 'progress-bar bg-danger';
            showErrorModal(eventData);
            break;
    }
});
```

### Starting Automation
```javascript
function startAutomation() {
    const tickers = getSelectedTickers();
    const profileId = document.getElementById('profile-select').value;
    
    if (!tickers.length) {
        alert('Please select at least one ticker');
        return;
    }
    
    // Clear previous logs
    progressLog.innerHTML = '';
    progressBar.style.width = '0%';
    
    // Send request to start automation
    fetch('/start-automation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            tickers: tickers,
            profile_id: profileId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            console.log('Automation started:', data.message);
            // Progress will come through SocketIO events
        }
    })
    .catch(error => {
        console.error('Error starting automation:', error);
        alert('Failed to start automation');
    });
}
```

### Pause/Resume
```javascript
function pauseAutomation() {
    socket.emit('pause_automation', {
        automation_id: currentAutomationId
    });
}

function resumeAutomation() {
    socket.emit('resume_automation', {
        automation_id: currentAutomationId
    });
}

socket.on('automation_paused', function(data) {
    document.getElementById('pause-btn').style.display = 'none';
    document.getElementById('resume-btn').style.display = 'inline-block';
    console.log('Automation paused:', data.message);
});

socket.on('automation_resumed', function(data) {
    document.getElementById('pause-btn').style.display = 'inline-block';
    document.getElementById('resume-btn').style.display = 'none';
    console.log('Automation resumed:', data.message);
});
```

### Real-time Ticker Updates
```javascript
// Update ticker status cards in real-time
socket.on('automation_progress', function(data) {
    if (data.data && data.data.ticker) {
        const ticker = data.data.ticker;
        const card = document.querySelector(`[data-ticker="${ticker}"]`);
        
        if (card) {
            // Update card styling based on status
            if (data.data.success === true) {
                card.classList.remove('processing');
                card.classList.add('success');
                card.querySelector('.status-icon').innerHTML = '✓';
            } else if (data.data.success === false) {
                card.classList.remove('processing');
                card.classList.add('error');
                card.querySelector('.status-icon').innerHTML = '✗';
            } else {
                card.classList.add('processing');
                card.querySelector('.status-icon').innerHTML = '⏳';
            }
            
            // Update status text
            card.querySelector('.status-text').textContent = data.message;
        }
    }
});
```

## Error Handling Patterns

### Server-Side Error Emission
```python
def emit_error(user_id, error_message, error_type='general', recoverable=True):
    """Emit error event with recovery options"""
    try:
        socketio.emit('automation_error', {
            'error_type': error_type,
            'message': error_message,
            'recoverable': recoverable,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, room=f"user_{user_id}")
        
    except Exception as e:
        app.logger.error(f"Failed to emit error: {e}", exc_info=True)
```

### Client-Side Error Handling
```javascript
socket.on('automation_error', function(data) {
    const { error_type, message, recoverable } = data;
    
    // Show error notification
    showNotification(message, 'error');
    
    // If recoverable, show retry option
    if (recoverable) {
        showRetryButton();
    }
    
    // Log error
    console.error('Automation error:', data);
});
```

## Multi-User Support

### Room Management
```python
# Each user gets their own room
join_room(f"user_{user_id}")

# Emit only to that user
socketio.emit('progress', data, room=f"user_{user_id}")

# Never use broadcast=True for user-specific events
socketio.emit('progress', data, broadcast=True)  # ❌ WRONG - sends to ALL users
```

### Session Management
```python
@socketio.on('connect')
def handle_connect():
    """Ensure user is authenticated before joining room"""
    if 'user_id' not in session:
        app.logger.warning(f"Unauthenticated connection: {request.sid}")
        emit('error', {'message': 'Authentication required'})
        return False  # Reject connection
    
    user_id = session['user_id']
    join_room(f"user_{user_id}")
    app.logger.info(f"User {user_id} connected: {request.sid}")
```

## Performance Optimization

### Throttle Progress Updates
```python
import time

class ProgressThrottler:
    """Throttle progress emissions to avoid overwhelming client"""
    def __init__(self, min_interval=0.5):
        self.min_interval = min_interval
        self.last_emit_time = 0
    
    def should_emit(self):
        current_time = time.time()
        if current_time - self.last_emit_time >= self.min_interval:
            self.last_emit_time = current_time
            return True
        return False

throttler = ProgressThrottler(min_interval=0.5)  # Max 2 updates/second

def emit_throttled_progress(user_id, stage, message, percent=None):
    """Emit progress only if throttle allows"""
    if throttler.should_emit() or stage in ['complete', 'error']:
        emit_progress(user_id, stage, message, percent)
```

### Batch Updates
```python
# Instead of emitting every ticker immediately
for ticker in tickers:
    process_ticker(ticker)
    emit_progress(user_id, 'processing', f'Processed {ticker}')  # ❌ Too many events

# Batch updates every N tickers
batch_size = 5
for idx, ticker in enumerate(tickers):
    process_ticker(ticker)
    if (idx + 1) % batch_size == 0 or idx == len(tickers) - 1:
        percent = int((idx + 1) / len(tickers) * 100)
        emit_progress(user_id, 'processing', 
                     f'Processed {idx + 1}/{len(tickers)} tickers', 
                     percent=percent)  # ✅ Batched
```

## Testing SocketIO

### Mock SocketIO in Tests
```python
from unittest.mock import Mock, patch

def test_automation_emits_progress():
    """Test that automation emits progress events"""
    with patch('main_portal_app.socketio') as mock_socketio:
        run_stock_automation('user123', ['AAPL'], 'profile1')
        
        # Verify progress was emitted
        assert mock_socketio.emit.called
        
        # Check specific calls
        calls = mock_socketio.emit.call_args_list
        assert any('automation_progress' in str(call) for call in calls)
```

## Deployment Checklist

Before deploying SocketIO features:
- [ ] `async_mode='threading'` configured (required for Azure App Service)
- [ ] CORS configured for production domain
- [ ] Ping timeout/interval configured appropriately
- [ ] All events emit to user-specific rooms (not broadcast)
- [ ] Error handling for disconnections
- [ ] Progress throttling implemented
- [ ] Client reconnection logic tested
- [ ] Multi-user testing completed
- [ ] SocketIO events logged for debugging
- [ ] Azure App Service WebSocket support enabled
