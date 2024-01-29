# GitHub Project Workflows Automation Setup

**Purpose**: Automatically generate and manage issues based on documents created in GitHub Project
**Scope**: `deokhwajeong/BioAI-Nutrition` project
**Created**: 2026-01-15

---

## 📋 Current Status

### ✅ Push Completed
```
Commit: dab9fd7 (main)
Files: 6 files (3,765 lines)
- PROJECT_ROADMAP.md
- ADVANCED_IMPLEMENTATION_GUIDE.md
- GITHUB_PROJECT_SETUP.md
- GITHUB_PROJECT_COMPLETE_PACKAGE.md
- PROJECT_CONFIG.json
- COMPLETION_REPORT.md
```

### 📊 Next Step: Workflows Automation

You can automate the following on GitHub Project's **Workflows** page:

| Workflow | Function | Status |
|----------|----------|--------|
| **Auto-add to Project** | New issue/PR → auto-add to project | ⚙️ Configuration Required |
| **Auto-set Status** | Auto-change status based on label | ⚙️ Configuration Required |
| **Auto-assign Milestone** | Phase label → auto-assign milestone | ⚙️ Configuration Required |
| **Burndown Tracking** | Auto-calculate story points | ⚙️ Configuration Required |

---

## 🔧 GitHub Project Workflows Configuration

### Step 1: Open GitHub Project
```
Repository → Projects → "Personalized Nutrition Platform Roadmap"
```

### Step 2: Click Workflows Tab
```
Project → Automation → (Right) Workflows Button
```

### Step 3: Add Workflow Rules

#### Workflow 1: Auto-add to Project
```
When: Issue or pull request is created
Then:
  ✓ Add to project
  ✓ Set field: Status = Backlog
```

**Configuration**:
- Trigger: Issues, Pull requests
- Action: Add to project
- Status: Backlog

#### Workflow 2: Auto-set Status Based on Label
```
When: Item is added with label
Then: Auto-set Status based on label
```

**Rules**:
| Label | Status |
|-------|--------|
| `in-progress` | In Progress |
| `review` | In Review |
| `done` | Done |
| `blocked` | Blocked |

#### Workflow 3: Phase Label → Milestone Assignment
```
When: Issue labeled with phase-1/2/3/4
Then: Auto-assign Milestone
```

**Rules**:
| Label | Milestone |
|-------|-----------|
| `phase-1` | Q1 2026 |
| `phase-2` | Q2 2026 |
| `phase-3` | Q3 2026 |
| `phase-4` | Q4 2026 |

#### Workflow 4: Update Status on PR Merge
```
When: Pull request merged
Then: Update issue Status → Done
```

---

## 📌 Automatic Issue Generation Script

### Phase 1 Issue Generation Using CLI

```bash
#!/bin/bash
# scripts/create_github_issues.sh

REPO="deokhwajeong/BioAI-Nutrition"

# Epic: User Management & Authentication
echo "Creating Epic: User Management & Authentication..."
gh issue create -R $REPO \
  --title "Epic: User Management & Authentication" \
  --body "## 📖 Epic Overview
User authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management
- Profile customization
- Password recovery

## 📚 Related Documentation
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#user-management--authentication)" \
  --label "epic,phase-1,critical,backend" \
  --milestone "Q1 2026"

# Story: User Registration Endpoint
echo "Creating Story: User Registration..."
gh issue create -R $REPO \
  --title "Story: Implement user registration endpoint" \
  --body "## 👤 User Story
As a new user, I want to register with email and password, so I can access the platform.

## ✅ Acceptance Criteria
- [ ] POST /users accepts email, password, name
- [ ] Password hashed with bcrypt (min 12 rounds)
- [ ] Returns user_id on success
- [ ] Duplicate email → 409 Conflict
- [ ] Invalid input → 422 validation error
- [ ] Email validation (RFC 5322)

## 📚 Reference
[ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#backend-implementation-details)" \
  --label "story,phase-1,backend,critical" \
  --milestone "Q1 2026"

# Story: API Key Authentication
echo "Creating Story: API Key Authentication..."
gh issue create -R $REPO \
  --title "Story: Add API key authentication" \
  --body "## 👤 User Story
As a backend service, I want to validate API keys, so only authorized clients access the API.

## ✅ Acceptance Criteria
- [ ] X-API-Key header validation
- [ ] Invalid keys → 401 Unauthorized
- [ ] Key validation logged (with PII filtering)
- [ ] Tests for valid/invalid keys
- [ ] Rate limiting on failed attempts

## 📚 Reference
[ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#security-implementation)" \
  --label "story,phase-1,backend,critical" \
  --milestone "Q1 2026"

echo "✅ Issues created successfully!"
```

### How to Execute
```bash
# Verify gh CLI installation
which gh

# Run script
chmod +x scripts/create_github_issues.sh
./scripts/create_github_issues.sh
```

---

## 🔗 Link GitHub Project with Documentation

### Add Documentation Links in Issue Body

Each issue should reference related documentation when created:

```markdown
## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#phase-1-core-mvp)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#backend-implementation-details)
- [GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md)
```

### Add Links to Project README

Add the following to `README.md`:

```markdown
## 📋 Project Documentation

- 🗺️ **[PROJECT_ROADMAP.md](PROJECT_ROADMAP.md)** - Strategic roadmap (Q1-Q4 2026)
- 🔧 **[ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md)** - Technical deep dive
- 🚀 **[GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md)** - GitHub project configuration
- 📦 **[PROJECT_CONFIG.json](PROJECT_CONFIG.json)** - Structured project data
- ✨ **[COMPLETION_REPORT.md](COMPLETION_REPORT.md)** - Project summary

## 🎯 Quick Start

1. Read [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for strategy
2. Check [GitHub Project](https://github.com/users/deokhwajeong/projects/2) for current status
3. Review [GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md) for workflow automation
```

