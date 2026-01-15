# 🚀 GitHub Project Setup Guide

**Target**: Project Managers, Scrum Masters  
**Complexity**: Intermediate | **Duration**: 30 minutes

---

## Overview

This guide explains how to configure the BioAI-Nutrition roadmap using GitHub Project (automated board).

---

## 📋 Setup Checklist

- [ ] Create GitHub Project (Table or Board view)
- [ ] Create Epic issues (Label: epic)
- [ ] Create Story & Task issues (Label: story, task)
- [ ] Configure automation workflows
- [ ] Set GitHub Milestones (quarterly)
- [ ] Set team assignments & owners

---

## 1️⃣ Create GitHub Project

### Step 1: Create New Project
```
GitHub → [Repository] → Projects → New Project
```

**Project Settings**:
- **Name**: `Personalized Nutrition Platform Roadmap`
- **Description**: `Advanced AI-driven wellness platform with privacy-by-design architecture`
- **Template**: `Table` (or `Board` - depending on preference)

### Step 2: Configure Columns (Board/Table view)

#### Board View (Kanban styleban style)
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│    Backlog   │     Todo     │  In Progress │     Done     │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

#### Table View (Spreadsheet styleheet style)
```
| Title | Status | Priority | Team | Due Date | Points | Phase |
|-------|--------|----------|------|----------|--------|-------|
```

---

## 2️⃣ Create Issue Templates

### Epic Template (.github/ISSUE_TEMPLATE/epic.md)
```markdown
---
name: Epic
about: Large feature area (multiple sprints)
labels: ['epic', 'needs-triage']
---

## 📖 Epic Description
[Detailed description]

## 🎯 Goal
[Goal of this epic]

## 📋 Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## 📊 Stories (will be linked)
- Related Story 1
- Related Story 2

## 👥 Owner
[Team/Person]

## 📅 Timeline
**Start**: [Date]  
**Target**: [Date]
```

### Story Template (.github/ISSUE_TEMPLATE/story.md)
```markdown
---
name: User Story
about: Feature development story
labels: ['story', 'needs-estimation']
---

## 👤 As a [user type]
I want to [action/feature]  
So that [benefit/value]

## 📝 Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass

## 🔗 Related
- Epic: [Link to epic]
- Related Stories: [Links]

## 📊 Estimation
**Points**: [5/8/13]  
**Priority**: [Critical/High/Medium/Low]

## 🛠️ Technical Notes
[Implementation hints, architecture considerations]
```

### Task Template (.github/ISSUE_TEMPLATE/task.md)
```markdown
---
name: Task
about: Technical tasks (migration, refactoring, etc.)
labels: ['task']
---

## 📌 Task Description
[Detailed description]

## ✅ Checklist
- [ ] Subtask 1
- [ ] Subtask 2

## 🎯 Definition of Done
- [ ] Code complete
- [ ] Tests written
- [ ] Documentation updated
- [ ] Code review passed

## 📊 Estimation
**Points**: [3/5/8]
```

---

## 3️⃣ Phase 1 Issue Generation Script

### Batch Creation Using CLI (gh CLI)

```bash
#!/bin/bash
# create_phase1_issues.sh

REPO="deokhwajeong/BioAI-Nutrition"

# Epic: User Management & Authentication
gh issue create -R $REPO \
  --title "Epic: User Management & Authentication" \
  --body "## 📖 Epic Description
A complete user authentication and profile management system.

## 🎯 Goals
- User registration & login
- API key management
- Profile customization
- Password recovery

## 📋 Related Stories
- Story: User registration endpoint
- Story: API key authentication
- Story: Profile management API

## 👥 Owner
Backend Team

## 📅 Timeline
**Start**: 2026-01-15  
**Target**: 2026-02-15" \
  --label "epic,phase-1,critical" \
  --milestone "Q1 2026"

# Story: User Registration Endpoint
gh issue create -R $REPO \
  --title "Story: Implement user registration endpoint" \
  --body "## 👤 As a new user
I want to register for an account with email and password  
So that I can access the platform

## 📝 Acceptance Criteria
- [ ] POST /users endpoint accepts email, password
- [ ] Password is hashed with bcrypt
- [ ] User ID is returned
- [ ] Duplicate email returns 400 error
- [ ] Request validation returns 422 for invalid input

## 🔗 Related
- Epic: User Management & Authentication

## 📊 Estimation
**Points**: 5
**Priority**: Critical" \
  --label "story,phase-1,backend,critical" \
  --milestone "Q1 2026"

# Story: API Key Authentication
gh issue create -R $REPO \
  --title "Story: Add API key authentication" \
  --body "## 👤 As a backend service
I want to validate API keys on protected endpoints  
So that only authorized clients can access the API

## 📝 Acceptance Criteria
- [ ] X-API-Key header is required for protected endpoints
- [ ] Invalid keys return 401 Unauthorized
- [ ] Key validation is logged (with PII filtering)
- [ ] Tests cover valid/invalid key scenarios

## 🔗 Related
- Epic: User Management & Authentication

## 📊 Estimation
**Points**: 3
**Priority**: Critical" \
  --label "story,phase-1,backend,critical" \
  --milestone "Q1 2026"

echo "✅ Phase 1 epics and stories created!"
```

