# MySQL Collector Extension

Connects to one or more MySQL instances, queries `SHOW GLOBAL STATUS`, and
emits OpenTelemetry metrics via the Extension Base Library.

## Repository layout

```
sample-extensions/mysql-extension/
├── Containerfile                   # Extension image (build context: repo root)
├── docker-compose.yml              # Starts the local MySQL database only
├── README.md
├── config/
│   ├── extension-config.json       # Endpoints, intervals, OTLP settings
│   └── credentials.json            # Per-endpoint credentials (mount as read-only volume)
├── extension/
│   └── collect.py                  # Collection logic
└── mysql-init/
    └── 01-monitor-user.sql         # Creates the monitor user on first DB start
```

## Prerequisites

- [Podman](https://podman.io/) with Podman Compose
- Access to the base image: `icr.io/instana/collector-extension-runtime-python:latest`
- Access to the [IBM 1Password vault](https://ibm.ent.1password.com) for the `mysql.remote` credential

All commands below are run from the **repo root**.

---

## Collector setup

The extension emits metrics over OTLP gRPC to the address configured in
`otlp.endpoint` (default: `host.containers.internal:4317`). Something must be
listening at that address before you run the extension — if the receiver is
unreachable, export errors will appear in the extension container logs and
metrics will be dropped.

**Option A — Instana agent (recommended)**
Install and configure the Instana agent with OpenTelemetry data ingestion enabled.
See the [Instana agent documentation](https://www.ibm.com/docs/en/instana-observability?topic=instana-agent)
for installation and configuration instructions.

**Option B — OpenTelemetry Collector (for local testing without an agent)**
Run a standalone OpenTelemetry Collector configured with an OTLP gRPC receiver
on port `4317`. See the
[OTel Collector Docker installation guide](https://opentelemetry.io/docs/collector/installation/#docker)
for setup instructions.

---

## 1. Start the local MySQL database

```bash
podman compose -f sample-extensions/mysql-extension/docker-compose.yml up -d
```

Wait until MySQL is healthy (the init script runs automatically on first start):

```bash
podman inspect mysql-extension-mysql-1 --format '{{.State.Health.Status}}'
# Should print: healthy
```

The `mysql-init/01-monitor-user.sql` script creates a `monitor` user with the
`PROCESS` and `REPLICATION CLIENT` privileges required by the extension.
The data directory is persisted in the `mysql_data` named volume across restarts.

To stop and remove the database (keeping data):

```bash
podman compose -f sample-extensions/mysql-extension/docker-compose.yml down
```

To also wipe the data volume:

```bash
podman compose -f sample-extensions/mysql-extension/docker-compose.yml down -v
```

---

## 2. Build the extension image

The build context must be the **repo root** so the `Containerfile` can `COPY`
`sample-extensions/mysql-extension/extension/collect.py` into the image.

### macOS

```bash
podman build --format docker \
    --platform linux/amd64 \
    -f sample-extensions/mysql-extension/Containerfile \
    -t mysql-extension:latest .
```

### Linux

```bash
podman build --format docker \
    -f sample-extensions/mysql-extension/Containerfile \
    -t mysql-extension:latest .
```

---

> **Before running:** To connect to the remote MySQL instance, fill
> in the `mysql.remote` password in `config/credentials.json` first —
> see [Configuration reference → `config/credentials.json`](#configcredentialsjson).

## 3. Run the extension

### macOS

Use `-p 8080:8080` to publish the health port and `host.containers.internal`
(already set in `extension-config.json`) to reach MySQL on the host:

```bash
podman run --rm \
    --platform linux/amd64 \
    -p 8080:8080 \
    -v $(pwd)/sample-extensions/mysql-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    mysql-extension:latest
```

### Linux

> **✅ Recommended** — no config changes needed:

```bash
podman run --rm \
    -p 8080:8080 \
    -v $(pwd)/sample-extensions/mysql-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    mysql-extension:latest
```

> **⚙️ Alternative** — use `--network host` to share the host network stack so
> the container sees `127.0.0.1:3306` directly (requires a one-off config edit):

```bash
sed -i 's/host\.containers\.internal/127.0.0.1/' \
    sample-extensions/mysql-extension/config/extension-config.json
```
```bash
podman run --rm \
    --network host \
    -v $(pwd)/sample-extensions/mysql-extension/config:/opt/instana/custom-collector/config:ro \
    -e INSTANA_LOG_LEVEL=DEBUG \
    mysql-extension:latest
```

---

## 4. Verify

Check the health endpoint:

```bash
curl -s http://localhost:8080/health | python -m json.tool
```

Expected response (once collection has run):

```json
{
    "status": "healthy",
    "extension_id": "mysql-ext-001",
    ...
}
```

---

## Configuration reference

### `config/extension-config.json`

| Field | Description |
|---|---|
| `configuration.interval` | Default collection interval in seconds |
| `configuration.timeout` | MySQL connect/read timeout in seconds |
| `endpoints[].url` | MySQL hostname or IP |
| `endpoints[].port` | MySQL port (default: `3306`) |
| `endpoints[].credentials_ref` | Key in `credentials.json` |
| `endpoints[].enabled` | Set `false` to skip an endpoint without removing it |
| `otlp.endpoint` | OTLP gRPC receiver address (`host:port`) |

### `config/credentials.json`

The `mysql.remote` password is stored in 1Password. Fetch it before running
the extension:

1. Open the [1Password item](https://start.1password.com/open/i?a=CTGAMKNWBZFNJFBH5VL7IA7MJU&v=5oq46k56svfk3nri3cpqctgoiy&i=s52fru3hmy3qzk7423ady53s4m&h=ibm.ent.1password.com)
2. Copy the password
3. Paste it into `config/credentials.json` replacing `<redacted>`:

```json
{
  "mysql.remote": {
    "type":     "basic",
    "username": "avnadmin",
    "password": "<redacted — see 1Password>"
  },
  "mysql.local": {
    "type":     "basic",
    "username": "monitor",
    "password": "monitorpassword"
  }
}
```

> **Never commit a plaintext password to the repository.**
> `credentials.json` is mounted into the container as a read-only volume at
> runtime and must not be baked into the image.

---

## Collected metrics

| Metric | Type | Description |
|---|---|---|
| `mysql.connections.total` | Counter | Total connection attempts since server start |
| `mysql.queries.total` | Counter | Total queries executed since server start |
| `mysql.slow_queries.total` | Counter | Queries exceeding `long_query_time` |
| `mysql.bytes.received` | Counter | Bytes received from all clients |
| `mysql.bytes.sent` | Counter | Bytes sent to all clients |
| `mysql.threads.connected` | Gauge | Currently open connections |
| `mysql.threads.running` | Gauge | Threads actively executing queries |
| `mysql.open_tables` | Gauge | Tables currently open |
| `mysql.collection.duration` | Histogram | Round-trip time for `SHOW GLOBAL STATUS` (ms) |
| `mysql.collection.errors` | Counter | Collection errors, tagged with `error_type` |

---

## MySQL monitor user permissions

The `monitor` user created by `mysql-init/01-monitor-user.sql` requires:

| Grant | Reason |
|---|---|
| `PROCESS` | Required for `SHOW GLOBAL STATUS` |
| `REPLICATION CLIENT` | Required for replication lag metrics |

To also enable Performance Schema metrics, uncomment the relevant line in
`01-monitor-user.sql` and recreate the database volume.
