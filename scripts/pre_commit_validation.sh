#!/bin/bash
# pre_commit_validation.sh - Consistent pre-commit testing script
# Environment detection and validation for FastIntercom MCP project

set -e  # Exit on any error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Script metadata
SCRIPT_NAME="FastIntercom MCP Pre-commit Validation"
SCRIPT_VERSION="1.0.0"
START_TIME=$(date +%s)

# Configuration
VERBOSE=false
QUIET=false
SKIP_TESTS=false
SKIP_TYPE_CHECK=false
SKIP_LINT=false
SKIP_FORMAT=false
FIX_ISSUES=false
OUTPUT_FILE=""
CHECK_IMPORTS=true
CHECK_CLI=true
FAST_MODE=false

# Environment detection results
PROJECT_ENV=""
PYTHON_CMD=""
PIP_CMD=""
RUFF_CMD=""
MYPY_CMD=""
PYTEST_CMD=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${BLUE}ℹ️  $1${NC}"
    fi
}

log_success() {
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${GREEN}✅ $1${NC}"
    fi
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    if [[ "$QUIET" != "true" ]]; then
        echo ""
        echo -e "${BLUE}🔍 $1${NC}"
        echo "=================================================================================="
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}🔬 $1${NC}"
    fi
}

# Usage information
usage() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

Usage: $0 [OPTIONS]

DESCRIPTION:
    Comprehensive pre-commit validation with environment detection.
    Automatically detects Poetry, venv, or system Python environments
    and runs appropriate linting, type checking, and testing.

OPTIONS:
    --verbose              Enable verbose output with detailed logging
    --quiet               Suppress non-essential output
    --skip-tests          Skip running tests (faster validation)
    --skip-type-check     Skip mypy type checking
    --skip-lint           Skip ruff linting
    --skip-format         Skip ruff formatting check
    --fix                 Auto-fix linting and formatting issues
    --fast                Fast mode: skip tests and type checking
    --no-import-check     Skip Python module import test
    --no-cli-check        Skip CLI smoke test
    --output FILE         Save validation results to JSON file
    --help                Show this help message

EXAMPLES:
    # Full validation (recommended for pre-commit)
    $0

    # Fast validation (linting and imports only)
    $0 --fast

    # Auto-fix issues and run full validation
    $0 --fix

    # Quiet mode for CI environments
    $0 --quiet

    # Debug mode with verbose output
    $0 --verbose

ENVIRONMENT DETECTION:
    The script automatically detects and uses:
    - Poetry projects (pyproject.toml + poetry command)
    - Virtual environments (venv/ or .venv/ directories)
    - System Python (fallback)

EXIT CODES:
    0 - All validations passed
    1 - Environment setup failed
    2 - Import test failed
    3 - Linting failed
    4 - Type checking failed
    5 - Tests failed
    6 - CLI test failed
    7 - Multiple validation failures
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose)
            VERBOSE=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-type-check)
            SKIP_TYPE_CHECK=true
            shift
            ;;
        --skip-lint)
            SKIP_LINT=true
            shift
            ;;
        --skip-format)
            SKIP_FORMAT=true
            shift
            ;;
        --fix)
            FIX_ISSUES=true
            shift
            ;;
        --fast)
            FAST_MODE=true
            SKIP_TESTS=true
            SKIP_TYPE_CHECK=true
            shift
            ;;
        --no-import-check)
            CHECK_IMPORTS=false
            shift
            ;;
        --no-cli-check)
            CHECK_CLI=false
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Global validation tracking
VALIDATION_RESULTS=()
FAILED_VALIDATIONS=()
VALIDATION_WARNINGS=()

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ "$VERBOSE" == "true" ]]; then
        log_verbose "Cleanup completed with exit code: $exit_code"
    fi
    
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Environment detection function
detect_project_environment() {
    log_section "Detecting Project Environment"
    
    # Check current directory
    log_verbose "Current directory: $(pwd)"
    log_verbose "Checking for environment indicators..."
    
    # Detect Poetry project
    if [[ -f "pyproject.toml" ]] && command -v poetry >/dev/null 2>&1; then
        PROJECT_ENV="poetry"
        PYTHON_CMD="poetry run python"
        PIP_CMD="poetry add"
        RUFF_CMD="poetry run ruff"
        MYPY_CMD="poetry run mypy"
        PYTEST_CMD="poetry run pytest"
        log_success "Poetry environment detected"
        log_verbose "Using Poetry commands for validation"
        return 0
    fi
    
    # Detect venv environment
    if [[ -f "venv/bin/activate" ]]; then
        PROJECT_ENV="venv"
        # Note: We'll source venv in setup function
        PYTHON_CMD="python"
        PIP_CMD="pip install"
        RUFF_CMD="ruff"
        MYPY_CMD="mypy"
        PYTEST_CMD="pytest"
        log_success "Virtual environment (venv) detected"
        log_verbose "Will activate venv and use local commands"
        return 0
    fi
    
    # Detect .venv environment
    if [[ -f ".venv/bin/activate" ]]; then
        PROJECT_ENV="dotvenv"
        # Note: We'll source .venv in setup function
        PYTHON_CMD="python"
        PIP_CMD="pip install"
        RUFF_CMD="ruff"
        MYPY_CMD="mypy"
        PYTEST_CMD="pytest"
        log_success "Virtual environment (.venv) detected"
        log_verbose "Will activate .venv and use local commands"
        return 0
    fi
    
    # System Python fallback
    PROJECT_ENV="system"
    PYTHON_CMD="python3"
    PIP_CMD="python3 -m pip install --user"
    RUFF_CMD="python3 -m ruff"
    MYPY_CMD="python3 -m mypy"
    PYTEST_CMD="python3 -m pytest"
    log_warning "Using system Python (no virtual environment detected)"
    log_verbose "Using system Python commands"
    
    return 0
}

