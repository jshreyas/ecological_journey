# Code Quality Setup and Guidelines

## 🎯 Overview

This document outlines the code quality setup for the Ecological Journey project, including pre-commit hooks, linting tools, and guidelines for maintaining code quality.

## 📋 Pre-commit Configuration

### Installed Hooks

1. **Black** (Code Formatting)
   - Automatically formats Python code to PEP 8 standards
   - Line length: 88 characters
   - Target Python version: 3.10

2. **isort** (Import Sorting)
   - Sorts and organizes imports
   - Compatible with Black formatting
   - Profile: black

3. **flake8** (Linting)
   - Checks for style violations and potential errors
   - Max line length: 88 characters
   - Ignores: E203, W503 (compatible with Black)

4. **mypy** (Type Checking)
   - Static type checking for Python
   - Ignores missing imports for external libraries
   - Relaxed settings for gradual adoption

5. **bandit** (Security Scanning)
   - Scans for common security vulnerabilities
   - Excludes test files
   - Outputs JSON report

6. **pydocstyle** (Documentation Style)
   - Checks docstring formatting
   - Uses Google style convention
   - Currently configured to ignore most docstring issues for gradual adoption

7. **prettier** (Frontend Formatting)
   - Formats JavaScript, CSS, HTML, and JSON files
   - Ensures consistent frontend code style

8. **hadolint** (Dockerfile Linting)
   - Lints Dockerfiles for best practices
   - Identifies potential issues and improvements

## 🚀 Quick Start

### For New Contributors

1. **Clone and Setup**:

   ```bash
   git clone https://github.com/jshreyas/ecological_journey.git
   cd ecological_journey
   ```

2. **Install Development Dependencies**:

   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Install Pre-commit Hooks**:

   ```bash
   pre-commit install
   ```

4. **Verify Setup**:
   ```bash
   pre-commit run --all-files
   ```

### For Existing Contributors

After pulling latest changes:

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Run checks on all files
pre-commit run --all-files
```

## 📁 Configuration Files

### `.pre-commit-config.yaml`

- Main configuration for all pre-commit hooks
- Defines versions and settings for each tool

### `pyproject.toml`

- Configuration for Black, isort, mypy, and pydocstyle
- Project metadata and dependencies

### `.flake8`

- Flake8 configuration
- Defines line length, ignored errors, and exclusions

### `requirements-dev.txt`

- Development dependencies
- Includes all linting and testing tools

## 🔧 Current Status

### ✅ Completed

- [x] Pre-commit configuration setup
- [x] Basic linting tools installed
- [x] Development dependencies documented
- [x] README updated with setup instructions
- [x] Convenience scripts created

### ⚠️ Partially Complete

- [x] Type annotations added to core functions
- [x] Basic formatting applied
- [x] Import sorting configured

### 🔄 In Progress / Remaining Tasks

#### Phase 1: Critical Issues (High Priority)

- [ ] Fix remaining mypy type errors in `ui/utils/utils_api.py`
- [ ] Fix ambiguous variable names (E741 errors)
- [ ] Remove unused imports (F401 errors)
- [ ] Fix line length violations (E501 errors)
- [ ] Remove unused variables (F841 errors)

#### Phase 2: Code Quality Improvements (Medium Priority)

- [ ] Add comprehensive docstrings to all public functions
- [ ] Improve type annotations throughout codebase
- [ ] Fix bandit security warnings
- [ ] Add proper error handling

#### Phase 3: Documentation and Standards (Low Priority)

- [ ] Create coding standards document
- [ ] Add inline comments for complex logic
- [ ] Improve test coverage
- [ ] Add API documentation

## 🛠️ Common Issues and Solutions

### MyPy Type Errors

```bash
# Install missing type stubs
pip install types-requests types-PyYAML types-pytz types-redis

# Run mypy with more lenient settings
mypy --ignore-missing-imports ui/ api/
```

### Flake8 Line Length Issues

```bash
# Auto-format with Black
black ui/ api/ tests/

# Check specific files
flake8 ui/pages/film.py
```

### Import Issues

```bash
# Auto-sort imports
isort ui/ api/ tests/

# Check for unused imports
flake8 --select=F401 ui/ api/
```

## 📊 Quality Metrics

### Current Statistics

- **Total Python Files**: ~50
- **Lines of Code**: ~15,000
- **Pre-commit Hooks**: 8 active
- **Automated Checks**: 6 categories

### Quality Targets

- [ ] Zero flake8 errors
- [ ] Zero mypy errors (with current settings)
- [ ] Zero bandit security issues
- [ ] 100% docstring coverage for public APIs
- [ ] 90%+ test coverage

## 🤝 Contributing Guidelines

### Before Submitting PR

1. Run pre-commit hooks: `pre-commit run --all-files`
2. Ensure all tests pass: `pytest tests/`
3. Check for security issues: `bandit -r ui/ api/`
4. Verify type checking: `mypy ui/ api/`

### Code Style

- Follow Black formatting (88 character line length)
- Use type hints for all function parameters and return values
- Add docstrings for all public functions and classes
- Use descriptive variable names (avoid single letters like 'l')

### Commit Messages

- Use conventional commit format
- Include issue numbers when applicable
- Be descriptive about changes

## 🔍 Monitoring and Maintenance

### Regular Tasks

- [ ] Weekly: Run full pre-commit suite
- [ ] Monthly: Update dependency versions
- [ ] Quarterly: Review and update coding standards

### Tools to Monitor

- Pre-commit hook success rate
- MyPy error count
- Flake8 violation count
- Security scan results

## 📚 Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

**Note**: This setup is designed for gradual adoption. The current configuration is lenient to allow for incremental improvements without blocking development. As the codebase matures, we can tighten these standards.
