# Contributing

We welcome contributions to django-fsm-rx! This guide will help you get started.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/specialorange/django-fsm-rx.git
cd django-fsm-rx

# Install dependencies with uv (recommended)
uv sync

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=django_fsm_rx --cov-report=term-missing
```

## Prerequisites

- **Python 3.10+** (we support 3.10, 3.11, 3.12, 3.13, and 3.14)
- **uv** (recommended) or pip for package management
- **graphviz** system package (optional, for graph visualization tests)

### Installing uv

[uv](https://github.com/astral-sh/uv) is a fast Python package manager:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Installing graphviz (Optional)

Only needed if you're working on graph visualization features:

```bash
# macOS
brew install graphviz

# Ubuntu/Debian
sudo apt-get install graphviz

# Fedora
sudo dnf install graphviz

# Windows (with chocolatey)
choco install graphviz
```

## Development Setup

### With uv (Recommended)

```bash
git clone https://github.com/specialorange/django-fsm-rx.git
cd django-fsm-rx

# Install all dependencies (creates .venv automatically)
uv sync

# Activate the virtual environment (optional, uv run handles this)
source .venv/bin/activate
```

### With pip

```bash
git clone https://github.com/specialorange/django-fsm-rx.git
cd django-fsm-rx

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[graphviz]"
pip install pytest pytest-django pytest-cov
```

## Running Tests

### Basic Commands

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_audit_logging.py

# Run specific test class
uv run pytest tests/test_audit_logging.py::TestAuditLogIntegration

# Run specific test
uv run pytest tests/test_audit_logging.py::TestAuditLogIntegration::test_transition_works_with_all_audit_settings

# Run tests matching a pattern
uv run pytest -k "audit"
```

### With Coverage

```bash
# Terminal report
uv run pytest --cov=django_fsm_rx --cov-report=term-missing

# HTML report (opens in browser)
uv run pytest --cov=django_fsm_rx --cov-report=html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Testing Multiple Django Versions

We use tox to test against multiple Python and Django versions:

```bash
# Install tox
pip install tox

# Run all environments (takes a while)
tox

# Run specific environment
tox -e py312-dj52

# List available environments
tox -l
```

**Supported Versions:**

| Django Version | Python Versions |
|----------------|-----------------|
| 4.2 LTS        | 3.10, 3.11      |
| 5.0            | 3.10, 3.11, 3.12 |
| 5.1            | 3.10, 3.11, 3.12 |
| 5.2            | 3.10, 3.11, 3.12, 3.13, 3.14 |
| 6.0            | 3.12, 3.13, 3.14 |

## Code Style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## Type Checking

We use mypy for type checking:

```bash
uv run mypy django_fsm_rx
```

## Pre-commit Hooks

We recommend using pre-commit to catch issues before committing:

```bash
# Install hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Project Structure

```
django-fsm-rx/
├── django_fsm_rx/          # Main package
│   ├── __init__.py         # Core FSM implementation
│   ├── admin.py            # Django admin integration
│   ├── audit.py            # Audit logging
│   ├── conf.py             # Settings configuration
│   ├── models.py           # FSMTransitionLog model
│   ├── signals.py          # Pre/post transition signals
│   └── management/         # Management commands
├── django_fsm/             # Backwards compatibility shim
├── django_fsm_2/           # Backwards compatibility shim
├── tests/                  # Test suite
│   ├── test_audit_logging.py
│   ├── test_settings.py
│   └── ...
├── docs/                   # Documentation
├── pyproject.toml          # Project configuration
└── tox.ini                 # Multi-version test config
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
# or
git checkout -b fix/my-bugfix
```

### 2. Make Your Changes

- Write tests for new functionality
- Update documentation if needed
- Follow the existing code style

### 3. Run Tests

```bash
uv run pytest
uv run ruff check .
```

### 4. Commit

```bash
git add .
git commit -m "Add feature: description of what you added"
```

**Commit Message Guidelines:**
- Start with a verb (Add, Fix, Update, Remove, Refactor)
- Keep the first line under 72 characters
- Reference issues when applicable: "Fix #123: Handle edge case"

### 5. Push and Create PR

```bash
git push origin feature/my-feature
```

Then open a Pull Request on GitHub.

## Pull Request Checklist

Before submitting:

- [ ] Tests added/updated for the changes
- [ ] All tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Documentation updated (if applicable)
- [ ] CHANGELOG.rst updated (for user-facing changes)

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/specialorange/django-fsm-rx/issues) for bugs or feature requests
- **Discussions**: GitHub Discussions for questions and ideas

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