# Environment setup function
setup_environment() {
    log_section "Setting Up Environment"
    
    # Setup based on detected environment
    case $PROJECT_ENV in
        "poetry")
            log_info "Installing Poetry dependencies..."
            if poetry install --no-dev 2>/dev/null; then
                log_success "Poetry dependencies installed"
            else
                log_warning "Poetry install failed, trying with dev dependencies"
                poetry install || {
                    log_error "Poetry installation failed"
                    return 1
                }
            fi
            ;;
            
        "venv")
            log_info "Activating virtual environment (venv)..."
            source venv/bin/activate || {
                log_error "Failed to activate venv"
                return 1
            }
            
            log_info "Installing package in development mode..."
            pip install -e . >/dev/null 2>&1 || {
                log_error "Failed to install package in development mode"
                return 1
            }
            log_success "Virtual environment activated and package installed"
            ;;
            
        "dotvenv")
            log_info "Activating virtual environment (.venv)..."
            source .venv/bin/activate || {
                log_error "Failed to activate .venv"
                return 1
            }
            
            log_info "Installing package in development mode..."
            pip install -e . >/dev/null 2>&1 || {
                log_error "Failed to install package in development mode"
                return 1
            }
            log_success "Virtual environment activated and package installed"
            ;;
            
        "system")
            log_warning "Using system Python - some features may be limited"
            ;;
    esac
    
    # Verify environment setup
    log_info "Verifying environment setup..."
    
    # Check Python availability
    if ! $PYTHON_CMD --version >/dev/null 2>&1; then
        log_error "Python not available: $PYTHON_CMD"
        return 1
    fi
    
    local python_version
    python_version=$($PYTHON_CMD --version 2>&1)
    log_verbose "Python version: $python_version"
    
    # Check tool availability
    local missing_tools=()
    
    if ! command -v ruff >/dev/null 2>&1 && ! $RUFF_CMD --version >/dev/null 2>&1; then
        missing_tools+=("ruff")
    fi
    
    if [[ "$SKIP_TYPE_CHECK" != "true" ]] && ! command -v mypy >/dev/null 2>&1 && ! $MYPY_CMD --version >/dev/null 2>&1; then
        missing_tools+=("mypy")
    fi
    
    if [[ "$SKIP_TESTS" != "true" ]] && ! command -v pytest >/dev/null 2>&1 && ! $PYTEST_CMD --version >/dev/null 2>&1; then
        missing_tools+=("pytest")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_warning "Missing tools: ${missing_tools[*]}"
        VALIDATION_WARNINGS+=("missing_tools:${missing_tools[*]}")
    fi
    
    log_success "Environment setup completed"
    VALIDATION_RESULTS+=("environment_setup:PASSED")
    return 0
}

# Python import validation
validate_imports() {
    if [[ "$CHECK_IMPORTS" != "true" ]]; then
        log_verbose "Skipping import check (disabled)"
        return 0
    fi
    
    log_section "Validating Python Imports"
    
    # Test main module import
    log_info "Testing main module import..."
    if $PYTHON_CMD -c "import fast_intercom_mcp; print('✅ Import successful')" 2>/dev/null; then
        log_success "Main module import: PASSED"
        VALIDATION_RESULTS+=("import_test:PASSED")
        return 0
    else
        log_error "Main module import: FAILED"
        log_error "Cannot import fast_intercom_mcp module"
        VALIDATION_RESULTS+=("import_test:FAILED")
        FAILED_VALIDATIONS+=("import_test")
        return 2
    fi
}

