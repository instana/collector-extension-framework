# HTTP API Collector Extension

Polls a small local REST API, parses JSON from a `/stats` endpoint, and emits
OpenTelemetry metrics via the Extension Base Library.

## Repository layout

```
sample-extensions/http-api-extension/
├── Containerfile                   # Extension image (build context: repo root)
├── README.md
├── config/
│   ├── extension-config.json       # Endpoint, interval, and OTLP settings
│   └── credentials.json            # Bearer token for the demo API
├── demo-api/
│   ├── requirements.txt            # Local demo API dependencies
│   └── server.py                   # Small Flask server returning JSON
└── extension/
    └── collect.py                  # Collection logic
```

## Prerequisites

- [Podman](https://podman.io/)
- Access to the base image: `icr.io/instana/collector-extension-runtime-python:latest`
- Python with `pip` available on the host for the local demo API setup
- An OTLP receiver listening on `host.containers.internal:4317` or an updated
  value in [`config/extension-config.json`](config/extension-config.json)

All commands below are run from the **repo root**.

---

## 1. Start the local demo API

Install the local demo API dependencies first:

```bash
pip install -r sample-extensions/http-api-extension/demo-api/requirements.txt
```

Then start the Flask demo API on the host:

```bash
python sample-extensions/http-api-extension/demo-api/server.py
```

The Flask server listens on `http://localhost:18080` and exposes:
- `GET /health` without authentication
- `GET /stats` with `Authorization: Bearer demo-secret-token`

Quick verification:

```bash
curl -s http://localhost:18080/health | python -m json.tool
```

```bash
curl -s -H 'Authorization: Bearer demo-secret-token' \
    http://localhost:18080/stats | python -m json.tool
```

---

## 2. Build the extension image

The build context must be the **repo root** so the [`Containerfile`](Containerfile)
can `COPY` [`sample-extensions/http-api-extension/extension/collect.py`](extension/collect.py)
into the image.

### macOS

```bash
podman build --format docker \
    --platform linux/amd64 \
    -f sample-extensions/http-api-extension/Containerfile \
    -t http-api-extension:latest .
```

### Linux

```bash
podman build --format docker \
    -f sample-extensions/http-api-extension/Containerfile \
    -t http-api-extension:latest .
```

---

## 3. Run the extension

### macOS

Use `-p 8080:8080` to publish the health port and `host.containers.internal`
(already set in [`extension-config.json`](config/extension-config.json))
to reach the demo API on the host:

```bash
podman run --rm \
    --platform linux/amd64 \
    -p 8080:8080 \
    -v $(pwd)/sample-extensions/http-api-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    http-api-extension:latest
```

### Linux

> **✅ Recommended** — no config changes needed:

```bash
podman run --rm \
    -p 8080:8080 \
    -v $(pwd)/sample-extensions/http-api-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    http-api-extension:latest
```

> **⚙️ Alternative** — use `--network host` to share the host network stack so
> the container sees `127.0.0.1:18080` directly (requires a one-off config edit):

```bash
sed -i 's/host\.containers\.internal/127.0.0.1/' \
    sample-extensions/http-api-extension/config/extension-config.json
```
```bash
podman run --rm \
    --network host \
    -v $(pwd)/sample-extensions/http-api-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    http-api-extension:latest
```

---

## 4. Verify

Check the extension health endpoint:

```bash
curl -s http://localhost:8080/health | python -m json.tool
```

You should also see collection log lines for the configured endpoint and JSON
payload.

---

## Configuration reference

### [`config/extension-config.json`](config/extension-config.json)

| Field | Description |
|---|---|
| `configuration.interval` | Default collection interval in seconds |
| `configuration.timeout` | HTTP request timeout in seconds |
| `endpoints[].url` | Demo API hostname or IP |
| `endpoints[].port` | Demo API port |
| `endpoints[].credentials_ref` | Key in [`credentials.json`](config/credentials.json) |
| `endpoints[].enabled` | Set `false` to skip an endpoint |
| `endpoints[].tags` | Tags automatically attached to every metric |
| `otlp.endpoint` | OTLP gRPC receiver address (`host:port`) |

### [`config/credentials.json`](config/credentials.json)

This sample uses a bearer token credential:

```json
{
  "demo.api.token": {
    "type": "token",
    "token": "demo-secret-token"
  }
}
```

---

## Collected metrics

| Metric | Type | Description |
|---|---|---|
| `demo.api.uptime` | Gauge | Demo API uptime in seconds |
| `demo.api.active_requests` | Gauge | Current active requests |
| `demo.api.error_count` | Counter | Total errors reported by the API |
| `demo.api.queue_depth` | Gauge | Current queue depth |
| `demo.api.jobs.total` | Gauge | Number of jobs returned in the payload |
| `demo.api.jobs.failed` | Gauge | Number of failed jobs |
| `demo.api.jobs.failure_rate` | Gauge | Failed jobs divided by total jobs |
| `demo.api.collection.duration` | Histogram | Time spent fetching `/stats` |
| `demo.api.collection.errors` | Counter | Collection failures, tagged by error type |
