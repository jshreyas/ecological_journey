# Ecological Journey

🥋 _Train, Track, and Transcend_ – A platform for martial artists to annotate, organize, and reflect on their journey with partners, clips, and insights.

## Features

- 🎥 **Video Archive**: Organize training footage by playlist, model, and partner.
- ✂️ **Clip Manager**: Annotate key moments and tag techniques.
- 🧠 **Technique Tracker**: Track progress over time on specific techniques.
- 👥 **Partner Journals**: View training logs and feedback across partners.
- 🔎 **Search & Filter**: Slice across metadata like playlist, model, or time period.
- 🌱 **Self-Hosted & Lightweight**: Runs with FastAPI + NiceGUI.

## Demo

👉 [Live Demo](https://ecological-journey.onrender.com)

## 🔄 Lazy Login Flow (Render-Friendly)

- Backend sleeps on free Render plan
- Login triggers backend to wake
- UI displays:
  > “Waking up servers… Please wait.”

This avoids failed login attempts and improves user clarity.

---

## Local Setup

### Basic Setup

```bash
git clone https://github.com/jshreyas/ecological_journey.git
cd ecological_journey
cp .env.example .env  # configure backend and redis URLs

# Start services
docker-compose up --build
```

### Development Setup with Pre-commit

For contributors and developers, we recommend setting up pre-commit hooks for code quality:

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run all checks manually (optional)
pre-commit run --all-files
```

#### Pre-commit Hooks Include:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting and style checking
- **mypy**: Type checking
- **bandit**: Security vulnerability scanning
- **pydocstyle**: Documentation style checking
- **prettier**: Frontend code formatting
- **hadolint**: Dockerfile linting

### Running Tests

The full pytest suite runs inside the Docker test stack, using the same Python
version and application dependencies as the UI image. MongoDB and Redis are
started as isolated test services; no production services or credentials are
needed. Use the same command locally and in CI:

```bash
bash scripts/test.sh
```

The script builds the test image, runs every test under `tests/`, and removes
the test containers and volumes when it finishes. Pull requests and pushes to
`main` run this workflow. Configure the `unit-tests` job as a required status
check in the repository's branch protection rules or ruleset to prevent merging
before the suite passes.

#### Running Individual Checks:

```bash
# Format code
black ui/ api/ tests/

# Sort imports
isort ui/ api/ tests/

# Lint code
flake8 ui/ api/ tests/

# Type check
mypy ui/ api/ tests/

# Security scan
bandit -r ui/ api/

# Documentation check
pydocstyle ui/ api/
```

#### Code Quality Script:

We provide a convenience script to run all checks:

```bash
./scripts/lint.sh
```

## Production Deployment (Render + Upstash)

- UI and API hosted on Render (free tier)
- Caching via Upstash Redis
- MongoDB via Atlas
- Lazy-login pattern with "Waking up server..." UX for cold start

---

## License

This project is licensed under the [MIT License](./LICENSE).

---

🧠 See `docs/architecture.md` for more.
