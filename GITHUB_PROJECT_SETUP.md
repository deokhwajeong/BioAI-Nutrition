# 🚀 GitHub 프로젝트 구성 가이드

**대상**: 프로젝트 관리자, Scrum Master  
**복잡도**: 중급 | **소요 시간**: 30분

---

## 개요

이 가이드는 BioAI-Nutrition의 로드맵을 GitHub Project(자동화 보드)로 설정하는 방법을 설명합니다.

---

## 📋 구성 체크리스트

- [ ] GitHub Project 생성 (Table 또는 Board view)
- [ ] Epic 이슈 생성 (Label: epic)
- [ ] 스토리 & 테스크 이슈 생성 (Label: story, task)
- [ ] 자동화 워크플로우 설정
- [ ] GitHub Milestones 설정 (분기별)
- [ ] 팀 할당 & 할당자 설정

---

## 1️⃣ GitHub Project 생성

### Step 1: 새 Project 생성
```
GitHub → [Repository] → Projects → New Project
```

**프로젝트 설정**:
- **Name**: `Personalized Nutrition Platform Roadmap`
- **Description**: `Advanced AI-driven wellness platform with privacy-by-design architecture`
- **Template**: `Table` (또는 `Board` - 선호도에 따라)

### Step 2: 컬럼 설정 (Board/Table view)

#### Board View (칸반식)
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│    Backlog   │     Todo     │  In Progress │     Done     │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

#### Table View (스프레드시트식)
```
| Title | Status | Priority | Team | Due Date | Points | Phase |
|-------|--------|----------|------|----------|--------|-------|
```

---

## 2️⃣ 이슈(Issue) 템플릿 생성

### Epic 템플릿 (.github/ISSUE_TEMPLATE/epic.md)
```markdown
---
name: Epic
about: 큰 기능 영역 (여러 스프린트)
labels: ['epic', 'needs-triage']
---

## 📖 Epic Description
[상세 설명]

## 🎯 Goal
[이 epic의 목표]

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

### Story 템플릿 (.github/ISSUE_TEMPLATE/story.md)
```markdown
---
name: User Story
about: 기능 개발 스토리
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

### Task 템플릿 (.github/ISSUE_TEMPLATE/task.md)
```markdown
---
name: Task
about: 기술 작업 (마이그레이션, 리팩토링 등)
labels: ['task']
---

## 📌 Task Description
[상세 설명]

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

## 3️⃣ Phase 1 이슈 생성 스크립트

### CLI를 이용한 일괄 생성 (gh CLI)

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

### 실행 방법
```bash
chmod +x create_phase1_issues.sh
./create_phase1_issues.sh
```

---

## 4️⃣ Labels 설정

GitHub → Settings → Labels

### 추천되는 Labels

#### Phase Labels
- `phase-1` - Q1 2026 MVP
- `phase-2` - Q2 2026 Advanced ML
- `phase-3` - Q3 2026 Community
- `phase-4` - Q4 2026 Enterprise

#### Type Labels
- `epic` - 큰 기능 영역
- `story` - 사용자 스토리
- `task` - 기술 작업
- `bug` - 버그 수정
- `enhancement` - 개선사항
- `documentation` - 문서화

#### Priority Labels
- `critical` - 🔴 긴급 (즉시)
- `high` - 🟠 높음 (이번 스프린트)
- `medium` - 🟡 중간 (곧 진행)
- `low` - 🟢 낮음 (나중에)

#### Team Labels
- `backend` - 백엔드 팀
- `frontend` - 프론트엔드 팀
- `ml` - ML 팀
- `data-eng` - 데이터 엔지니어링
- `devops` - DevOps 팀
- `security` - 보안 & 컴플라이언스

#### Status Labels
- `needs-triage` - 검토 필요
- `needs-estimation` - 포인트 필요
- `in-progress` - 진행 중
- `blocked` - 차단됨
- `done` - 완료

#### Component Labels
- `api` - API/Backend
- `web` - Frontend
- `ml-pipeline` - ML
- `database` - Database
- `infra` - Infrastructure
- `security` - Security/Privacy

---

## 5️⃣ Milestones 설정

GitHub → Settings → Milestones

### Milestones 생성

| Milestone | Due Date | Description |
|-----------|----------|-------------|
| Q1 2026 | 2026-03-31 | MVP: Core features (auth, meal ingestion, recommendations) |
| Q2 2026 | 2026-06-30 | Advanced ML: Personalization, activity tracking, validation |
| Q3 2026 | 2026-09-30 | Community: Social features, integrations, content |
| Q4 2026 | 2026-12-31 | Enterprise: Compliance, scaling, analytics |

---

## 6️⃣ 프로젝트 자동화 설정

### Workflow 규칙

#### 규칙 1: 자동 Status 업데이트 (Draft → Backlog)
```
When: Issue is created
Then: Add to Project, Status = Backlog
```

#### 규칙 2: PR 자동 연결
```
When: PR is created and links issue
Then: Add to Project
```

#### 규칙 3: 완료 표시
```
When: PR is merged
Then: Move issue Status → Done
```

#### 규칙 4: 자동 라벨 추가
```
When: Issue in phase-1 milestone
Then: Add label "phase-1"
```

### 설정 방법
```
Project → Automation → Workflows

