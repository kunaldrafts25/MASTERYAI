#!/bin/bash
set -e

echo "=== MasteryAI Deployment ==="

if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example to .env and fill in values."
    exit 1
fi

echo "Building containers..."
docker compose build

echo "Starting services..."
docker compose up -d

echo "Waiting for services to be healthy..."
sleep 10

echo "Checking health..."
curl -s http://localhost/api/v1/health | python3 -m json.tool

echo ""
echo "=== Deployment complete ==="
echo "Frontend: http://localhost"
echo "API: http://localhost/api/v1/health"
echo "Docs: http://localhost/api/v1/docs"
