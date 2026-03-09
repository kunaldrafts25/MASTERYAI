#!/bin/bash
# ============================================
# MasteryAI EC2 Setup Script
# Run this on a fresh Ubuntu 22.04/24.04 EC2 instance
# Usage: curl -s <raw-url> | bash   OR   bash ec2-setup.sh
# ============================================
set -e

echo "========================================"
echo " MasteryAI — EC2 Server Setup"
echo "========================================"

# Update system
echo "[1/5] Updating system packages..."
sudo apt-get update -y && sudo apt-get upgrade -y

# Install Docker
echo "[2/5] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to re-login for group changes."
else
    echo "Docker already installed."
fi

# Install Docker Compose plugin
echo "[3/5] Installing Docker Compose..."
if ! docker compose version &> /dev/null; then
    sudo apt-get install -y docker-compose-plugin
else
    echo "Docker Compose already installed."
fi

# Install useful tools
echo "[4/5] Installing utilities..."
sudo apt-get install -y git htop curl jq

# Clone repo (if not already cloned)
echo "[5/5] Setting up project..."
APP_DIR="$HOME/masteryai"
if [ ! -d "$APP_DIR" ]; then
    echo "Enter your GitHub repo URL (e.g., https://github.com/youruser/masteryai.git):"
    read -r REPO_URL
    git clone "$REPO_URL" "$APP_DIR"
else
    echo "Project directory exists. Pulling latest..."
    cd "$APP_DIR" && git pull
fi

cd "$APP_DIR"

# Create .env from template if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "========================================="
    echo " IMPORTANT: Edit .env before deploying!"
    echo "========================================="
    echo ""
    echo "Run:  nano $APP_DIR/.env"
    echo ""
    echo "Fill in these required values:"
    echo "  - AWS_ACCESS_KEY_ID"
    echo "  - AWS_SECRET_ACCESS_KEY"
    echo "  - JWT_SECRET (run: openssl rand -hex 32)"
    echo "  - POSTGRES_PASSWORD (run: openssl rand -hex 16)"
    echo "  - DOMAIN (your domain, e.g., api.masteryai.com)"
    echo "  - FRONTEND_URL (your Vercel URL)"
    echo ""
else
    echo ".env file already exists."
fi

echo ""
echo "========================================"
echo " Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env:           nano $APP_DIR/.env"
echo "  2. Deploy:              cd $APP_DIR && bash scripts/deploy-prod.sh"
echo "  3. Check logs:          docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Generate secrets with:"
echo "  JWT_SECRET:       openssl rand -hex 32"
echo "  POSTGRES_PASSWORD: openssl rand -hex 16"
echo ""
