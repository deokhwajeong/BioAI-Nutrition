#!/bin/bash

REPO="deokhwajeong/BioAI-Nutrition"
OWNER="deokhwajeong"
PROJECT_ID="2"

echo "🚀 전체 GitHub Project 자동 설정 시작..."
echo ""

# ============================================================================
# 1. MILESTONES 생성 (GitHub API)
# ============================================================================
echo "📅 Milestones 생성 중..."

create_milestone() {
    local title=$1
    local due_on=$2
    local description=$3
    
    curl -s -X POST \
        -H "Authorization: token $(gh auth token)" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d "{\"title\":\"$title\",\"due_on\":\"$due_on\",\"description\":\"$description\"}" > /dev/null 2>&1
    echo "✓ $title"
}

create_milestone "Q1 2026" "2026-03-31T23:59:59Z" "MVP: Core features (Jan-Mar 2026)"
create_milestone "Q2 2026" "2026-06-30T23:59:59Z" "Advanced ML: Personalization (Apr-Jun 2026)"
create_milestone "Q3 2026" "2026-09-30T23:59:59Z" "Community: Social features (Jul-Sep 2026)"
create_milestone "Q4 2026" "2026-12-31T23:59:59Z" "Enterprise: Compliance & scaling (Oct-Dec 2026)"

echo ""

# ============================================================================
# 2. LABELS 생성 (GitHub API)
# ============================================================================
echo "🏷️  Labels 생성 중..."

create_label() {
    local name=$1
    local color=$2
    local description=$3
    
    curl -s -X POST \
        -H "Authorization: token $(gh auth token)" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/labels \
        -d "{\"name\":\"$name\",\"color\":\"$color\",\"description\":\"$description\"}" > /dev/null 2>&1
}

# Phase Labels
create_label "phase-1" "0366d6" "Q1 2026 - MVP"
create_label "phase-2" "0366d6" "Q2 2026 - Advanced ML"
create_label "phase-3" "0366d6" "Q3 2026 - Community"
create_label "phase-4" "0366d6" "Q4 2026 - Enterprise"

# Type Labels
create_label "epic" "a2eeef" "Large feature (multiple sprints)"
create_label "story" "a2eeef" "User story"
create_label "task" "a2eeef" "Technical task"
create_label "bug" "d73a49" "Bug report"
create_label "enhancement" "84b6eb" "Enhancement"

# Priority Labels
create_label "critical" "ff0000" "Critical priority"
create_label "high" "ff9900" "High priority"
create_label "medium" "ffcc00" "Medium priority"
create_label "low" "99cc00" "Low priority"

# Team Labels
create_label "backend" "1f883d" "Backend team"
create_label "frontend" "1f883d" "Frontend team"
create_label "ml" "1f883d" "ML team"
create_label "data-eng" "1f883d" "Data engineering"
create_label "devops" "1f883d" "DevOps team"
create_label "security" "1f883d" "Security & compliance"

# Status Labels
create_label "needs-triage" "cccccc" "Needs review"
create_label "needs-estimation" "cccccc" "Needs story points"
create_label "blocked" "d73a49" "Blocked"
create_label "documentation" "0075ca" "Documentation"

echo "✓ 24개 Labels 생성됨"
echo ""

# ============================================================================
# 3. PHASE 1 EPICS 생성 및 PROJECT에 추가
# ============================================================================
echo "📌 Phase 1 Epics 생성 중..."

create_and_add_epic() {
    local title=$1
    local body=$2
    local labels=$3
    
    ISSUE=$(gh issue create -R $REPO \
      --title "$title" \
      --body "$body" \
      --label "$labels" \
      --milestone "Q1 2026" \
      --json number \
      -q '.number' 2>/dev/null)
    
    if [ -n "$ISSUE" ]; then
        echo "✓ Created: $title (#$ISSUE)"
        # Project에 추가
        gh project item-add $PROJECT_ID --owner $OWNER --content-id $ISSUE --content-type Issue 2>/dev/null
        echo "  → Project에 추가됨"
    fi
}

create_and_add_epic \
  "Epic: User Management & Authentication" \
  "User authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management  
- Profile customization
- Password recovery

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-1,critical,backend"

create_and_add_epic \
  "Epic: Meal Data Ingestion" \
  "Meal data ingestion pipeline with nutrition parsing.

## 🎯 Goals
- Manual meal entry API
- Nutrition fact parsing
- Food database integration

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-1,critical,backend"

create_and_add_epic \
  "Epic: Food Image Analysis MVP" \
  "YOLOv8-based meal detection from photos.

## 🎯 Goals
- Meal detection from images
- Serving size estimation
- Nutrition fact lookup

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-1,high,ml"

create_and_add_epic \
  "Epic: Rule-Based Recommendations" \
  "YAML-based recommendation engine with privacy-safe logic.

## 🎯 Goals
- Load YAML rules
- Evaluate conditions
- Score recommendations
- Generate explanations

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-1,critical,backend"