[+] Add workflow
  - Trigger: When issue/PR created
  - Action: Move to Status
  - Custom: Add labels automatically
```

---

## 7️⃣ 대시보드 뷰 설정

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

### Assignees (팀 리더 정의)
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

### 브랜치 보호 규칙
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

## 1️⃣1️⃣ 보고 및 모니터링

### 주간 보고서 (Weekly Report)

```
GitHub → Insights → Network (또는 별도 스크립트)

Reports:
- Velocity (완료한 포인트/스프린트)
- Burndown (시간 경과에 따른 작업량)
- Issue 해결율 (Issue 종료 비율)
- PR 병합 속도
```

### Metrics 대시보드 (GitHub Insights)

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

## 1️⃣2️⃣ 체크리스트: 설정 완료

### Project 설정
- [ ] GitHub Project 생성 (Table/Board view)
- [ ] 컬럼/상태 정의
- [ ] 자동화 워크플로우 활성화

### Issues & Labels
- [ ] Issue 템플릿 생성 (epic, story, task)
- [ ] 20+ Labels 정의
- [ ] Phase 1 이슈 100개+ 생성

### Organization
- [ ] Q1-Q4 Milestones 생성
- [ ] 팀 lead 할당
- [ ] CODEOWNERS 파일 작성
- [ ] 브랜치 보호 규칙 설정

### Automation
- [ ] GitHub Actions 워크플로우 설정
- [ ] 자동 라벨 추가 규칙
- [ ] PR 자동 병합 규칙

### Reporting
- [ ] 대시보드 뷰 3개 이상 생성
- [ ] 주간 보고 템플릿
- [ ] Insights 모니터링 설정

---

## 📚 추가 자료

### GitHub Project API
```bash
# GraphQL을 사용한 프로젝트 관리 자동화
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

### 추천 문서
- [GitHub Projects Documentation](https://docs.github.com/en/issues/planning-and-tracking-with-projects)
- [GitHub Project REST API](https://docs.github.com/en/rest/projects)
- [GitHub Project GraphQL API](https://docs.github.com/en/graphql/reference/objects#projectv2)

---

## 🎉 마치며

이제 **고급 수준의 GitHub 프로젝트**가 완전히 설정되었습니다!

**다음 단계**:
1. ✅ 모든 이슈 생성
2. ✅ Team members 초대 & 할당
3. ✅ 첫 스프린트 계획
4. ✅ Daily standup 시작
5. ✅ 주간 review & retro

