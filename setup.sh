#!/bin/bash
# Setup script for Slack Listener application (uv-based)

set -e

echo "=== Slack Listener Setup ==="
echo ""

# Check uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "❌ uv is not installed."
    echo "   Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "   or: brew install uv"
    exit 1
fi
echo "Found uv: $(uv --version)"

# Create / update virtual environment and sync dependencies from uv.lock
echo ""
echo "Syncing dependencies (this creates .venv/ if needed)..."
uv sync --frozen
echo "✓ Dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠️  Please edit .env and add your Slack tokens"
else
    echo ""
    echo ".env file already exists"
fi

# Create config file if it doesn't exist
if [ ! -f "config/config.yaml" ]; then
    echo ""
    echo "Creating config.yaml from template..."
    cp config/config.example.yaml config/config.yaml
    echo "✓ config.yaml created"
    echo "⚠️  Please edit config/config.yaml and configure your channels"
else
    echo ""
    echo "config.yaml already exists"
fi

# Make run script executable
chmod +x run.py

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your SLACK_BOT_TOKEN and SLACK_APP_TOKEN"
echo "2. Edit config/config.yaml to set up your channels and commands"
echo "3. Run the application:"
echo "   uv run python run.py"
echo ""
