#!/bin/bash
# ============================================
# MasteryAI Production Deployment
# Usage: bash scripts/deploy-prod.sh
# ============================================
set -e

cd "$(dirname "$0")/.."

echo "=== MasteryAI Production Deployment ==="

# Validate .env
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Run: cp .env.example .env"
    exit 1
fi

# Check required vars
source .env
MISSING=""
[ -z "$AWS_ACCESS_KEY_ID" ] && MISSING="$MISSING AWS_ACCESS_KEY_ID"
[ -z "$AWS_SECRET_ACCESS_KEY" ] && MISSING="$MISSING AWS_SECRET_ACCESS_KEY"
[ "$JWT_SECRET" = "generate-a-64-char-random-string-here" ] && MISSING="$MISSING JWT_SECRET"
[ "$POSTGRES_PASSWORD" = "generate-a-strong-password-here" ] && MISSING="$MISSING POSTGRES_PASSWORD"

if [ -n "$MISSING" ]; then
    echo "ERROR: These .env variables need real values:$MISSING"
    echo "Edit .env first: nano .env"
    exit 1
fi

echo "[1/4] Pulling latest code..."
git pull 2>/dev/null || echo "Not a git repo or no remote — skipping pull."

echo "[2/4] Building containers..."
docker compose -f docker-compose.prod.yml build

echo "[3/4] Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo "[4/4] Waiting for services..."
sleep 15

# Health check
echo ""
echo "Checking health..."
HEALTH=$(curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "FAILED")

if echo "$HEALTH" | jq . 2>/dev/null; then
    # Get public IP
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com 2>/dev/null || echo "<your-ec2-ip>")
    echo ""
    echo "=== Deployment successful! ==="
    echo ""
    echo "Backend API:  http://$PUBLIC_IP/api/v1/health"
    echo "Frontend:     ${FRONTEND_URL:-not set}"
    echo ""
    echo "Set this in Vercel env vars:"
    echo "  NEXT_PUBLIC_API_URL = http://$PUBLIC_IP/api/v1"
    echo ""
    echo "Useful commands:"
    echo "  Logs:     docker compose -f docker-compose.prod.yml logs -f"
    echo "  Stop:     docker compose -f docker-compose.prod.yml down"
    echo "  Restart:  docker compose -f docker-compose.prod.yml restart"
    echo "  Update:   git pull && bash scripts/deploy-prod.sh"
else
    echo ""
    echo "WARNING: Health check failed. Check logs:"
    echo "  docker compose -f docker-compose.prod.yml logs backend"
fi
