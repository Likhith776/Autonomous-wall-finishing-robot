// Configuration
const API_URL = 'http://localhost:8000';

// State management
const state = {
    wallId: null,
    trajectoryId: null,
    pathData: [],
    currentStep: 0,
    isPlaying: false,
    animationId: null,
    obstacles: [],
    ws: null,
    isConnected: false
};

// Canvas elements
const canvas = document.getElementById('pathCanvas');
const ctx = canvas.getContext('2d');

// DOM elements
const elements = {
    wallWidth: document.getElementById('wallWidth'),
    wallHeight: document.getElementById('wallHeight'),
    toolWidth: document.getElementById('toolWidth'),
    overlap: document.getElementById('overlap'),
    backgroundMode: document.getElementById('backgroundMode'),
    obstaclesList: document.getElementById('obstaclesList'),
    addObstacle: document.getElementById('addObstacle'),
    generatePath: document.getElementById('generatePath'),
    clearAll: document.getElementById('clearAll'),
    playPause: document.getElementById('playPause'),
    reset: document.getElementById('reset'),
    speedControl: document.getElementById('speedControl'),
    totalDistance: document.getElementById('totalDistance'),
    computationTime: document.getElementById('computationTime'),
    pathEfficiency: document.getElementById('pathEfficiency'),
    coverage: document.getElementById('coverage'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    progressText: document.getElementById('progressText'),
    connectionStatus: document.getElementById('connectionStatus')
};

// Initialize
init();

function init() {
    // Event listeners
    elements.addObstacle.addEventListener('click', addObstacle);
    elements.generatePath.addEventListener('click', generatePath);
    elements.clearAll.addEventListener('click', clearAll);
    elements.playPause.addEventListener('click', togglePlayPause);
    elements.reset.addEventListener('click', resetAnimation);
    
    // Draw initial empty canvas
    drawCanvas();
}

function addObstacle() {
    const obstacle = {
        id: Date.now(),
        x: 1,
        y: 1,
        width: 0.5,
        height: 0.5
    };
    
    state.obstacles.push(obstacle);
    renderObstacles();
    drawCanvas();
}

function renderObstacles() {
    elements.obstaclesList.innerHTML = '';
    
    state.obstacles.forEach((obstacle, index) => {
        const div = document.createElement('div');
        div.className = 'obstacle-item';
        div.innerHTML = `
            <input type="number" placeholder="X (m)" value="${obstacle.x}" 
                   step="0.1" min="0" onchange="updateObstacle(${index}, 'x', this.value)">
            <input type="number" placeholder="Y (m)" value="${obstacle.y}" 
                   step="0.1" min="0" onchange="updateObstacle(${index}, 'y', this.value)">
            <input type="number" placeholder="Width (m)" value="${obstacle.width}" 
                   step="0.1" min="0.1" onchange="updateObstacle(${index}, 'width', this.value)">
            <input type="number" placeholder="Height (m)" value="${obstacle.height}" 
                   step="0.1" min="0.1" onchange="updateObstacle(${index}, 'height', this.value)">
            <button onclick="removeObstacle(${index})">Remove</button>
        `;
        elements.obstaclesList.appendChild(div);
    });
}

window.updateObstacle = function(index, field, value) {
    state.obstacles[index][field] = parseFloat(value);
    drawCanvas();
};

window.removeObstacle = function(index) {
    state.obstacles.splice(index, 1);
    renderObstacles();
    drawCanvas();
};

function connectWebSocket(wallId) {
    if (state.ws) {
        state.ws.close();
    }
    
    state.ws = new WebSocket(`ws://localhost:8000/ws/trajectory/${wallId}`);
    
    state.ws.onopen = () => {
        console.log('WebSocket connected');
        state.isConnected = true;
        updateConnectionStatus(true);
        showNotification('Real-time connection established', 'success');
    };
    
    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        
        if (data.status === 'started') {
            elements.progressText.textContent = 'Starting trajectory generation...';
        } else if (data.status === 'planning') {
            elements.progressText.textContent = `Planning path... ${data.progress}%`;
        } else if (data.status === 'storing') {
            elements.progressText.textContent = `Storing trajectory... ${data.progress}%`;
        } else if (data.status === 'completed') {
            elements.loadingOverlay.style.display = 'none';
            
            // Update stats
            elements.totalDistance.textContent = `${data.total_distance.toFixed(2)} m`;
            elements.computationTime.textContent = `${data.computation_time.toFixed(3)} s`;
            elements.pathEfficiency.textContent = `${data.path_efficiency.toFixed(1)}%`;
            elements.coverage.textContent = `${data.coverage_percentage.toFixed(1)}%`;
            
            // Fetch complete trajectory
            fetchTrajectory(data.trajectory_id);
            
            showNotification('Path generated successfully!', 'success');
        } else if (data.status === 'error') {
            elements.loadingOverlay.style.display = 'none';
            showNotification(`Error: ${data.message}`, 'error');
        }
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus(false);
        showNotification('WebSocket connection error', 'error');
    };
    
    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        state.isConnected = false;
        updateConnectionStatus(false);
    };
}