# CLI validation
validate_cli() {
    if [[ "$CHECK_CLI" != "true" ]]; then
        log_verbose "Skipping CLI check (disabled)"
        return 0
    fi
    
    log_section "Validating CLI"
    
    # Test CLI availability and basic functionality
    log_info "Testing CLI availability..."
    
    # Try multiple CLI access methods
    local cli_working=false
    
    # Method 1: Poetry script
    if [[ "$PROJECT_ENV" == "poetry" ]] && poetry run fast-intercom-mcp --help >/dev/null 2>&1; then
        cli_working=true
        log_verbose "CLI accessible via Poetry script"
    fi
    
    # Method 2: Python module
    if ! $cli_working && $PYTHON_CMD -m fast_intercom_mcp --help >/dev/null 2>&1; then
        cli_working=true
        log_verbose "CLI accessible via Python module"
    fi
    
    # Method 3: Direct command (if installed)
    if ! $cli_working && command -v fast-intercom-mcp >/dev/null 2>&1 && fast-intercom-mcp --help >/dev/null 2>&1; then
        cli_working=true
        log_verbose "CLI accessible via direct command"
    fi
    
    if $cli_working; then
        log_success "CLI functionality: PASSED"
        VALIDATION_RESULTS+=("cli_test:PASSED")
        return 0
    else
        log_error "CLI functionality: FAILED"
        log_error "Unable to access CLI via any method"
        VALIDATION_RESULTS+=("cli_test:FAILED")
        FAILED_VALIDATIONS+=("cli_test")
        return 6
    fi
}

# Linting validation
validate_linting() {
    if [[ "$SKIP_LINT" == "true" ]]; then
        log_verbose "Skipping linting (disabled)"
        return 0
    fi
    
    log_section "Validating Code Linting"
    
    # Check if ruff is available
    local ruff_available=false
    if command -v ruff >/dev/null 2>&1; then
        ruff_available=true
        RUFF_CMD="ruff"
    elif $RUFF_CMD --version >/dev/null 2>&1; then
        ruff_available=true
    fi
    
    if ! $ruff_available; then
        log_warning "Ruff not available, skipping linting"
        VALIDATION_WARNINGS+=("linting:SKIPPED:ruff_unavailable")
        return 0
    fi
    
    # Auto-fix if requested
    if [[ "$FIX_ISSUES" == "true" ]]; then
        log_info "Auto-fixing linting issues..."
        if $RUFF_CMD check . --fix --config pyproject.toml --exclude __pycache__ --exclude venv --exclude .venv 2>/dev/null; then
            log_success "Auto-fix completed"
        else
            log_warning "Some issues could not be auto-fixed"
        fi
        
        # Format code
        if [[ "$SKIP_FORMAT" != "true" ]]; then
            log_info "Auto-formatting code..."
            if $RUFF_CMD format . --config pyproject.toml --exclude __pycache__ --exclude venv --exclude .venv 2>/dev/null; then
                log_success "Code formatting completed"
            else
                log_warning "Code formatting had issues"
            fi
        fi
    fi
    
    # Run linting check
    log_info "Running linting check..."
    local lint_output
    if lint_output=$($RUFF_CMD check . --config pyproject.toml --exclude __pycache__ --exclude venv --exclude .venv 2>&1); then
        log_success "Linting: PASSED"
        VALIDATION_RESULTS+=("linting:PASSED")
        return 0
    else
        log_error "Linting: FAILED"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "$lint_output"
        else
            echo "$lint_output" | head -10
            if [[ $(echo "$lint_output" | wc -l) -gt 10 ]]; then
                log_info "... (use --verbose for full output)"
            fi
        fi
        VALIDATION_RESULTS+=("linting:FAILED")
        FAILED_VALIDATIONS+=("linting")
        return 3
    fi
}

