#!/bin/bash
# (c) Copyright IBM Corp. 2026
# Container health check script for Instana Collector Extension Runtime
#
# This script provides health status for container orchestration systems
# (Podman, Kubernetes) to make restart decisions and traffic routing.
#
# Exit codes:
#   0 — healthy or degraded (container stays up, collection is running)
#   1 — unhealthy (container should be restarted)
#
# Two-stage check:
#   1. pgrep: fast early-exit if the Python process is gone entirely
#   2. curl GET /health: authoritative verdict from the HealthReporter
#      HTTP 200 → healthy or degraded → exit 0
#      HTTP 503 → unhealthy           → exit 1
#      curl error / timeout           → exit 1

# Configuration
readonly HEALTH_PORT="${INSTANA_HEALTH_PORT:-8080}"
readonly HEALTH_CHECK_TIMEOUT="${INSTANA_HEALTH_CHECK_TIMEOUT:-5}"

# Exit codes
readonly EXIT_HEALTHY=0
readonly EXIT_UNHEALTHY=1

# Guard: fail fast if the Python process is not running at all.
# This avoids a curl timeout during early startup before the HTTP server binds,
# and catches the case where the process has died silently.
check_process_health() {
    pgrep -f "python" > /dev/null 2>&1
}

# Authoritative health verdict: poll the /health HTTP endpoint served by
# HealthReporter inside the extension process.
#   HTTP 200 — healthy or degraded — collection is running
#   HTTP 503 — unhealthy           — all endpoints failed, restart warranted
#   curl failure (timeout, ECONNREFUSED) treated as unhealthy
check_http_health() {
    local http_code
    http_code=$(curl --silent --output /dev/null \
                     --write-out "%{http_code}" \
                     --max-time "${HEALTH_CHECK_TIMEOUT}" \
                     "http://localhost:${HEALTH_PORT}/health")
    [[ "${http_code}" -eq 200 ]]
}

# Main health check
main() {
    if ! check_process_health; then
        echo "UNHEALTHY: Extension process not running"
        exit ${EXIT_UNHEALTHY}
    fi

    if check_http_health; then
        echo "HEALTHY: /health returned 200"
        exit ${EXIT_HEALTHY}
    else
        echo "UNHEALTHY: /health did not return 200"
        exit ${EXIT_UNHEALTHY}
    fi
}

# Run main function
main "$@"

# Made with Bob
