# 📦 Publishing Guide for PyPI

This guide explains how to publish `webhook-tunnel` to PyPI (Python Package Index).

## Prerequisites

1. PyPI account: https://pypi.org/account/register/
2. TestPyPI account: https://test.pypi.org/account/register/
3. Install build tooling:

```bash
pip install --upgrade build twine
```

## Publishing steps

### 1. Prepare the package

```bash
# Navigate to the project directory
cd webhook-tunnel

# Ensure files look correct
ls -la

# Review project metadata
cat pyproject.toml
```

### 2. Update the version

Update the version in:
- `webhook_tunnel/__init__.py`
- `pyproject.toml`
- `setup.py`

```python
# webhook_tunnel/__init__.py
__version__ = "1.0.0"  # Update here
```

### 3. Maintain a changelog

Add changes to your changelog (or the README if you keep it there):

```markdown
## 📝 Changelog

### v1.0.0 (2024-01-15)
- ✨ Interactive k9s-style TUI
- 🚀 Full Rich-based CLI
- ...
```

### 4. Build the distributions

```bash
# Remove previous builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# This will create:
# dist/webhook-tunnel-1.0.0.tar.gz
# dist/webhook_tunnel-1.0.0-py3-none-any.whl
```

### 5. Verify the distributions

```bash
twine check dist/*

# Expected output:
# Checking dist/webhook-tunnel-1.0.0.tar.gz: PASSED
# Checking dist/webhook_tunnel-1.0.0-py3-none-any.whl: PASSED
```

### 6. Upload to TestPyPI (recommended)

```bash
# Configure credentials
# Create ~/.pypirc:
cat > ~/.pypirc << 'EOF2'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZw...
EOF2

chmod 600 ~/.pypirc

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ webhook-tunnel

# Smoke test
tunnel --help
tunnel-tui
```

### 7. Upload to PyPI

```bash
twine upload dist/*

# You'll see:
# Uploading distributions to https://upload.pypi.org/legacy/
# Uploading webhook-tunnel-1.0.0.tar.gz
# Uploading webhook_tunnel-1.0.0-py3-none-any.whl
# View at: https://pypi.org/project/webhook-tunnel/1.0.0/
```

### 8. Verify the release

```bash
pip install webhook-tunnel

tunnel --help
tunnel-tui
```

## API tokens

### PyPI

1. Go to https://pypi.org/manage/account/token/
2. Click "Add API token"
3. Name: "webhook-tunnel-upload"
4. Scope: "Entire account" or "Project: webhook-tunnel"
5. Copy the token (it starts with `pypi-`)

### TestPyPI

1. Go to https://test.pypi.org/manage/account/token/
2. Follow the same steps

## Automating with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine

    - name: Build package
      run: python -m build

    - name: Publish to PyPI
      env:
        TWINE_USERNAME: __token__
        TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
      run: twine upload dist/*
```

Add the token as a GitHub secret:
- Settings → Secrets → Actions
- New repository secret
- Name: `PYPI_API_TOKEN`
- Value: your PyPI token

## Semantic versioning

Follow SemVer (https://semver.org/):

- **MAJOR** (1.0.0): breaking changes
- **MINOR** (0.1.0): backwards-compatible features
- **PATCH** (0.0.1): backwards-compatible bug fixes

Examples:
- `1.0.0` → first stable release
- `1.1.0` → new feature
- `1.1.1` → bugfix
- `2.0.0` → breaking change

## Publishing checklist

- [ ] Version updated everywhere
- [ ] CHANGELOG.md updated
- [ ] README.md reviewed
- [ ] Tests passing (`pytest`)
- [ ] Code formatted (`black`)
- [ ] Build created (`python -m build`)
- [ ] Distributions verified (`twine check dist/*`)
- [ ] Tested on TestPyPI
- [ ] Published to PyPI
- [ ] Git tag created (`git tag v1.0.0`)
- [ ] Tag pushed (`git push --tags`)
- [ ] GitHub release created

## Useful commands

```bash
# Show installed version
pip show webhook-tunnel

# Uninstall
pip uninstall webhook-tunnel

# Install a specific version
pip install webhook-tunnel==1.0.0

# Upgrade
pip install --upgrade webhook-tunnel

# PyPI stats
# https://pypistats.org/packages/webhook-tunnel
```

## Troubleshooting

### Error: "File already exists"

```bash
# You already uploaded that version. Bump the version and rebuild:
python -m build
twine upload dist/*
```

### Error: "Invalid or non-existent authentication"

```bash
# Check ~/.pypirc or use environment variables:
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmc...
twine upload dist/*
```

### Error: "HTTPError: 403 Forbidden"

```bash
# Check whether the package name exists or whether you have upload permissions
pip search webhook-tunnel
```

## Resources

- PyPI: https://pypi.org/
- TestPyPI: https://test.pypi.org/
- Twine: https://twine.readthedocs.io/
- Packaging Tutorial: https://packaging.python.org/tutorials/packaging-projects/
- SemVer: https://semver.org/

---

Good luck with your release. 🚀
