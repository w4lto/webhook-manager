# 🎉 Webhook Tunnel - Ready to Publish!

## 📦 Project structure

```
webhook-tunnel/
├── webhook_tunnel/          # Main package
│   ├── __init__.py         # Package initialization
│   ├── manager.py          # Tunnel manager
│   ├── cli.py              # CLI interface
│   ├── tui.py              # TUI interface (k9s-style)
│   └── webhook_server.py   # Example server
├── setup.py                 # Legacy packaging
├── pyproject.toml          # Modern build metadata (PEP 517)
├── MANIFEST.in             # Extra packaged files
├── requirements.txt        # Dependencies
├── Makefile                # Task automation
├── install.sh              # Installation script
├── README.md               # Full documentation
├── QUICKSTART.md           # Quick start
├── PUBLISHING.md           # PyPI publishing guide
└── LICENSE                 # MIT license

Extras:
├── .gitignore
├── docker-compose.example.yml
└── nginx-example.conf
```

## 🚀 How to publish to PyPI

### 1. Preparation

```bash
cd webhook-tunnel

# Install build tooling
pip install --upgrade build twine

# Configure your PyPI credentials
# Create ~/.pypirc or use environment variables
```

### 2. Build the package

```bash
# Clean previous builds
make clean

# Build
make build

# Or manually:
python -m build
```

### 3. Test on TestPyPI (recommended)

```bash
# Upload to TestPyPI
make test-pypi

# Or manually:
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ webhook-tunnel

tunnel --help
tunnel-tui
```

### 4. Publish on PyPI

```bash
# Upload to PyPI
make publish

# Or manually:
twine upload dist/*
```

### 5. End-user installation

```bash
# Basic install
pip install webhook-tunnel

# With extras
pip install webhook-tunnel[webhook-server]
```

## 🎯 Available commands

After installation, users will have access to:

```bash
tunnel          # Traditional CLI
tunnel-tui      # TUI (k9s-style)
tunnel-server   # Example webhook receiver
```

## 🖥️ TUI overview

The TUI provides:

- **Real-time dashboard** (CPU/memory, active tunnels)
- **Interactive table** with keyboard navigation
- **Full lifecycle management**: create (`c`), delete (`d`), restart (`r`), logs (`l`), stop all (`k`)
- **Tabbed navigation**: Tunnels, Create, Logs, Help

## 📝 Usage examples

### Basic CLI

```bash
# Create tunnel
tunnel start myapi 3000

# Create tunnel with public internet URL (localtunnel)
tunnel start myapi 3000 --public

# List
tunnel list

# Logs
tunnel logs myapi

# Stop
tunnel stop myapi
```

### Interactive TUI

```bash
tunnel-tui

# Arrow keys to navigate
# 'c' to create
# 'd' to delete
# '?' for help
```

### Example server

```bash
# Terminal 1: start example server
tunnel-server

# Terminal 2: expose port and get external URL
tunnel start webhook 5000 --public

# Terminal 3: test
curl -X POST <external_url>/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## 🔧 Development

```bash
git clone https://github.com/yourusername/webhook-tunnel.git
cd webhook-tunnel

make dev
make test
make format
make lint
make build
```

## 📚 Documentation

- **README.md**: full documentation
- **QUICKSTART.md**: quick start
- **PUBLISHING.md**: PyPI publishing guide
- **Makefile**: available tasks

## 🔑 Dependencies

```text
click>=8.1.0      (CLI)
textual>=0.47.0   (TUI)
rich>=13.0.0      (formatting + tables)
psutil>=5.9.0     (process monitoring)
flask>=3.0.0      (optional: example webhook server)
```

Note: public exposure uses **localtunnel** via **npm/npx**. If Node.js is not installed, the CLI/TUI can offer to install a portable Node.js runtime under `~/.webhook-tunnel/tools/node`.

## 🚧 Roadmap (future ideas)

- Request counter per tunnel
- HTTPS/SSL support
- Additional providers (optional)
- Authentication support
- Rate limiting
- Signed webhook verification
- Export logs to file
- Themes and customization
- Plugin system
- REST API for management

## 🤝 Contributing

1. Fork the project
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m "Add feature"`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

Built for developers.