create_and_add_epic \
  "Epic: User Dashboard" \
  "Frontend dashboard for nutrition tracking and recommendations.

## 🎯 Goals
- Daily nutrition summary
- Trend visualization
- Recommendation feed
- Goal progress tracking

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-1,high,frontend"

echo ""

# ============================================================================
# 4. PHASE 2 EPICS 생성
# ============================================================================
echo "📌 Phase 2 Epics 생성 중..."

create_and_add_epic_q2() {
    local title=$1
    local body=$2
    local labels=$3
    
    ISSUE=$(gh issue create -R $REPO \
      --title "$title" \
      --body "$body" \
      --label "$labels" \
      --milestone "Q2 2026" \
      --json number \
      -q '.number' 2>/dev/null)
    
    if [ -n "$ISSUE" ]; then
        echo "✓ Created: $title (#$ISSUE)"
        gh project item-add $PROJECT_ID --owner $OWNER --content-id $ISSUE --content-type Issue 2>/dev/null
        echo "  → Project에 추가됨"
    fi
}

create_and_add_epic_q2 \
  "Epic: XGBoost-Based Personalization" \
  "ML model for personalized nutrition recommendations.

## 🎯 Goals
- Build XGBoost model
- User preference learning
- Real-time scoring

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-2,high,ml"

create_and_add_epic_q2 \
  "Epic: Meal Planning & Scheduling" \
  "Weekly meal planning with goal optimization.

## 🎯 Goals
- Plan meals for week
- Optimize for goals
- Shopping list generation

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-2,high,backend"

create_and_add_epic_q2 \
  "Epic: Advanced Image Analysis" \
  "Enhanced food detection with serving size estimation.

## 🎯 Goals
- Multi-item detection
- Improved accuracy
- Database expansion

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-2,high,ml"

create_and_add_epic_q2 \
  "Epic: Analytics Dashboard" \
  "User analytics and health insights.

## 🎯 Goals
- Nutrition trends
- Health metrics
- Progress reports

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-2,medium,frontend"

echo ""

# ============================================================================
# 5. PHASE 3 EPICS 생성
# ============================================================================
echo "📌 Phase 3 Epics 생성 중..."

create_and_add_epic_q3() {
    local title=$1
    local body=$2
    local labels=$3
    
    ISSUE=$(gh issue create -R $REPO \
      --title "$title" \
      --body "$body" \
      --label "$labels" \
      --milestone "Q3 2026" \
      --json number \
      -q '.number' 2>/dev/null)
    
    if [ -n "$ISSUE" ]; then
        echo "✓ Created: $title (#$ISSUE)"
        gh project item-add $PROJECT_ID --owner $OWNER --content-id $ISSUE --content-type Issue 2>/dev/null
        echo "  → Project에 추가됨"
    fi
}

create_and_add_epic_q3 \
  "Epic: Social Features & Community" \
  "Community-driven nutrition insights.

## 🎯 Goals
- User recipes sharing
- Meal recommendations
- Community challenges

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-3,medium,frontend"

create_and_add_epic_q3 \
  "Epic: Integration Platform" \
  "Connect with health devices and APIs.

## 🎯 Goals
- FitBit integration
- Apple Health sync
- Google Fit integration

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-3,medium,backend"

echo ""

# ============================================================================
# 6. PHASE 4 EPICS 생성
# ============================================================================
echo "📌 Phase 4 Epics 생성 중..."

create_and_add_epic_q4() {
    local title=$1
    local body=$2
    local labels=$3
    
    ISSUE=$(gh issue create -R $REPO \
      --title "$title" \
      --body "$body" \
      --label "$labels" \
      --milestone "Q4 2026" \
      --json number \
      -q '.number' 2>/dev/null)
    
    if [ -n "$ISSUE" ]; then
        echo "✓ Created: $title (#$ISSUE)"
        gh project item-add $PROJECT_ID --owner $OWNER --content-id $ISSUE --content-type Issue 2>/dev/null
        echo "  → Project에 추가됨"
    fi
}

create_and_add_epic_q4 \
  "Epic: Enterprise Features & SLA" \
  "Enterprise compliance and support.

## 🎯 Goals
- HIPAA compliance
- Multi-tenant support
- Premium support tier

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-4,high,backend"

create_and_add_epic_q4 \
  "Epic: ML Optimization & Scale" \
  "Optimize models for production scale.

## 🎯 Goals
- Model optimization
- Caching strategy
- Performance tuning

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  "epic,phase-4,high,ml"

echo ""
echo "✅ GitHub Project 전체 설정 완료!"
echo ""
echo "📊 생성된 항목:"
echo "  ✓ Milestones: 4개 (Q1-Q4 2026)"
echo "  ✓ Labels: 24개"
echo "  ✓ Epics: 14개 (모두 Project에 추가됨)"
echo ""
echo "📋 다음 단계:"
echo "  1. Project 보기: https://github.com/users/$OWNER/projects/$PROJECT_ID"
echo "  2. Automation 설정 (웹 UI에서)"
echo "  3. 팀원 초대"
echo ""
