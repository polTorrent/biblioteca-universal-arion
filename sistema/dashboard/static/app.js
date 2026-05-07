// Arion Dashboard - WebSocket Client

let socket;
let connected = false;

// Connect to WebSocket server
function connectWebSocket() {
    socket = io('http://localhost:9120', {
        transports: ['websocket', 'polling']
    });

    socket.on('connect', () => {
        console.log('Connected to WebSocket server');
        connected = true;
        updateConnectionStatus(true);
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket server');
        connected = false;
        updateConnectionStatus(false);
    });

    socket.on('connected', (data) => {
        console.log('Server message:', data.message);
    });

    // Handle different event types
    socket.on('hermes_event', (event) => {
        addEvent('hermes', event);
    });

    socket.on('llm_event', (event) => {
        addEvent('llm', event);
    });

    socket.on('worker_event', (event) => {
        addEvent('worker', event);
    });

    socket.on('tools_event', (event) => {
        addEvent('tools', event);
    });

    socket.on('errors_event', (event) => {
        addEvent('errors', event);
    });
}

// Update connection status indicator
function updateConnectionStatus(isConnected) {
    const statusEl = document.getElementById('connection-status');
    if (isConnected) {
        statusEl.classList.remove('disconnected');
        statusEl.classList.add('connected');
        statusEl.innerHTML = '<i class="fas fa-circle"></i> <span>Connectat</span>';
    } else {
        statusEl.classList.remove('connected');
        statusEl.classList.add('disconnected');
        statusEl.innerHTML = '<i class="fas fa-circle"></i> <span>Desconnectat</span>';
    }
}

// Add event to panel
function addEvent(panelType, event) {
    const streamEl = document.getElementById(`${panelType}-stream`);
    const emptyState = streamEl.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const eventCard = document.createElement('div');
    eventCard.className = 'event-card';

    // Format content
    let contentClass = '';
    if (event.data.content.includes('ERROR') || event.data.content.includes('Error')) {
        contentClass = 'error';
    } else if (panelType === 'llm' && event.data.content.includes('<thinking>')) {
        contentClass = 'thinking';
    } else if (panelType === 'tools') {
        contentClass = 'tool-call';
    }

    eventCard.innerHTML = `
        <div class="event-timestamp">${formatTimestamp(event.timestamp)}</div>
        <div class="event-content ${contentClass}">${escapeHtml(event.data.content)}</div>
    `;

    streamEl.appendChild(eventCard);

    // Auto-scroll to bottom
    streamEl.scrollTop = streamEl.scrollHeight;

    // Limit to 100 events
    while (streamEl.children.length > 100) {
        streamEl.removeChild(streamEl.firstChild);
    }
}

// Format timestamp
function formatTimestamp(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('ca-ES', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clear panel
function clearPanel(panelType) {
    const streamEl = document.getElementById(`${panelType}-stream`);
    streamEl.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-hourglass-start"></i>
            <p>Esperant activitat...</p>
        </div>
    `;
}

// Update clock
function updateClock() {
    const clockEl = document.getElementById('clock');
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('ca-ES', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Fetch system status
async function fetchStatus() {
    try {
        const response = await fetch('http://localhost:9120/api/status');
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }
        const data = await response.json();

        // Update worker status
        const workerEl = document.getElementById('worker-status');
        if (data.worker.running) {
            workerEl.textContent = `Actiu (PID: ${data.worker.pid})`;
            workerEl.style.color = '#00d26a';
        } else {
            workerEl.textContent = 'Aturat';
            workerEl.style.color = '#ff4757';
        }

        // Update DIEM balance
        document.getElementById('diem-balance').textContent = data.venice.diem.toFixed(2);

        // Update queue count
        document.getElementById('queue-count').textContent = data.queue.count;

        // Update requests remaining
        document.getElementById('requests-remaining').textContent = data.venice.requests;

        // Update tokens remaining
        document.getElementById('tokens-remaining').textContent = formatNumber(data.venice.tokens);

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Format large numbers
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket
    connectWebSocket();

    // Update clock every second
    setInterval(updateClock, 1000);
    updateClock();

    // Fetch status every 5 seconds
    setInterval(fetchStatus, 5000);
    fetchStatus();
});