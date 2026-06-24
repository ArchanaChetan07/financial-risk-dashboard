# CI/CD Pipeline — financial-risk-dashboard

## Overview

Three GitHub Actions workflows power this pipeline:

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci-cd.yml` | Push to `main`/`develop` | Full lint → test → build → deploy |
| `pr-checks.yml` | Pull requests | Fast feedback before merge |
| `retrain.yml` | Weekly (Monday 2am) | Auto-retrain ML models |

---

## Pipeline Flow

```
Push to main
    │
    ├── Lint (flake8, black, isort)
    │
    ├── Security Scan (bandit, safety)
    │
    ├── Tests (pytest + coverage ≥ 70%)
    │       └── MySQL service spun up automatically
    │
    ├── Docker Build & Push → Docker Hub
    │
    └── Deploy via SSH → docker compose up
```

---

## Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `DB_USER` | MySQL username |
| `DB_PASSWORD` | MySQL password |
| `DB_NAME` | MySQL database name |
| `DB_HOST` | MySQL host (for deploy env) |
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `DEPLOY_HOST` | Production server IP/hostname |
| `DEPLOY_USER` | SSH username on production server |
| `DEPLOY_SSH_KEY` | Private SSH key for deployment |

---

## Setup Steps

### 1. Copy workflow files into your repo
```bash
cp -r .github/ /path/to/financial-risk-dashboard/
cp infrastructure/Dockerfile /path/to/financial-risk-dashboard/infrastructure/
cp tests/ /path/to/financial-risk-dashboard/
```

### 2. Add GitHub Secrets
Add all secrets listed above via GitHub UI or CLI:
```bash
gh secret set DB_USER --body "your_db_user"
gh secret set DB_PASSWORD --body "your_db_password"
# ... etc
```

### 3. Create a `.env.example` file
```bash
DB_HOST=localhost
DB_USER=
DB_PASSWORD=
DB_NAME=financial_risk
```

### 4. Push to trigger the pipeline
```bash
git add .
git commit -m "ci: add GitHub Actions CI/CD pipeline"
git push origin main
```

---

## Running Tests Locally

```bash
pip install -r requirements.txt pytest pytest-cov
pytest tests/ -v --cov=scripts --cov-report=term-missing
```

---

## Docker Local Run

```bash
cd infrastructure
docker compose up --build
```
