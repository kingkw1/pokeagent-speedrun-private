#!/bin/bash
# Quick test runner wrapper for scenario tests
# Usage: ./run_scenario_tests.sh [filter]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Pokemon Agent Scenario Test Runner${NC}"
echo "======================================"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    if [[ -f ".venv/bin/activate" ]]; then
        echo "Activating .venv..."
        source .venv/bin/activate
    else
        echo -e "${RED}❌ Could not find .venv/bin/activate${NC}"
        echo "Please activate your virtual environment first:"
        echo "  source .venv/bin/activate"
        exit 1
    fi
fi

# Kill any existing run.py processes to avoid port conflicts
if pgrep -f "python.*run.py" > /dev/null; then
    echo -e "${YELLOW}⚠️  Killing existing run.py processes...${NC}"
    pkill -f "python.*run.py" || true
    sleep 2
fi

# Run the tests
if [[ $# -eq 0 ]]; then
    echo "Running all tests..."
    python tests/scenarios/run_scenarios.py
else
    echo "Running tests matching: $1"
    python tests/scenarios/run_scenarios.py "$1"
fi

exit_code=$?

# Cleanup any lingering processes
if pgrep -f "python.*run.py" > /dev/null; then
    echo -e "${YELLOW}🧹 Cleaning up test processes...${NC}"
    pkill -f "python.*run.py" || true
fi

if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}✅ Tests completed successfully!${NC}"
else
    echo -e "${RED}❌ Tests failed${NC}"
fi

exit $exit_code
