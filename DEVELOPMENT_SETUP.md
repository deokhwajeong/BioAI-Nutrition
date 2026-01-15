# 🛠️ Development Environment Setup Guide

**Target Audience**: New team members  
**Last Updated**: 2026-01-15  
**Estimated Setup Time**: 30 minutes

---

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+ / macOS 12+ / Windows 11 (WSL2)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 20GB free
- **Git**: 2.30+

### Required Tools
- Git
- Docker & Docker Compose
- Python 3.11
- Node.js 18+
- npm or pnpm

---

## Quick Start (5 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/deokhwajeong/BioAI-Nutrition.git
cd BioAI-Nutrition
```

### 2. Install Dependencies
```bash
# Backend
cd apps/api
pip install -r requirements.txt

# Frontend
cd ../web
pnpm install

# Return to root
cd ../..
```

### 3. Start Development Servers
```bash
# Terminal 1: Backend API (localhost:8000)
cd apps/api
uvicorn app.main:app --reload

# Terminal 2: Frontend (localhost:3000)
cd apps/web
pnpm dev

# Terminal 3: Database (optional - using Docker)
docker-compose up -d postgres
```

### 4. Verify Setup
```bash
# Backend
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000
```

---

## Detailed Setup Instructions

### Backend Setup

#### Step 1: Python Environment
```bash
cd apps/api

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version
python --version  # Should be 3.11.x
```

#### Step 2: Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install project dependencies
pip install -r requirements.txt

# Verify installations
pip list | grep -E "fastapi|sqlalchemy|pydantic"
```

#### Step 3: Environment Configuration
```bash
# Create .env file from template
cp .env.example .env

# Edit .env with your settings
cat .env
```

**Sample .env**:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bioai_nutrition

# API Configuration
API_KEY=dev-api-key-change-in-production
HASH_PEPPER=dev-pepper-change-in-production

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Feature Flags
DEBUG_MODE=true
ENABLE_IMAGE_ANALYSIS=true
```

#### Step 4: Database Setup
```bash
# Start PostgreSQL (using Docker)
docker run -d \
  --name bioai-postgres \
  -e POSTGRES_USER=bioai_user \
  -e POSTGRES_PASSWORD=bioai_pass \
  -e POSTGRES_DB=bioai_nutrition \
  -p 5432:5432 \
  postgres:15

# Run migrations
alembic upgrade head

# Verify database
psql postgresql://bioai_user:bioai_pass@localhost:5432/bioai_nutrition -c "\dt"
```

#### Step 5: Start Backend
```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python module
python -m uvicorn app.main:app --reload
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

#### Step 6: Test Backend
```bash
# Health check
curl http://localhost:8000/health
# Response: {"status": "healthy"}

# API documentation
# Visit: http://localhost:8000/docs (Swagger UI)
# Visit: http://localhost:8000/redoc (ReDoc)
```

---

### Frontend Setup

#### Step 1: Node.js & pnpm
```bash
cd apps/web

# Verify Node.js version (need 18+)
node --version
npm --version

# Install pnpm
npm install -g pnpm

# Verify pnpm
pnpm --version
```

#### Step 2: Install Dependencies
```bash
# Install project dependencies
pnpm install

# This will install all packages from pnpm-lock.yaml
# Takes ~3-5 minutes
```

#### Step 3: Environment Configuration
```bash
# Create .env.local
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ENVIRONMENT=development
EOF
```

#### Step 4: Start Development Server
```bash
# Development mode (with hot reload)
pnpm dev

# Or specific port
pnpm dev -- -p 3000
```

**Expected Output**:
```
▲ Next.js 16.0.0
  - Local:        http://localhost:3000
  - Environments: .env.local

✓ Ready in 2.5s
```

#### Step 5: Test Frontend
```bash
# Visit in browser
# http://localhost:3000

# Should see the dashboard
# Click on different tabs to test routing
```

---

### Full Docker Compose Setup (Alternative)

#### Step 1: Build Containers
```bash
# From project root
docker-compose build

# This builds both API and web images
```

#### Step 2: Start Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# Expected services:
# - bioai-api (port 8000)
# - bioai-web (port 3000)
# - bioai-postgres (port 5432)
```

#### Step 3: View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f web
```

#### Step 4: Stop Services
```bash
# Stop all
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## IDE Setup

### VS Code (Recommended)

#### Extensions to Install
```bash
# Python Development
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- Pylint (ms-pylint.pylint)

