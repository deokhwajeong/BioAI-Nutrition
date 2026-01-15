# GitHub Project Workflows 자동화 설정

**목적**: GitHub Project에 생성된 문서를 기반으로 이슈 자동 생성 & 관리  
**적용 범위**: `deokhwajeong/BioAI-Nutrition` 프로젝트  
**작성일**: 2026-01-15

---

## 📋 현재 상태

### ✅ 푸시 완료
```
Commit: dab9fd7 (main)
Files: 6개 (3,765 라인)
- PROJECT_ROADMAP.md
- ADVANCED_IMPLEMENTATION_GUIDE.md
- GITHUB_PROJECT_SETUP.md
- GITHUB_PROJECT_COMPLETE_PACKAGE.md
- PROJECT_CONFIG.json
- COMPLETION_REPORT.md
```

### 📊 다음 단계: Workflows 자동화

GitHub Project의 **Workflows** 페이지에서 다음을 자동화할 수 있습니다:

| Workflow | 기능 | 상태 |
|----------|------|------|
| **Auto-add to Project** | 새 이슈/PR → 자동 프로젝트 추가 | ⚙️ 설정 필요 |
| **Auto-set Status** | 라벨 기반 Status 자동 변경 | ⚙️ 설정 필요 |
| **Auto-assign Milestone** | Phase 라벨 → Milestone 자동 할당 | ⚙️ 설정 필요 |
| **Burndown Tracking** | Story Points 자동 계산 | ⚙️ 설정 필요 |

---

## 🔧 GitHub Project Workflows 설정

### Step 1: GitHub Project 열기
```
Repository → Projects → "Personalized Nutrition Platform Roadmap"
```

### Step 2: Workflows 탭 클릭
```
Project → Automation → (오른쪽) Workflows 버튼
```

### Step 3: 워크플로우 규칙 추가

#### Workflow 1: 자동 프로젝트 추가
```
When: Issue or pull request is created
Then: 
  ✓ Add to project
  ✓ Set field: Status = Backlog
```

**설정**:
- Trigger: Issues, Pull requests
- Action: Add to project
- Status: Backlog

#### Workflow 2: 라벨 기반 Status 변경
```
When: Item is added with label
Then: Auto-set Status based on label
```

**규칙**:
| Label | Status |
|-------|--------|
| `in-progress` | In Progress |
| `review` | In Review |
| `done` | Done |
| `blocked` | Blocked |

#### Workflow 3: Phase 라벨 → Milestone 할당
```
When: Issue labeled with phase-1/2/3/4
Then: Auto-assign Milestone
```

**규칙**:
| Label | Milestone |
|-------|-----------|
| `phase-1` | Q1 2026 |
| `phase-2` | Q2 2026 |
| `phase-3` | Q3 2026 |
| `phase-4` | Q4 2026 |

#### Workflow 4: PR 병합 시 Status 변경
```
When: Pull request merged
Then: Update issue Status → Done
```

---

## 📌 이슈 자동 생성 스크립트

### CLI를 이용한 Phase 1 이슈 생성

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

### 실행 방법
```bash
# gh CLI 설치 확인
which gh

# 스크립트 실행
chmod +x scripts/create_github_issues.sh
./scripts/create_github_issues.sh
```

---

## 🔗 GitHub Project와 문서 연결

### 이슈 본문에 문서 링크 추가

각 이슈를 만들 때 관련 문서를 참조하도록:

```markdown
## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#phase-1-core-mvp)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#backend-implementation-details)
- [GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md)
```

### 프로젝트 README에 링크 추가

`README.md`에 다음을 추가:

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

## 📊 GitHub Project 보드 설정

### View 1: Backlog (우선순위 정렬)
```
Filter: status:Backlog
Sort by: Priority (Critical → High → Medium → Low)
Group by: Phase
```

### View 2: Sprint (현재 진행)
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

### View 4: Velocity (팀 성과)
```
Filter: status:Done AND closed_at:[last 4 weeks]
Group by: Week
Show: Total points completed per week
```

---

## ⚙️ GitHub Actions Integration

### 새 워크플로우 파일: `.github/workflows/project-sync.yml`

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

## 📈 모니터링 & 보고

### Weekly Report Template

**파일**: `.github/ISSUE_TEMPLATE/weekly-report.md`

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

## ✅ 체크리스트: Workflows 설정 완료

### GitHub Project Automation
- [ ] GitHub Project "Personalized Nutrition Platform Roadmap" 생성
- [ ] Workflows 탭에서 4개 자동화 규칙 설정
  - [ ] Auto-add to project
  - [ ] Auto-set status by label
  - [ ] Auto-assign milestone
  - [ ] Auto-update on PR merge

### Issue Templates
- [ ] `.github/ISSUE_TEMPLATE/epic.md` 생성
- [ ] `.github/ISSUE_TEMPLATE/story.md` 생성
- [ ] `.github/ISSUE_TEMPLATE/task.md` 생성
- [ ] `.github/ISSUE_TEMPLATE/bug.md` 생성

### GitHub Actions
- [ ] `.github/workflows/project-sync.yml` 설정
- [ ] Tests 실행 워크플로우 설정
- [ ] 배포 자동화 설정

### Documentation
- [ ] README.md에 프로젝트 링크 추가
- [ ] 각 이슈에 관련 문서 참조 추가
- [ ] GitHub Discussions 활성화
- [ ] Wiki 페이지 생성 (선택사항)

### Initial Issues
- [ ] Phase 1 Epic 생성 (5개)
- [ ] Phase 1 Stories 생성 (20-30개)
- [ ] Milestones 생성 (Q1-Q4 2026)
- [ ] Labels 정의 (20+ 라벨)

---

## 🎯 다음 단계 (우선순위)

### Immediate (오늘)
1. ✅ 문서 푸시 **완료**
2. GitHub Project 생성 (URL 접근: https://github.com/users/deokhwajeong/projects/2)
3. Workflows 자동화 규칙 5개 추가

### This Week
4. Issue Templates 5개 생성
5. Phase 1 이슈 50개 생성
6. `.github/workflows/project-sync.yml` 추가

### Next Week
7. 팀 온보딩 시작
8. 첫 스프린트 계획
9. Daily standup 시작

---

## 📚 참고 링크

### GitHub 공식 문서
- [GitHub Project Automation](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project)
- [GitHub Project API](https://docs.github.com/en/graphql/reference/objects#projectv2)
- [GitHub Actions Workflows](https://docs.github.com/en/actions/using-workflows)

### 프로젝트 문서
- [PROJECT_ROADMAP.md](../PROJECT_ROADMAP.md)
- [GITHUB_PROJECT_SETUP.md](../GITHUB_PROJECT_SETUP.md)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](../ADVANCED_IMPLEMENTATION_GUIDE.md)

### GitHub Project URL
- **Main Project**: https://github.com/users/deokhwajeong/projects/2
- **Repository**: https://github.com/deokhwajeong/BioAI-Nutrition

---

**생성일**: 2026-01-15  
**상태**: 📋 Implementation Ready  
**다음 업데이트**: 2026-01-22 (주간 review)

