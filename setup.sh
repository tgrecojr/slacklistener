#!/bin/bash
# Setup script for Slack Listener application

set -e

echo "=== Slack Listener Setup ==="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo ""
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
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
echo "2. Configure AWS credentials (via ~/.aws/credentials or env vars)"
echo "3. Edit config/config.yaml to set up your channels and commands"
echo "4. Run the application:"
echo "   source venv/bin/activate"
echo "   python run.py"
echo ""