# Frontend Development
- ES7+ React/Redux/React-Native snippets (dsznajder.es7-react-js-snippets)
- Prettier - Code formatter (esbenp.prettier-vscode)
- TypeScript Vue Plugin (Vue.vscode-typescript-vue-plugin)
- TailwindCSS IntelliSense (bradlc.vscode-tailwindcss)

# Git & DevOps
- GitLens (eamodio.gitlens)
- Docker (ms-azuretools.vscode-docker)
- GitHub Copilot (GitHub.copilot)

# General
- REST Client (humao.rest-client)
- Thunder Client (rangav.vscode-thunder-client)
```

#### VS Code Settings
```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/apps/api/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python",
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "[typescript]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

#### Launch Configurations
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "jinja": true,
      "cwd": "${workspaceFolder}/apps/api"
    },
    {
      "name": "JavaScript: Next.js",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/apps/web/node_modules/.bin/next",
      "args": ["dev"],
      "cwd": "${workspaceFolder}/apps/web",
      "skipFiles": ["<node_internals>/**"],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm

1. **Open Project**
   - File → Open → Select BioAI-Nutrition folder
   
2. **Configure Python Interpreter**
   - Settings → Project → Python Interpreter
   - Click gear icon → Add
   - Select "Existing Environment"
   - Navigate to `apps/api/venv/bin/python`

3. **Configure Database**
   - View → Tool Windows → Database
   - Click + → PostgreSQL
   - Host: localhost, Port: 5432
   - User: bioai_user, Password: bioai_pass

4. **Run Configuration**
   - Run → Edit Configurations
   - Click + → Python
   - Module: uvicorn
   - Parameters: app.main:app --reload

---

## Common Issues & Troubleshooting

### Issue: "Python 3.11 not found"
**Solution**:
```bash
# Check available Python versions
python3.11 --version
python3.10 --version

# Or install Python 3.11
brew install python@3.11  # macOS
sudo apt install python3.11  # Ubuntu
```

### Issue: "ModuleNotFoundError: No module named 'fastapi'"
**Solution**:
```bash
# Make sure venv is activated
source apps/api/venv/bin/activate

# Reinstall dependencies
pip install -r apps/api/requirements.txt
```

### Issue: "Database connection refused"
**Solution**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# If not, start it
docker run -d \
  --name bioai-postgres \
  -e POSTGRES_PASSWORD=bioai_pass \
  -p 5432:5432 \
  postgres:15
```

### Issue: "Port 3000 already in use"
**Solution**:
```bash
# Find process using port 3000
lsof -i :3000

# Kill process
kill -9 <PID>

# Or use different port
pnpm dev -- -p 3001
```

### Issue: "pnpm: command not found"
**Solution**:
```bash
# Install pnpm globally
npm install -g pnpm

# Or use npm instead
npm install
npm run dev
```

---

## Code Style & Linting

### Python Code Style

#### Black Formatter
```bash
cd apps/api

# Format all Python files
black .

# Check formatting (dry run)
black --check .

# Format specific file
black app/main.py
```

#### Linting with Pylint
```bash
# Lint all Python files
pylint app/

# Lint with score
pylint --exit-zero app/

# Generate report
pylint app/ --output-format=text > lint_report.txt
```

#### Type Checking with Mypy
```bash
# Type check Python code
mypy app/

# Ignore missing imports
mypy app/ --ignore-missing-imports
```

### TypeScript/JavaScript Code Style

#### Prettier Formatting
```bash
cd apps/web

# Format all files
pnpm prettier --write .

# Check formatting
pnpm prettier --check .
```

#### ESLint
```bash
# Lint JavaScript/TypeScript
pnpm eslint .

# Fix issues automatically
pnpm eslint . --fix
```

---

## Testing

### Backend Tests
```bash
cd apps/api

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api.py

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_api.py::test_health
```

### Frontend Tests
```bash
cd apps/web

# Run Jest tests
pnpm test

# Watch mode
pnpm test --watch

# Coverage report
pnpm test --coverage
```

### End-to-End Tests
```bash
cd apps/web

# Run Playwright tests
pnpm e2e

# Run in headed mode (see browser)
pnpm e2e --headed

# Run specific test
pnpm e2e login.spec.ts
```

---

## Database Management

### Alembic Migrations

```bash
cd apps/api

# Create new migration
alembic revision --autogenerate -m "Add user table"

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# Downgrade to previous
alembic downgrade -1

# Upgrade to specific revision
alembic upgrade 1234abcd
```

### Database Inspection
```bash
# Connect to database
psql postgresql://bioai_user:bioai_pass@localhost:5432/bioai_nutrition

# List tables
\dt

# Describe table
\d users

# Run query
SELECT * FROM users LIMIT 5;

# Exit
\q
```

---

## Git Workflow

### Branch Naming Convention
```
feature/user-registration  # New feature
bugfix/api-timeout         # Bug fix
docs/setup-guide           # Documentation
chore/update-dependencies  # Maintenance
```

### Commit Convention
```
feat: Add user registration endpoint
fix: Resolve database connection timeout
docs: Update API documentation
test: Add unit tests for recommendations
chore: Update dependencies
```

### Pull Request Workflow
```bash
# Create feature branch
git checkout -b feature/meal-logging

# Make changes
git add .
git commit -m "feat: Add meal logging endpoint"

# Push to remote
git push origin feature/meal-logging

# Create pull request via GitHub web UI
# https://github.com/deokhwajeong/BioAI-Nutrition/compare

# After approval, merge and delete branch
git checkout main
git pull origin main
git branch -d feature/meal-logging
```

---

## Performance Optimization Tips

### Backend Performance
```python
# 1. Use database indexes
@app.get("/users/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    # IndexError on indexed columns is fast
    user = db.query(User).filter(User.id == user_id).first()
    return user

# 2. Enable query caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_nutrition_rules():
    # Cache doesn't change often
    return load_rules()

# 3. Use async for I/O operations
async def fetch_meal_data(meal_id: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"http://api/meals/{meal_id}") as resp:
            return await resp.json()
```

### Frontend Performance
```javascript
// 1. Code splitting (Next.js does this automatically)
// 2. Image optimization
import Image from 'next/image'

<Image
  src="/dashboard.png"
  alt="Dashboard"
  width={800}
  height={600}
  loading="lazy"
/>

// 3. Lazy loading components
import dynamic from 'next/dynamic'
const DashboardChart = dynamic(() => import('./Chart'), {
  loading: () => <p>Loading chart...</p>
})
```

---

## Useful Commands Reference

### Docker Commands
```bash
# View running containers
docker ps

# View all containers (including stopped)
docker ps -a

# View container logs
docker logs container-name

# Follow logs
docker logs -f container-name

# Stop container
docker stop container-name

# Remove container
docker rm container-name

# Build image
docker build -t image-name .

# Run image
docker run -d --name container-name image-name
```

### Git Commands
```bash
# View recent commits
git log --oneline -10

# View branch status
git status

# Stash changes
git stash

# Rebase on main
git rebase main

# Interactive rebase (squash commits)
git rebase -i HEAD~5
```

### npm/pnpm Commands
```bash
# Install dependencies
pnpm install

# Add new dependency
pnpm add package-name

# Remove dependency
pnpm remove package-name

# Update dependencies
pnpm update

# List dependencies
pnpm list
```

---

## Quick Reference Checklist

- [ ] Clone repository
- [ ] Create Python virtual environment
- [ ] Install backend dependencies
- [ ] Configure `.env` file
- [ ] Start PostgreSQL database
- [ ] Run database migrations
- [ ] Start backend API (uvicorn)
- [ ] Install Node.js dependencies
- [ ] Configure `.env.local` (frontend)
- [ ] Start frontend dev server
- [ ] Verify both servers running (http://localhost:8000 & http://localhost:3000)
- [ ] Run tests to verify setup
- [ ] Configure IDE (VS Code)
- [ ] Create feature branch for first task
- [ ] Make first commit

---

## Getting Help

### Documentation
- Backend API: http://localhost:8000/docs
- Frontend Components: See `apps/web/components/`
- Architecture: See `ADVANCED_IMPLEMENTATION_GUIDE.md`

### Team Communication
- Questions: Create GitHub Discussion
- Bugs: Create GitHub Issue
- Emergencies: Slack #engineering-emergency
- Daily Standup: 10 AM (team Zoom)

### Resources
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/docs
- PostgreSQL: https://www.postgresql.org/docs/
- Docker: https://docs.docker.com/
- Git: https://git-scm.com/doc

