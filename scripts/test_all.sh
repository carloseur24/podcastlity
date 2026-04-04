#!/bin/bash

# Test and format automation script for Content-OS
# Usage: ./scripts/test_all.sh [options]
# Options: format, test, test:quick, test:all

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate venv helper
activate_venv() {
    if [ -d "$PROJECT_ROOT/.venv" ]; then
        source "$PROJECT_ROOT/.venv/bin/activate"
    else
        echo -e "${RED}Virtual environment not found${NC}"
        exit 1
    fi
}

# Format Python
format_py() {
    echo -e "${YELLOW}Formatting Python code...${NC}"
    activate_venv
    ruff format .
    echo -e "${GREEN}Python formatting complete${NC}"
}

# Format Remotion
format_remotion() {
    echo -e "${YELLOW}Formatting Remotion code...${NC}"
    cd "$PROJECT_ROOT/remotion"
    pnpm exec prettier --write "src/**/*.{js,jsx,ts,tsx}"
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}Remotion formatting complete${NC}"
}

# Format all
format_all() {
    format_py
    format_remotion
}

# Test Python
test_py() {
    echo -e "${YELLOW}Running Python tests...${NC}"
    activate_venv
    python -m pytest tests/ --ignore=tests/test_audio_processing.py --ignore=tests/test_e2e.py -v "$@"
}

# Test Python quick
test_py_quick() {
    echo -e "${YELLOW}Running Python tests (quick)...${NC}"
    activate_venv
    python -m pytest tests/ --ignore=tests/test_audio_processing.py --ignore=tests/test_e2e.py -q "$@"
}

# Test Remotion
test_remotion() {
    echo -e "${YELLOW}Running Remotion tests (format check)...${NC}"
    cd "$PROJECT_ROOT/remotion"
    pnpm exec prettier --check "src/**/*.{js,jsx,ts,tsx}"
    cd "$PROJECT_ROOT"
    echo -e "${GREEN}Remotion tests complete${NC}"
}

# Test all
test_all() {
    echo -e "${YELLOW}Running all tests...${NC}"
    
    # Python tests
    activate_venv
    python -m pytest tests/ --ignore=tests/test_audio_processing.py --ignore=tests/test_e2e.py -q
    
    PYTHON_RESULT=$?
    
    # Remotion tests
    cd "$PROJECT_ROOT/remotion"
    pnpm exec prettier --check "src/**/*.{js,jsx,ts,tsx}" 2>/dev/null
    REMOTION_RESULT=$?
    cd "$PROJECT_ROOT"
    
    if [ $PYTHON_RESULT -eq 0 ] && [ $REMOTION_RESULT -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed${NC}"
        return 1
    fi
}

# Main
case "${1:-test:all}" in
    format)
        format_py
        ;;
    format:all)
        format_all
        ;;
    format:remotion)
        format_remotion
        ;;
    test)
        test_py "${@:2}"
        ;;
    test:quick)
        test_py_quick "${@:2}"
        ;;
    test:remotion)
        test_remotion
        ;;
    test:all)
        test_all
        ;;
    *)
        echo "Usage: $0 {format|format:all|format:remotion|test|test:quick|test:remotion|test:all}"
        exit 1
        ;;
esac