### How to Run
```bash
chmod +x create_phase1_issues.sh
./create_phase1_issues.sh
```

---

## 4️⃣ Configure Labels

GitHub → Settings → Labels

### Recommended Labels

#### Phase Labels
- `phase-1` - Q1 2026 MVP
- `phase-2` - Q2 2026 Advanced ML
- `phase-3` - Q3 2026 Community
- `phase-4` - Q4 2026 Enterprise

#### Type Labels
- `epic` - Large feature area
- `story` - User story
- `task` - Technical task
- `bug` - Bug fix
- `enhancement` - Enhancement
- `documentation` - Documentation

#### Priority Labels
- `critical` - 🔴 Urgent (immediate)
- `high` - 🟠 High (this sprint)
- `medium` - 🟡 Medium (coming soon)
- `low` - 🟢 Low (later)

#### Team Labels
- `backend` - Backend team
- `frontend` - Frontend team
- `ml` - ML team
- `data-eng` - Data engineering
- `devops` - DevOps team
- `security` - Security & Compliance

#### Status Labels
- `needs-triage` - Needs review
- `needs-estimation` - Needs points
- `in-progress` - In progress
- `blocked` - Blocked
- `done` - Done

#### Component Labels
- `api` - API/Backend
- `web` - Frontend
- `ml-pipeline` - ML
- `database` - Database
- `infra` - Infrastructure
- `security` - Security/Privacy

---

## 5️⃣ Configure Milestones

GitHub → Settings → Milestones

### Create Milestones

| Milestone | Due Date | Description |
|-----------|----------|-------------|
| Q1 2026 | 2026-03-31 | MVP: Core features (auth, meal ingestion, recommendations) |
| Q2 2026 | 2026-06-30 | Advanced ML: Personalization, activity tracking, validation |
| Q3 2026 | 2026-09-30 | Community: Social features, integrations, content |
| Q4 2026 | 2026-12-31 | Enterprise: Compliance, scaling, analytics |

---

## 6️⃣ Configure Project Automation

### Workflow Rules

#### Rule 1: Auto Status Update (Draft → Backlog)
```
When: Issue is created
Then: Add to Project, Status = Backlog
```

#### Rule 2: Auto Link PR
```
When: PR is created and links issue
Then: Add to Project
```

#### Rule 3: Mark as Complete
```
When: PR is merged
Then: Move issue Status → Done
```

#### Rule 4: Auto Add Label
```
When: Issue in phase-1 milestone
Then: Add label "phase-1"
```

### How to Configure
```
Project → Automation → Workflows

[+] Add workflow
  - Trigger: When issue/PR created
  - Action: Move to Status
  - Custom: Add labels automatically
```

---

## 7️⃣ Configure Dashboard Views

### View 1: Team Dashboard
```
Filter: label:backend OR label:frontend OR label:ml
Group by: Status
Show: Title, Assignee, Points, Due Date
```

### View 2: Priority Matrix
```
Filter: phase-1
Group by: Priority
Sort by: Due Date
Show: Title, Assignee, Points
```

### View 3: Burndown (Milestone view)
```
Milestone: Q1 2026
Show: Issues by Status
Chart: Points completed per day
```

### View 4: Backlog Grooming
```
Filter: needs-estimation OR needs-triage
Sort by: Priority
Show: Title, Team, Description
```

---

## 8️⃣ Team Collaboration Setup

### Assignees (Define Team Leaders)
```
Backend Team Lead: [GitHub Username]
Frontend Team Lead: [GitHub Username]
ML Team Lead: [GitHub Username]
Data Eng Lead: [GitHub Username]
DevOps Lead: [GitHub Username]
Security Lead: [GitHub Username]
```

