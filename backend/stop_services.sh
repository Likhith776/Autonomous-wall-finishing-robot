#!/bin/bash

echo "🛑 Stopping Wall Robot Coverage System services..."
echo ""

# Stop Redis
echo "Stopping Redis..."
redis-cli shutdown 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Redis stopped"
else
    echo "⚠ Redis was not running or failed to stop"
fi

# Stop Celery Worker
echo "Stopping Celery workers..."
pkill -f "celery.*worker" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Celery workers stopped"
else
    echo "⚠ Celery workers were not running"
fi

# Stop Flower
echo "Stopping Flower..."
pkill -f "celery.*flower" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Flower stopped"
else
    echo "⚠ Flower was not running"
fi

# Stop FastAPI
echo "Stopping FastAPI..."
pkill -f "uvicorn" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ FastAPI stopped"
else
    echo "⚠ FastAPI was not running"
fi

echo ""
echo "✨ All services stopped!"