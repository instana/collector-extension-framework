# Documentation

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://astral.sh/uv/) (Python package manager)
- [Podman](https://podman.io/) (container engine)

### Project Setup

```shell
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/instana/collector-extension-framework.git

# Create virtual environment and install dependencies
cd collector-extension-framework
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### Building the Extension Runtime Container Image

```shell
cd container
podman build --format docker -t instana/collector-extension-runtime-python:1.0.0 -f Containerfile .
```

### Running the Extension Runtime Container Image

```shell
podman run --rm instana/collector-extension-runtime-python:1.0.0 python --version
```

### Building the Extension Base Library

```shell
cd base_library
uv build
```
This builds the base library as a Python Wheel file located in the `dist` directory of the project root.

```shell
collector-extension-framework/dist/extension_base-<VERSION>.tar.gz
collector-extension-framework/dist/extension_base-<VERSION>-py3-none-any.whl
```

### Running the Extension Base Library

```shell
uv run - <<EOF
import extension_base
from importlib.metadata import version
version_ = version("extension-base")
print(f">>> Hello from extension-base v{version_}!")
EOF
```
