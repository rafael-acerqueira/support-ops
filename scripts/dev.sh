#!/bin/bash

# Start all development services

set -e

echo "🚀 Starting SupportOps"
echo "===================================="
echo ""

# Check if docker services are running
echo "🐳 Checking Docker services..."
if ! docker ps | grep -q supportops-postgres; then
    echo "Starting Docker services..."
    docker compose up -d
    sleep 5
fi
echo "✅ Docker services running"

echo ""
echo "📊 Services will start in this terminal:"
echo ""
echo "Frontend:  http://localhost:3000"
echo "API:       http://localhost:8000"
echo "API Docs:  http://localhost:8000/docs"
echo "Workers:   Celery connected to Redis"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start all in parallel
npm run dev