# Format validation
validate_formatting() {
    if [[ "$SKIP_FORMAT" == "true" ]]; then
        log_verbose "Skipping format check (disabled)"
        return 0
    fi
    
    log_section "Validating Code Formatting"
    
    # Check if ruff is available
    local ruff_available=false
    if command -v ruff >/dev/null 2>&1; then
        ruff_available=true
        RUFF_CMD="ruff"
    elif $RUFF_CMD --version >/dev/null 2>&1; then
        ruff_available=true
    fi
    
    if ! $ruff_available; then
        log_warning "Ruff not available, skipping format check"
        VALIDATION_WARNINGS+=("formatting:SKIPPED:ruff_unavailable")
        return 0
    fi
    
    # Run format check
    log_info "Checking code formatting..."
    if $RUFF_CMD format --check . --config pyproject.toml --exclude __pycache__ --exclude venv --exclude .venv >/dev/null 2>&1; then
        log_success "Code formatting: PASSED"
        VALIDATION_RESULTS+=("formatting:PASSED")
        return 0
    else
        log_error "Code formatting: FAILED"
        log_info "Run with --fix to auto-format code"
        VALIDATION_RESULTS+=("formatting:FAILED")
        FAILED_VALIDATIONS+=("formatting")
        return 3
    fi
}

# Type checking validation
validate_type_checking() {
    if [[ "$SKIP_TYPE_CHECK" == "true" ]]; then
        log_verbose "Skipping type checking (disabled)"
        return 0
    fi
    
    log_section "Validating Type Checking"
    
    # Check if mypy is available
    local mypy_available=false
    if command -v mypy >/dev/null 2>&1; then
        mypy_available=true
        MYPY_CMD="mypy"
    elif $MYPY_CMD --version >/dev/null 2>&1; then
        mypy_available=true
    fi
    
    if ! $mypy_available; then
        log_warning "MyPy not available, skipping type checking"
        VALIDATION_WARNINGS+=("type_checking:SKIPPED:mypy_unavailable")
        return 0
    fi
    
    # Run type checking
    log_info "Running type checking..."
    local type_output
    if type_output=$($MYPY_CMD fast_intercom_mcp/ --config-file pyproject.toml 2>&1); then
        log_success "Type checking: PASSED"
        VALIDATION_RESULTS+=("type_checking:PASSED")
        return 0
    else
        log_error "Type checking: FAILED"
        if [[ "$VERBOSE" == "true" ]]; then
            echo "$type_output"
        else
            echo "$type_output" | head -10
            if [[ $(echo "$type_output" | wc -l) -gt 10 ]]; then
                log_info "... (use --verbose for full output)"
            fi
        fi
        VALIDATION_RESULTS+=("type_checking:FAILED")
        FAILED_VALIDATIONS+=("type_checking")
        return 4
    fi
}

# Test validation
validate_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_verbose "Skipping tests (disabled)"
        return 0
    fi
    
    log_section "Running Tests"
    
    # Check if pytest is available
    local pytest_available=false
    if command -v pytest >/dev/null 2>&1; then
        pytest_available=true
        PYTEST_CMD="pytest"
    elif $PYTEST_CMD --version >/dev/null 2>&1; then
        pytest_available=true
    fi
    
    if ! $pytest_available; then
        log_warning "Pytest not available, skipping tests"
        VALIDATION_WARNINGS+=("tests:SKIPPED:pytest_unavailable")
        return 0
    fi
    
    # Check if tests directory exists
    if [[ ! -d "tests" ]]; then
        log_warning "No tests directory found, skipping tests"
        VALIDATION_WARNINGS+=("tests:SKIPPED:no_tests_dir")
        return 0
    fi
    
    # Run tests
    log_info "Running tests..."
    local test_args="tests/ -x --tb=short -q"
    
    if [[ "$VERBOSE" == "true" ]]; then
        test_args="tests/ -x --tb=short -v"
    fi
    
    if $PYTEST_CMD $test_args; then
        log_success "Tests: PASSED"
        VALIDATION_RESULTS+=("tests:PASSED")
        return 0
    else
        log_error "Tests: FAILED"
        VALIDATION_RESULTS+=("tests:FAILED")
        FAILED_VALIDATIONS+=("tests")
        return 5
    fi
}