### Code Owners (.github/CODEOWNERS)
```
# Backend
apps/api/ @backend-team-lead

# Frontend
apps/web/ @frontend-team-lead

# ML
models/ pipelines/ @ml-team-lead

# DevOps
infra/ @devops-team-lead

# Docs
docs/ *.md @team-lead
```

### Branch Protection Rules
```
GitHub → Settings → Branches → main

Require:
- [ ] Pull request reviews before merging (2 approvals)
- [ ] Status checks pass before merging
- [ ] Code coverage >80%
- [ ] Conversation resolution before merge
```

---

## 9️⃣ Sprint Planning Template

### Weekly Sprint Review
```markdown
## 📊 Sprint Status

### Completed ✅
- [x] Story: User registration endpoint (5 points)
- [x] Task: Database schema update (3 points)

### In Progress 🔄
- [ ] Story: API key authentication (3 points)
- [ ] Story: Meal ingestion endpoint (8 points)

### Blocked 🚫
- [ ] Story: Image analysis (depends on model training)

### Metrics
- **Velocity**: 11 points
- **Burndown**: On track
- **Issues**: 0 bugs, 2 tech debt items
```

---

## 🔟 GitHub Actions Integration

### Automated Issue Management (.github/workflows/issue-sync.yml)

```yaml
name: Sync Issues to Project

on:
  issues:
    types: [opened, labeled]

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
    - name: Add issue to project
      uses: actions/github-script@v6
      with:
        script: |
          const issue = context.payload.issue;
          
          // Automatically add milestone if label is phase-1
          if (issue.labels.some(l => l.name === 'phase-1')) {
            github.rest.issues.update({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: issue.number,
              milestone: 1  // Q1 2026 milestone ID
            });
          }
```

### Automated Release Notes (.github/workflows/release-notes.yml)

```yaml
name: Generate Release Notes

on:
  release:
    types: [published]

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
    - name: Generate release notes
      uses: actions/github-script@v6
      with:
        script: |
          const tag = context.ref.replace('refs/tags/', '');
          const issues = await github.rest.issues.listForRepo({
            owner: context.repo.owner,
            repo: context.repo.repo,
            state: 'closed',
            milestone: tag
          });
          
          console.log(JSON.stringify(issues.data, null, 2));
```

---

## 1️⃣1️⃣ Reporting & Monitoring

### Weekly Report

```
GitHub → Insights → Network (or separate script)

Reports:
- Velocity (points completed/sprint)
- Burndown (work over time)
- Issue resolution rate (issues closed ratio)
- PR merge speed
```

### Metrics Dashboard (GitHub Insights)

```
Project Insights:
├── Pull Requests
│   ├── Open/Closed
│   ├── Average time to merge
│   └── Review turnaround
├── Issues
│   ├── Open/Closed
│   ├── Resolution time
│   └── Backlog size
└── Code Frequency
    └── Commits per week
```

---

## 1️⃣2️⃣ Checklist: Setup Complete

### Project Setup
- [ ] Create GitHub Project (Table/Board view)
- [ ] Define columns/status
- [ ] Enable automation workflows

### Issues & Labels
- [ ] Create issue templates (epic, story, task)
- [ ] Define 20+ labels
- [ ] Create 100+ Phase 1 issues

### Organization
- [ ] Create Q1-Q4 milestones
- [ ] Assign team leads
- [ ] Write CODEOWNERS file
- [ ] Set branch protection rules

### Automation
- [ ] Set up GitHub Actions workflows
- [ ] Create auto label rules
- [ ] Set up auto merge rules for PRs

### Reporting
- [ ] Create 3+ dashboard views
- [ ] Set up weekly report template
- [ ] Configure Insights monitoring

---

## 📚 Additional Resources

### GitHub Project API
```bash
# Automate project management using GraphQL
gh api graphql -f query='
  query {
    repository(owner: "deokhwajeong", name: "BioAI-Nutrition") {
      projectsV2(first: 10) {
        nodes {
          id
          title
          items(first: 20) {
            nodes {
              id
              fieldValues(first: 10) {
                nodes {
                  field { name }
                  value
                }
              }
            }
          }
        }
      }
    }
  }
'
```

### Recommended Documentation
- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub Project REST API](https://docs.github.com/en/rest/projects)
- [GitHub Project GraphQL API](https://docs.github.com/en/graphql/reference/objects#projectv2)

---

## 🎉 Wrap-Up

Your **advanced GitHub project** is now fully configured!

**Next Steps**:
1. ✅ Create all issues
2. ✅ Invite & assign team members
3. ✅ Plan first sprint
4. ✅ Start daily standups
5. ✅ Start weekly reviews & retrospectives

