#!/bin/bash
# (c) Copyright IBM Corp. 2026
# Container entrypoint script for Instana Collector Extension Runtime
#
# This script initializes the container environment and starts the extension process
# with proper error handling, logging, and signal management.

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Configuration
readonly EXTENSION_HOME="${INSTANA_EXTENSION_HOME:-/opt/instana/custom-collector}"
readonly CONFIG_DIR="${EXTENSION_HOME}/config"
readonly EXTENSION_DIR="${EXTENSION_HOME}/extensions"
readonly LOG_LEVEL="${INSTANA_LOG_LEVEL:-INFO}"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date -u +"%Y-%m-%dT%H:%M:%SZ") $*" >&2
}

log_json() {
    local level="$1"
    local message="$2"
    echo "{\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"level\":\"${level}\",\"message\":\"${message}\"}"
}

# Validate environment
validate_environment() {
    log_info "Validating environment..."

    # Check Python runtime
    if ! command -v python &> /dev/null; then
        log_error "Python runtime not found"
        exit 1
    fi

    local python_version
    python_version=$(python --version 2>&1 | awk '{print $2}')
    log_info "Python version: ${python_version}"

    # Check required directories
    if [[ ! -d "${EXTENSION_HOME}" ]]; then
        log_error "Extension home directory not found: ${EXTENSION_HOME}"
        exit 1
    fi

    # Check if config directory is mounted (optional at startup)
    if [[ ! -d "${CONFIG_DIR}" ]]; then
        log_warn "Config directory not found: ${CONFIG_DIR} (will be mounted at runtime)"
    fi

    # Check if extensions directory is mounted (optional at startup)
    if [[ ! -d "${EXTENSION_DIR}" ]]; then
        log_warn "Extensions directory not found: ${EXTENSION_DIR} (will be mounted at runtime)"
    fi

    log_info "Environment validation completed"
}

# Load configuration
load_configuration() {
    log_info "Loading configuration..."

    local config_file="${CONFIG_DIR}/extension-config.json"

    if [[ -f "${config_file}" ]]; then
        log_info "Configuration file found: ${config_file}"

        # Validate JSON syntax
        if ! python -m json.tool "${config_file}" > /dev/null 2>&1; then
            log_error "Invalid JSON in configuration file: ${config_file}"
            exit 1
        fi

        export INSTANA_EXTENSION_CONFIG="${config_file}"
    else
        log_warn "Configuration file not found: ${config_file}"
    fi

    log_info "Configuration loading completed"
}

# Setup logging
setup_logging() {
    log_info "Setting up logging..."

    export PYTHONUNBUFFERED=1
    export INSTANA_LOG_LEVEL="${LOG_LEVEL}"

    log_info "Log level set to: ${LOG_LEVEL}"
    log_info "Logging setup completed"
}

# Start extension process
start_extension() {
    log_info "Starting extension process..."

    # Execute the command passed to the container
    if [[ $# -eq 0 ]]; then
        log_error "No command specified"
        exit 1
    fi

    log_info "Executing: $*"

    # Use exec to replace the shell with the extension process
    # This makes the extension process receive signals directly from tini
    # and eliminates the shell as an intermediary
    exec "$@"
}

# Main execution
main() {
    log_info "=== Instana Collector Extension Runtime ==="
    log_info "Starting container initialization..."

    validate_environment
    load_configuration
    setup_logging

    log_info "Initialization completed, starting extension..."

    # Start the extension with all arguments passed to the script
    start_extension "$@"
}

# Run main function with all script arguments
main "$@"

# Made with Bob