# Generate validation report
generate_validation_report() {
    log_section "Validation Results"
    
    local end_time
    end_time=$(date +%s)
    local total_duration=$((end_time - START_TIME))
    
    local passed_validations=0
    local total_validations=0
    
    # Count validation results
    for result in "${VALIDATION_RESULTS[@]}"; do
        total_validations=$((total_validations + 1))
        if [[ "$result" =~ :PASSED ]]; then
            passed_validations=$((passed_validations + 1))
        fi
    done
    
    # Generate summary
    if [[ "$QUIET" != "true" ]]; then
        echo ""
        echo "🔍 $SCRIPT_NAME - Validation Report"
        echo "=================================================================================="
        echo "Environment: $PROJECT_ENV"
        echo "Duration: ${total_duration}s"
        echo "Validations Passed: $passed_validations/$total_validations"
        echo ""
    fi
    
    # Detailed results
    for result in "${VALIDATION_RESULTS[@]}"; do
        local validation_name
        validation_name=$(echo "$result" | cut -d: -f1)
        local validation_status
        validation_status=$(echo "$result" | cut -d: -f2)
        
        case "$validation_status" in
            PASSED)
                log_success "$validation_name: PASSED"
                ;;
            FAILED)
                log_error "$validation_name: FAILED"
                ;;
        esac
    done
    
    # Show warnings
    if [[ ${#VALIDATION_WARNINGS[@]} -gt 0 ]]; then
        echo ""
        for warning in "${VALIDATION_WARNINGS[@]}"; do
            log_warning "$warning"
        done
    fi
    
    if [[ "$QUIET" != "true" ]]; then
        echo ""
        echo "=================================================================================="
    fi
    
    # Final result
    if [[ ${#FAILED_VALIDATIONS[@]} -eq 0 ]]; then
        log_success "Pre-commit validation PASSED ✅"
        return 0
    else
        log_error "Pre-commit validation FAILED ❌"
        if [[ "$QUIET" != "true" ]]; then
            echo ""
            log_error "Failed validations: ${FAILED_VALIDATIONS[*]}"
            if [[ "$FIX_ISSUES" != "true" ]]; then
                log_info "Tip: Use --fix to auto-fix linting and formatting issues"
            fi
        fi
        return 7
    fi
}

# Save results to file if requested
save_validation_results() {
    if [[ -n "$OUTPUT_FILE" ]]; then
        log_info "Saving validation results to: $OUTPUT_FILE"
        
        # Create comprehensive results file
        cat > "$OUTPUT_FILE" << EOF
{
    "validation_metadata": {
        "script_name": "$SCRIPT_NAME",
        "script_version": "$SCRIPT_VERSION",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "duration_seconds": $(($(date +%s) - START_TIME)),
        "environment": "$PROJECT_ENV",
        "config": {
            "fast_mode": $FAST_MODE,
            "fix_issues": $FIX_ISSUES,
            "skip_tests": $SKIP_TESTS,
            "skip_type_check": $SKIP_TYPE_CHECK,
            "skip_lint": $SKIP_LINT,
            "skip_format": $SKIP_FORMAT
        }
    },
    "validation_results": [
$(IFS=$'\n'; for result in "${VALIDATION_RESULTS[@]}"; do
    validation_name=$(echo "$result" | cut -d: -f1)
    validation_status=$(echo "$result" | cut -d: -f2)
    echo "        {\"validation\": \"$validation_name\", \"status\": \"$validation_status\"},"
done | sed '$ s/,$//')
    ],
    "failed_validations": [$(IFS=','; echo "\"${FAILED_VALIDATIONS[*]//,/\",\"}\"")],
    "warnings": [$(IFS=','; echo "\"${VALIDATION_WARNINGS[*]//,/\",\"}\"")],
    "summary": {
        "total_validations": ${#VALIDATION_RESULTS[@]},
        "passed_validations": $((${#VALIDATION_RESULTS[@]} - ${#FAILED_VALIDATIONS[@]})),
        "failed_validations": ${#FAILED_VALIDATIONS[@]},
        "warnings": ${#VALIDATION_WARNINGS[@]},
        "success": $(if [[ ${#FAILED_VALIDATIONS[@]} -eq 0 ]]; then echo "true"; else echo "false"; fi)
    }
}
EOF
        
        log_success "Results saved to: $OUTPUT_FILE"
    fi
}

# Main execution function
main() {
    if [[ "$QUIET" != "true" ]]; then
        log_section "$SCRIPT_NAME v$SCRIPT_VERSION"
        
        if [[ "$FAST_MODE" == "true" ]]; then
            log_info "Running in FAST mode (linting and imports only)"
        elif [[ "$FIX_ISSUES" == "true" ]]; then
            log_info "Running with auto-fix enabled"
        else
            log_info "Running full pre-commit validation"
        fi
    fi
    
    # Run validation sequence
    detect_project_environment || exit 1
    setup_environment || exit 1
    validate_imports || exit 2
    validate_cli || exit 6
    validate_linting || exit 3
    validate_formatting || exit 3
    validate_type_checking || exit 4
    validate_tests || exit 5
    
    # Generate and save results
    generate_validation_report
    local validation_result=$?
    save_validation_results
    
    exit $validation_result
}

# Execute main function
main "$@"