---

## 📊 GitHub Project Board Setup

### View 1: Backlog (Priority Sort)
```
Filter: status:Backlog
Sort by: Priority (Critical → High → Medium → Low)
Group by: Phase
```

### View 2: Sprint (Current Progress)
```
Filter: status:"In Progress" OR status:"In Review"
Sort by: Due Date
Show: Assignee, Story Points
```

### View 3: Burndown Chart
```
Chart: Completed points per day (this sprint)
X-axis: Days
Y-axis: Points remaining
```

### View 4: Velocity (Team Performance)
```
Filter: status:Done AND closed_at:[last 4 weeks]
Group by: Week
Show: Total points completed per week
```

---

## ⚙️ GitHub Actions Integration

### New Workflow File: `.github/workflows/project-sync.yml`

```yaml
name: Sync Issues to Project

on:
  issues:
    types: [opened, labeled, unlabeled]
  pull_request:
    types: [opened, closed]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - name: Sync to GitHub Project
      uses: actions/github-script@v7
      with:
        script: |
          const issue = context.payload.issue || context.payload.pull_request;

          // Auto-add phase milestone
          if (issue.labels.some(l => l.name.startsWith('phase-'))) {
            const phase = issue.labels.find(l => l.name.startsWith('phase-')).name;
            const milestoneMap = {
              'phase-1': 'Q1 2026',
              'phase-2': 'Q2 2026',
              'phase-3': 'Q3 2026',
              'phase-4': 'Q4 2026'
            };

            const milestone = milestoneMap[phase];
            if (milestone) {
              // Get milestone ID
              const milestones = await github.rest.issues.listMilestones({
                owner: context.repo.owner,
                repo: context.repo.repo
              });

              const ms = milestones.data.find(m => m.title === milestone);
              if (ms) {
                await github.rest.issues.update({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  issue_number: issue.number,
                  milestone: ms.number
                });
              }
            }
          }

          console.log(`✅ Synced issue #${issue.number}`);
```

---

## 📈 Monitoring & Reporting

### Weekly Report Template

**File**: `.github/ISSUE_TEMPLATE/weekly-report.md`

```markdown
---
name: Weekly Status Report
about: Team status and progress tracking
labels: ['report']
---

## 📊 Sprint Status

**Week of**: [Date range]
**Sprint**: [Sprint name]

### ✅ Completed (Points)
- Story 1 (5 pts)
- Story 2 (8 pts)

### 🔄 In Progress
- Story 3 (13 pts)
- Story 4 (5 pts)

### 📋 Backlog Added
- [New items]

### 🚫 Blocked
- Issue #123: [Reason]

### 📈 Metrics
- **Velocity**: [Points/Week]
- **Burndown**: [On track / Behind]
- **Defects**: [Open bugs]

### 🎯 Next Week Goals
- [ ] Complete Story X
- [ ] Start Phase Y
```

---

## ✅ Checklist: Workflows Configuration Complete

### GitHub Project Automation
- [ ] Create GitHub Project "Personalized Nutrition Platform Roadmap"
- [ ] Set 4 automation rules in Workflows tab
  - [ ] Auto-add to project
  - [ ] Auto-set status by label
  - [ ] Auto-assign milestone
  - [ ] Auto-update on PR merge

### Issue Templates
- [ ] Create `.github/ISSUE_TEMPLATE/epic.md`
- [ ] Create `.github/ISSUE_TEMPLATE/story.md`
- [ ] Create `.github/ISSUE_TEMPLATE/task.md`
- [ ] Create `.github/ISSUE_TEMPLATE/bug.md`

### GitHub Actions
- [ ] Configure `.github/workflows/project-sync.yml`
- [ ] Configure test execution workflow
- [ ] Configure deployment automation

### Documentation
- [ ] Add project links to README.md
- [ ] Add documentation references to each issue
- [ ] Enable GitHub Discussions
- [ ] Create Wiki pages (optional)

### Initial Issues
- [ ] Create Phase 1 Epics (5 total)
- [ ] Create Phase 1 Stories (20-30 total)
- [ ] Create Milestones (Q1-Q4 2026)
- [ ] Define Labels (20+ total)

---

## 🎯 Next Steps (Priority Order)

### Immediate (Today)
1. ✅ Push documentation **Complete**
2. Create GitHub Project (URL access: https://github.com/users/deokhwajeong/projects/2)
3. Add 5 automation rules in Workflows

### This Week
4. Create 5 issue templates
5. Generate 50 Phase 1 issues
6. Add `.github/workflows/project-sync.yml`

### Next Week
7. Start team onboarding
8. Plan first sprint
9. Start daily standups

---

## 📚 Reference Links

### Official GitHub Documentation
- [GitHub Project Automation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project)
- [GitHub Project API](https://docs.github.com/en/graphql/reference/objects#projectv2)
- [GitHub Actions Workflows](https://docs.github.com/en/actions/using-workflows)

### Project Documentation
- [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md)
- [GITHUB_PROJECT_SETUP.md](../GITHUB_PROJECT_SETUP.md)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](../ADVANCED_IMPLEMENTATION_GUIDE.md)

### GitHub Project URL
- **Main Project**: https://github.com/users/deokhwajeong/projects/2
- **Repository**: https://github.com/deokhwajeong/BioAI-Nutrition

---

**Creation Date**: 2026-01-15
**Status**: 📋 Implementation Ready
**Next Update**: 2026-01-22 (Weekly Review)


<!-- reviewed: 2023-09-17 -->
<!-- reviewed: 2024-01-29 -->