function updateConnectionStatus(connected) {
    const statusElement = elements.connectionStatus;
    const statusText = statusElement.querySelector('.status-text');
    
    if (connected) {
        statusElement.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusElement.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

async function fetchTrajectory(trajectoryId) {
    try {
        const response = await fetch(`${API_URL}/trajectories/${trajectoryId}`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch trajectory');
        }
        
        const trajectory = await response.json();
        state.trajectoryId = trajectory.id;
        state.pathData = trajectory.path_data;
        state.currentStep = 0;
        
        // Enable controls
        elements.playPause.disabled = false;
        elements.reset.disabled = false;
        elements.speedControl.disabled = false;
        
        // Draw path
        drawCanvas();
    } catch (error) {
        console.error('Error fetching trajectory:', error);
        showNotification('Failed to load trajectory data', 'error');
    }
}

async function generatePath() {
    try {
        elements.generatePath.disabled = true;
        elements.generatePath.textContent = 'Generating...';
        
        const useBackground = elements.backgroundMode.checked;
        
        // Create wall
        const wallData = {
            width: parseFloat(elements.wallWidth.value),
            height: parseFloat(elements.wallHeight.value),
            obstacles: state.obstacles.map(obs => ({
                x: obs.x,
                y: obs.y,
                width: obs.width,
                height: obs.height
            }))
        };
        
        const wallResponse = await fetch(`${API_URL}/walls/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(wallData)
        });
        
        if (!wallResponse.ok) {
            const error = await wallResponse.json();
            throw new Error(error.detail || 'Failed to create wall');
        }
        
        const wall = await wallResponse.json();
        state.wallId = wall.id;
        
        // Generate trajectory
        const trajectoryData = {
            wall_id: wall.id,
            tool_width: parseFloat(elements.toolWidth.value),
            overlap: parseFloat(elements.overlap.value) / 100
        };
        
        const trajectoryUrl = useBackground 
            ? `${API_URL}/trajectories/?background=true`
            : `${API_URL}/trajectories/`;
        
        const trajectoryResponse = await fetch(trajectoryUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(trajectoryData)
        });
        
        if (!trajectoryResponse.ok) {
            const error = await trajectoryResponse.json();
            throw new Error(error.detail || 'Failed to generate trajectory');
        }
        
        const result = await trajectoryResponse.json();
        
        if (useBackground) {
            // Background mode - connect WebSocket
            elements.loadingOverlay.style.display = 'flex';
            elements.progressText.textContent = 'Connecting to real-time updates...';
            connectWebSocket(wall.id);
            showNotification('Trajectory generation started in background', 'success');
        } else {
            // Synchronous mode - process result directly
            const trajectory = result.trajectory;
            state.trajectoryId = trajectory.id;
            state.pathData = trajectory.path_data;
            state.currentStep = 0;
            
            // Update stats
            elements.totalDistance.textContent = `${trajectory.total_distance.toFixed(2)} m`;
            elements.computationTime.textContent = `${trajectory.computation_time.toFixed(3)} s`;
            elements.pathEfficiency.textContent = `${trajectory.path_efficiency.toFixed(1)}%`;
            elements.coverage.textContent = `${trajectory.coverage_percentage.toFixed(1)}%`;
            
            // Enable controls
            elements.playPause.disabled = false;
            elements.reset.disabled = false;
            elements.speedControl.disabled = false;
            
            // Draw path
            drawCanvas();
            
            showNotification('Path generated successfully!', 'success');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification(`Error: ${error.message}`, 'error');
        elements.loadingOverlay.style.display = 'none';
    } finally {
        elements.generatePath.disabled = false;
        elements.generatePath.textContent = 'Generate Path';
    }
}

function drawCanvas() {
    const wallWidth = parseFloat(elements.wallWidth.value);
    const wallHeight = parseFloat(elements.wallHeight.value);
    
    // Clear canvas with subtle background
    ctx.fillStyle = '#fafafa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Calculate scale
    const padding = 60;
    const scaleX = (canvas.width - 2 * padding) / wallWidth;
    const scaleY = (canvas.height - 2 * padding) / wallHeight;
    const scale = Math.min(scaleX, scaleY);
    
    // Center the drawing
    const offsetX = (canvas.width - wallWidth * scale) / 2;
    const offsetY = (canvas.height - wallHeight * scale) / 2;
    
    // Transform functions
    const toCanvasX = (x) => offsetX + x * scale;
    const toCanvasY = (y) => canvas.height - (offsetY + y * scale);
    
    // Draw subtle grid
    ctx.strokeStyle = '#f0f0f5';
    ctx.lineWidth = 1;
    const gridSize = 1;
    
    for (let x = 0; x <= wallWidth; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(toCanvasX(x), toCanvasY(0));
        ctx.lineTo(toCanvasX(x), toCanvasY(wallHeight));
        ctx.stroke();
    }
    
    for (let y = 0; y <= wallHeight; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(toCanvasX(0), toCanvasY(y));
        ctx.lineTo(toCanvasX(wallWidth), toCanvasY(y));
        ctx.stroke();
    }
    
    // Draw wall boundary with rounded corners
    ctx.strokeStyle = '#2c2c2e';
    ctx.lineWidth = 2;
    const borderRadius = 8;
    const x = offsetX;
    const y = offsetY;
    const w = wallWidth * scale;
    const h = wallHeight * scale;
    
    ctx.beginPath();
    ctx.moveTo(x + borderRadius, y);
    ctx.lineTo(x + w - borderRadius, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + borderRadius);
    ctx.lineTo(x + w, y + h - borderRadius);
    ctx.quadraticCurveTo(x + w, y + h, x + w - borderRadius, y + h);
    ctx.lineTo(x + borderRadius, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - borderRadius);
    ctx.lineTo(x, y + borderRadius);
    ctx.quadraticCurveTo(x, y, x + borderRadius, y);
    ctx.closePath();
    ctx.stroke();
    
    // Draw obstacles with soft shadows
    state.obstacles.forEach(obs => {
        const obsX = toCanvasX(obs.x);
        const obsY = toCanvasY(obs.y + obs.height);
        const obsW = obs.width * scale;
        const obsH = obs.height * scale;
        const obsRadius = 6;
        
        // Shadow
        ctx.shadowColor = 'rgba(0, 0, 0, 0.1)';
        ctx.shadowBlur = 12;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 2;
        
        // Fill
        ctx.fillStyle = '#6e6e73';
        ctx.beginPath();
        ctx.moveTo(obsX + obsRadius, obsY);
        ctx.lineTo(obsX + obsW - obsRadius, obsY);
        ctx.quadraticCurveTo(obsX + obsW, obsY, obsX + obsW, obsY + obsRadius);
        ctx.lineTo(obsX + obsW, obsY + obsH - obsRadius);
        ctx.quadraticCurveTo(obsX + obsW, obsY + obsH, obsX + obsW - obsRadius, obsY + obsH);
        ctx.lineTo(obsX + obsRadius, obsY + obsH);
        ctx.quadraticCurveTo(obsX, obsY + obsH, obsX, obsY + obsH - obsRadius);
        ctx.lineTo(obsX, obsY + obsRadius);
        ctx.quadraticCurveTo(obsX, obsY, obsX + obsRadius, obsY);
        ctx.closePath();
        ctx.fill();
        
        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    });
    
    // Draw path
    if (state.pathData.length > 0) {
        // Draw complete path (light gray)
        ctx.strokeStyle = '#d1d1d6';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        
        state.pathData.forEach((point, index) => {
            const px = toCanvasX(point[0]);
            const py = toCanvasY(point[1]);
            
            if (index === 0) {
                ctx.moveTo(px, py);
            } else {
                ctx.lineTo(px, py);
            }
        });
        
        ctx.stroke();
        
        // Draw animated portion (dark)
        if (state.currentStep > 0) {
            ctx.strokeStyle = '#2c2c2e';
            ctx.lineWidth = 3;
            ctx.beginPath();
            
            for (let i = 0; i <= Math.min(state.currentStep, state.pathData.length - 1); i++) {
                const point = state.pathData[i];
                const px = toCanvasX(point[0]);
                const py = toCanvasY(point[1]);
                
                if (i === 0) {
                    ctx.moveTo(px, py);
                } else {
                    ctx.lineTo(px, py);
                }
            }
            
            ctx.stroke();
            
            // Draw robot position with soft glow
            if (state.currentStep < state.pathData.length) {
                const currentPoint = state.pathData[state.currentStep];
                const px = toCanvasX(currentPoint[0]);
                const py = toCanvasY(currentPoint[1]);
                
                // Outer glow
                ctx.fillStyle = 'rgba(44, 44, 46, 0.15)';
                ctx.beginPath();
                ctx.arc(px, py, 12, 0, Math.PI * 2);
                ctx.fill();
                
                // Robot marker
                ctx.fillStyle = '#2c2c2e';
                ctx.beginPath();
                ctx.arc(px, py, 7, 0, Math.PI * 2);
                ctx.fill();
            }
        }
        
        // Draw start marker (with subtle shadow)
        const start = state.pathData[0];
        const startX = toCanvasX(start[0]);
        const startY = toCanvasY(start[1]);
        
        ctx.shadowColor = 'rgba(0, 0, 0, 0.15)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 2;
        
        ctx.fillStyle = '#6e6e73';
        ctx.beginPath();
        ctx.arc(startX, startY, 8, 0, Math.PI * 2);
        ctx.fill();
        
        // Draw end marker
        const end = state.pathData[state.pathData.length - 1];
        const endX = toCanvasX(end[0]);
        const endY = toCanvasY(end[1]);
        
        ctx.fillStyle = '#2c2c2e';
        ctx.beginPath();
        ctx.arc(endX, endY, 8, 0, Math.PI * 2);
        ctx.fill();
        
        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
    }
    
    // Draw subtle dimension labels
    ctx.fillStyle = '#86868b';
    ctx.font = '500 13px -apple-system, BlinkMacSystemFont, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${wallWidth}m`, offsetX + (wallWidth * scale) / 2, canvas.height - 20);
    
    ctx.save();
    ctx.translate(20, offsetY + (wallHeight * scale) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(`${wallHeight}m`, 0, 0);
    ctx.restore();
}

function togglePlayPause() {
    state.isPlaying = !state.isPlaying;
    
    const icon = elements.playPause.querySelector('.icon');
    
    if (state.isPlaying) {
        icon.textContent = '⏸';
        animate();
    } else {
        icon.textContent = '▶';
        if (state.animationId) {
            cancelAnimationFrame(state.animationId);
        }
    }
}

function animate() {
    if (!state.isPlaying) return;
    
    const speed = parseInt(elements.speedControl.value);
    const stepsPerFrame = Math.max(1, Math.floor(speed / 10));
    
    state.currentStep += stepsPerFrame;
    
    if (state.currentStep >= state.pathData.length) {
        state.currentStep = state.pathData.length - 1;
        state.isPlaying = false;
        elements.playPause.querySelector('.icon').textContent = '▶';
        drawCanvas();
        return;
    }
    
    drawCanvas();
    
    state.animationId = requestAnimationFrame(() => {
        setTimeout(animate, 16);
    });
}

function resetAnimation() {
    state.currentStep = 0;
    state.isPlaying = false;
    elements.playPause.querySelector('.icon').textContent = '▶';
    
    if (state.animationId) {
        cancelAnimationFrame(state.animationId);
    }
    
    drawCanvas();
}

function clearAll() {
    state.obstacles = [];
    state.pathData = [];
    state.currentStep = 0;
    state.isPlaying = false;
    
    if (state.ws) {
        state.ws.close();
        state.ws = null;
    }
    
    renderObstacles();
    drawCanvas();
    
    elements.playPause.disabled = true;
    elements.reset.disabled = true;
    elements.speedControl.disabled = true;
    elements.loadingOverlay.style.display = 'none';
    
    elements.totalDistance.textContent = '—';
    elements.computationTime.textContent = '—';
    elements.pathEfficiency.textContent = '—';
    elements.coverage.textContent = '—';
    
    updateConnectionStatus(false);
    showNotification('Cleared successfully', 'success');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 250ms cubic-bezier(0.4, 0, 0.2, 1)';
        setTimeout(() => notification.remove(), 250);
    }, 3000);
}