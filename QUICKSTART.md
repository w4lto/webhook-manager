# 🚀 Quick Start Guide

## Quick Installation

```bash
# From PyPI (recommended)
pip install webhook-tunnel

# With the example webhook server
pip install webhook-tunnel[webhook-server]
```

## 3-step workflow

### 1) Start your local service

```bash
# Example: FastAPI/Uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Running on http://127.0.0.1:8000
```

### 2) Start a tunnel

#### Traditional CLI

```bash
# Local gateway only
# (Creates a local TCP forward: :<public_port> -> :<local_port>)
tunnel start teste 8000

# Public internet exposure (no account required)
# Always uses localtunnel via npm/npx
tunnel start teste 8000 --public
```

#### TUI (recommended)

```bash
tunnel-tui
```

Common shortcuts:
- `c` create a tunnel
- `d` delete a tunnel
- `r` restart
- `l` logs
- `p` toggle public exposure (localtunnel)
- `q` quit

### 3) Validate reachability

If your app has `GET /readyz`:

#### Local gateway (always works)

```bash
curl -v http://127.0.0.1:<public_port>/readyz
```

#### Hostname without OS DNS changes

If your hostname does not resolve in your OS, you can still test by sending the Host header:

```bash
curl -v http://127.0.0.1:<public_port>/readyz -H "Host: teste.localhost"
```

#### Public internet URL (requires `--public`)

The command output will print an `External URL`. Use it directly:

```bash
curl -v <external_url>/readyz
```

## Essential commands

```bash
# Interactive TUI
tunnel-tui

# Create tunnel
# tunnel start <name> <local_port>
tunnel start myapi 3000

# Create tunnel + public internet URL
tunnel start myapi 3000 --public

# List tunnels
tunnel list

# Tunnel details
tunnel info myapi

# Logs
tunnel logs myapi -f  # -f to follow

# Stop a tunnel
tunnel stop myapi

# Stop all
tunnel stopall

# Global stats
tunnel stats
```

## End-to-end example: testing a webhook receiver

```bash
# Terminal 1: start the example server
tunnel-server

# Terminal 2: expose port 5000 and get an external URL
tunnel start webhook 5000 --public

# Terminal 3: send a test webhook to the external URL
curl -X POST <external_url>/webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "data": {"value": 123}}'

# View received webhooks on http://127.0.0.1:5000
```

## Quick troubleshooting

### "Local port XXXX is not in use"

Start your service first.

```bash
curl -v http://127.0.0.1:8000/readyz
```

### Command not found

Make sure your Python user bin path is in `PATH`.

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Public URL not created

The `--public` option uses npm/npx. If Node.js is not installed, the CLI/TUI can offer to install a portable Node.js runtime under:

```
~/.webhook-tunnel/tools/node
```

## Additional resources

- [Full README](README.md)
