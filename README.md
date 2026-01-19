# 🚇 Webhook Tunnel

[![PyPI version](https://badge.fury.io/py/webhook-tunnel.svg)](https://badge.fury.io/py/webhook-tunnel)
[![Python Version](https://img.shields.io/pypi/pyversions/webhook-tunnel.svg)](https://pypi.org/project/webhook-tunnel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A professional Python CLI to expose local ports with a custom hostname, ideal for testing webhooks and callbacks during development. Includes an interactive, k9s-style TUI (Text User Interface).

This version can also expose your local endpoint to the public internet (no account required) using **localtunnel** via **npm/npx**.

![Webhook Tunnel Demo](https://via.placeholder.com/800x400?text=Webhook+Tunnel+TUI)

## ✨ Key Features

- 🚀 **Fast local port exposure**
- 🌐 **Custom hostname** with subdomains
- 🌍 **Public internet URL** via npm/npx (**localtunnel**) for webhook testing
- 💻 **Interactive k9s-style TUI**
- 📊 **Real-time monitoring** (CPU, memory, uptime)
- 🔍 **Built-in log viewer**
- 🎯 **Multiple tunnels** simultaneously
- 💾 **Automatic persistence** (config + tunnel registry)
- 🧹 **Dead process cleanup**

## 📦 Installation

### From PyPI (recommended)

```bash
pip install webhook-tunnel
```

### With extras

```bash
# Full installation with an example webhook server
pip install webhook-tunnel[webhook-server]

# Development extras
pip install webhook-tunnel[dev]
```

## 🚀 Quick Start

### 1) Start your local service

Make sure your application is running locally, e.g.:

```bash
uvicorn app:app --port 8000
```

### 2) Create a tunnel

```bash
tunnel start teste 8000
```

You will get:
- **Hostname URL** (e.g. `http://teste.localhost:8001`) — requires DNS resolution of `teste.localhost`
- **Local URL** (always works) (e.g. `http://127.0.0.1:8001`) — works without any OS DNS changes

If your hostname does not resolve, use the printed `curl --resolve ...` example.

### 3) Expose publicly (for real webhook callbacks)

```bash
tunnel start teste 8000 --public
```

This will:
- keep the local gateway running (port forward)
- start **localtunnel** via **npx**
- print an **External URL** that can be called by third-party webhook providers

If `npx` is not available, the tool can automatically download a portable Node.js LTS runtime into:

```
~/.webhook-tunnel/tools/node
```

## 🖥️ TUI (Interactive Interface)

```bash
tunnel-tui
```

Common keys:
- `c` create a tunnel
- `d` delete a tunnel
- `r` restart a tunnel
- `l` open logs
- `p` toggle public exposure (localtunnel)
- `q` quit

## 🧪 Testing your endpoint

If your local app has `GET /readyz`, you can test via:

- Local gateway:

```bash
curl -v http://127.0.0.1:8001/readyz
```

- Hostname without OS DNS changes:

```bash
curl -v http://127.0.0.1:8001/readyz -H "Host: teste.localhost"
```

- External URL (requires `--public`):

```bash
curl -v <external_url>/readyz
```

## 📚 Documentation

- [Quick Start](QUICKSTART.md)
- [Publishing to PyPI](PUBLISHING.md)

## 📄 License

MIT
