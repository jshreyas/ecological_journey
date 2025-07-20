#!/bin/bash

# Linting script for Ecological Journey
# Run all linting tools and provide a summary

set -e

echo "🔍 Running comprehensive code quality checks..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a tool and report status
run_tool() {
    local tool_name="$1"
    local command="$2"

    echo -e "\n${YELLOW}Running $tool_name...${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✅ $tool_name passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $tool_name failed${NC}"
        return 1
    fi
}

# Track overall success
overall_success=true

# 1. Black formatting check
run_tool "Black (formatting)" "black --check --diff ui/ api/ tests/" || overall_success=false

# 2. isort import sorting check
run_tool "isort (import sorting)" "isort --check-only --diff ui/ api/ tests/" || overall_success=false

# 3. Flake8 linting
run_tool "Flake8 (linting)" "flake8 ui/ api/ tests/" || overall_success=false

# 4. MyPy type checking
run_tool "MyPy (type checking)" "mypy ui/ api/" || overall_success=false

# 5. Bandit security scanning
run_tool "Bandit (security)" "bandit -r ui/ api/ -f json -o bandit-report.json" || overall_success=false

# 6. Pydocstyle docstring checking
run_tool "Pydocstyle (docstrings)" "pydocstyle ui/ api/" || overall_success=false

# 7. Pre-commit hooks (if available)
if command -v pre-commit &> /dev/null; then
    run_tool "Pre-commit hooks" "pre-commit run --all-files" || overall_success=false
else
    echo -e "\n${YELLOW}⚠️  Pre-commit not installed, skipping...${NC}"
fi

echo -e "\n================================================"
if $overall_success; then
    echo -e "${GREEN}🎉 All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
