#!/usr/bin/env python3
# (c) Copyright IBM Corp. 2026
"""Small Flask demo API for the HTTP API sample extension."""

import time

from flask import Flask, jsonify, request

HOST = "0.0.0.0"
PORT = 18080
BEARER_TOKEN = "demo-secret-token"
START_TIME = time.time()
JOBS = [
    {
        "id": "job-1",
        "name": "daily-import",
        "status": "success",
        "duration_seconds": 42,
    },
    {
        "id": "job-2",
        "name": "customer-sync",
        "status": "running",
        "duration_seconds": 95,
    },
    {
        "id": "job-3",
        "name": "invoice-export",
        "status": "failed",
        "duration_seconds": 18,
    },
    {
        "id": "job-4",
        "name": "cache-refresh",
        "status": "queued",
        "duration_seconds": 0,
    },
]

app = Flask(__name__)


@app.get("/health")
def health() -> tuple:
    return (
        jsonify(
            {
                "status": "ok",
                "service": "demo-api",
                "uptime_seconds": int(time.time() - START_TIME),
            }
        ),
        200,
    )


@app.get("/stats")
def stats() -> tuple:
    if request.headers.get("Authorization") != f"Bearer {BEARER_TOKEN}":
        return jsonify({"error": "missing or invalid bearer token"}), 401

    active_requests = sum(1 for job in JOBS if job["status"] == "running")
    queue_depth = sum(1 for job in JOBS if job["status"] in {"queued", "running"})
    error_count = sum(1 for job in JOBS if job["status"] == "failed")

    return (
        jsonify(
            {
                "uptime_seconds": int(time.time() - START_TIME),
                "active_requests": active_requests,
                "error_count": error_count,
                "queue_depth": queue_depth,
                "jobs": JOBS,
            }
        ),
        200,
    )


if __name__ == "__main__":
    print(f"Demo API listening on http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT)
