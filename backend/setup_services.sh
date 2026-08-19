#!/bin/bash

echo "🚀 Setting up Wall Robot Coverage System services..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

echo "========================================"
echo "  1. Checking System Requirements"
echo "========================================"
echo ""

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    echo -e "${GREEN}✓${NC} Python 3 installed: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check pip
if command_exists pip3; then
    echo -e "${GREEN}✓${NC} pip3 installed"
else
    echo -e "${RED}✗${NC} pip3 not found. Please install pip3."
    exit 1
fi

echo ""
echo "========================================"
echo "  2. Installing/Checking Redis"
echo "========================================"
echo ""

# Check if Redis is installed
if ! command_exists redis-server; then
    echo -e "${YELLOW}⚠${NC}  Redis not found. Installing..."
    
    # Detect OS and install Redis
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            echo "Installing Redis via Homebrew..."
            brew install redis
        else
            echo -e "${RED}✗${NC} Homebrew not found. Please install Homebrew first:"
            echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command_exists apt-get; then
            echo "Installing Redis via apt-get..."
            sudo apt-get update
            sudo apt-get install -y redis-server
        elif command_exists yum; then
            echo "Installing Redis via yum..."
            sudo yum install -y redis
        else
            echo -e "${RED}✗${NC} Unable to install Redis automatically. Please install manually."
            exit 1
        fi
    else
        echo -e "${RED}✗${NC} Unsupported OS: $OSTYPE"
        echo "Please install Redis manually: https://redis.io/download"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Redis already installed"
fi

echo ""
echo "========================================"
echo "  3. Starting Redis Server"
echo "========================================"
echo ""

# Check if Redis is already running
if port_in_use 6379; then
    echo -e "${YELLOW}⚠${NC}  Redis is already running on port 6379"
else
    echo "Starting Redis server..."
    redis-server --daemonize yes --port 6379
    sleep 2
fi

# Verify Redis is running
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running on port 6379"
    echo "  Test connection: redis-cli ping"
else
    echo -e "${RED}✗${NC} Failed to start Redis"
    echo "  Try manually: redis-server"
    exit 1
fi

echo ""
echo "========================================"
echo "  4. Installing Python Dependencies"
echo "========================================"
echo ""

# Check if we're in the backend directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}⚠${NC}  requirements.txt not found in current directory"
    if [ -f "backend/requirements.txt" ]; then
        cd backend
        echo "Changed to backend directory"
    else
        echo -e "${RED}✗${NC} requirements.txt not found. Make sure you're in the project root."
        exit 1
    fi
fi

echo "Installing Python packages..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Python dependencies installed"
else
    echo -e "${RED}✗${NC} Failed to install dependencies"
    exit 1
fi

echo ""
echo "========================================"
echo "  5. Starting Celery Worker"
echo "========================================"
echo ""

# Check if Celery worker is already running
if pgrep -f "celery.*worker" > /dev/null; then
    echo -e "${YELLOW}⚠${NC}  Celery worker is already running"
    echo "  To restart, stop existing workers first:"
    echo "  pkill -f 'celery.*worker'"
else
    echo "Starting Celery worker..."
    celery -A app.celery_app worker --loglevel=info --concurrency=2 > celery_worker.log 2>&1 &
    CELERY_PID=$!
    
    sleep 3
    
    if ps -p $CELERY_PID > /dev/null; then
        echo -e "${GREEN}✓${NC} Celery worker started (PID: $CELERY_PID)"
        echo "  Logs: tail -f celery_worker.log"
    else
        echo -e "${RED}✗${NC} Failed to start Celery worker"
        echo "  Check logs: cat celery_worker.log"
    fi
fi

echo ""
echo "========================================"
echo "  6. Starting Flower (Celery Monitor)"
echo "========================================"
echo ""

# Check if Flower is already running
if port_in_use 5555; then
    echo -e "${YELLOW}⚠${NC}  Flower is already running on port 5555"
else
    echo "Starting Flower monitoring dashboard..."
    celery -A app.celery_app flower --port=5555 > flower.log 2>&1 &
    FLOWER_PID=$!
    
    sleep 3
    
    if ps -p $FLOWER_PID > /dev/null; then
        echo -e "${GREEN}✓${NC} Flower started (PID: $FLOWER_PID)"
        echo "  Dashboard: http://localhost:5555"
    else
        echo -e "${RED}✗${NC} Failed to start Flower"
        echo "  Check logs: cat flower.log"
    fi
fi

echo ""
echo "========================================"
echo "  7. Service Status Summary"
echo "========================================"
echo ""

echo -e "${BLUE}📊 Active Services:${NC}"
echo ""

# Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Redis Server"
    echo "     URL: redis://localhost:6379"
    echo "     Status: $(redis-cli ping)"
else
    echo -e "  ${RED}✗${NC} Redis Server - NOT RUNNING"
fi

echo ""

# Celery Worker
if pgrep -f "celery.*worker" > /dev/null; then
    WORKER_COUNT=$(pgrep -f "celery.*worker" | wc -l)
    echo -e "  ${GREEN}✓${NC} Celery Worker(s): $WORKER_COUNT instance(s)"
    echo "     Logs: tail -f celery_worker.log"
else
    echo -e "  ${RED}✗${NC} Celery Worker - NOT RUNNING"
fi

echo ""

# Flower
if port_in_use 5555; then
    echo -e "  ${GREEN}✓${NC} Flower Dashboard"
    echo "     URL: http://localhost:5555"
else
    echo -e "  ${RED}✗${NC} Flower Dashboard - NOT RUNNING"
fi

echo ""
echo "========================================"
echo "  8. Next Steps"
echo "========================================"
echo ""

echo -e "${BLUE}To start the FastAPI server:${NC}"
echo "  cd backend"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""

echo -e "${BLUE}To start the frontend:${NC}"
echo "  cd frontend"
echo "  python3 -m http.server 8080"
echo ""

echo -e "${BLUE}Access the application:${NC}"
echo "  • Frontend:  http://localhost:8080"
echo "  • API Docs:  http://localhost:8000/docs"
echo "  • Metrics:   http://localhost:8000/metrics"
echo "  • Flower:    http://localhost:5555"
echo ""

echo "========================================"
echo "  Stop Services Commands"
echo "========================================"
echo ""

echo "To stop all services, run:"
echo ""
echo -e "${YELLOW}# Stop Redis${NC}"
echo "  redis-cli shutdown"
echo ""
echo -e "${YELLOW}# Stop Celery Worker${NC}"
echo "  pkill -f 'celery.*worker'"
echo ""
echo -e "${YELLOW}# Stop Flower${NC}"
echo "  pkill -f 'celery.*flower'"
echo ""
echo -e "${YELLOW}# Stop FastAPI (if running)${NC}"
echo "  pkill -f 'uvicorn'"
echo ""

echo "========================================"
echo "  Quick Stop Script"
echo "========================================"
echo ""
echo "Create a stop_services.sh file with:"
echo ""
echo '#!/bin/bash'
echo 'echo "Stopping all services..."'
echo 'redis-cli shutdown 2>/dev/null'
echo 'pkill -f "celery.*worker" 2>/dev/null'
echo 'pkill -f "celery.*flower" 2>/dev/null'
echo 'pkill -f "uvicorn" 2>/dev/null'
echo 'echo "All services stopped."'
echo ""

echo -e "${GREEN}✨ Setup complete!${NC}"
echo ""