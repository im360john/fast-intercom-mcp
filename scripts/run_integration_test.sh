#!/bin/bash

# Local Integration Test Script - Real API Testing with 30+ Days
# This script runs comprehensive end-to-end tests with real Intercom API data

set -e  # Exit on any error

echo "🚀 FastIntercom Local Integration Test - Real API Testing"
echo "========================================================"

# Check required environment variables
if [ -z "$INTERCOM_ACCESS_TOKEN" ]; then
    echo "❌ ERROR: INTERCOM_ACCESS_TOKEN environment variable is required"
    echo "Please set your Intercom access token:"
    echo "export INTERCOM_ACCESS_TOKEN=your_production_token_here"
    exit 1
fi

# Set logging level for verbose output
export FASTINTERCOM_LOG_LEVEL=DEBUG

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📁 Project Root: $PROJECT_ROOT"
echo "🔑 Using Intercom Access Token: ${INTERCOM_ACCESS_TOKEN:0:10}..."
echo "📊 Log Level: $FASTINTERCOM_LOG_LEVEL"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check if we're in a virtual environment or can import the module
echo "🔍 Checking Python environment..."
if ! python3 -c "import fast_intercom_mcp" 2>/dev/null; then
    echo "📦 Installing package in development mode..."
    pip install -e . || {
        echo "❌ Failed to install package. Please check your Python environment."
        exit 1
    }
fi

# Run the comprehensive integration test
echo "🧪 Running comprehensive integration test..."
echo "⏱️  This may take several minutes (syncing 30+ days of data)..."
echo ""

# Run the test with verbose output
python3 -m pytest tests/integration/test_e2e_comprehensive.py -v -s --tb=short

echo ""
echo "✅ Integration test completed successfully!"
echo "🎉 FastIntercom is ready for production use!"