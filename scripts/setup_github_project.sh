#!/bin/bash

# GitHub Project 자동 설정 스크립트
# Milestones, Labels, Issues 생성

set -e

REPO="deokhwajeong/BioAI-Nutrition"

echo "🚀 GitHub Project 자동 설정 시작..."
echo ""

# ============================================================================
# 1. MILESTONES 생성
# ============================================================================
echo "📅 Milestones 생성 중..."

gh milestone create -R $REPO "Q1 2026" --description "MVP: Core features (Jan-Mar 2026)" --due-date 2026-03-31
echo "✓ Q1 2026 milestone created"

gh milestone create -R $REPO "Q2 2026" --description "Advanced ML: Personalization (Apr-Jun 2026)" --due-date 2026-06-30
echo "✓ Q2 2026 milestone created"

gh milestone create -R $REPO "Q3 2026" --description "Community: Social features (Jul-Sep 2026)" --due-date 2026-09-30
echo "✓ Q3 2026 milestone created"

gh milestone create -R $REPO "Q4 2026" --description "Enterprise: Compliance & scaling (Oct-Dec 2026)" --due-date 2026-12-31
echo "✓ Q4 2026 milestone created"

echo ""

# ============================================================================
# 2. LABELS 생성
# ============================================================================
echo "🏷️  Labels 생성 중..."

# Phase Labels
gh label create -R $REPO "phase-1" --color "0366d6" --description "Q1 2026 - MVP" || true
gh label create -R $REPO "phase-2" --color "0366d6" --description "Q2 2026 - Advanced ML" || true
gh label create -R $REPO "phase-3" --color "0366d6" --description "Q3 2026 - Community" || true
gh label create -R $REPO "phase-4" --color "0366d6" --description "Q4 2026 - Enterprise" || true

# Type Labels
gh label create -R $REPO "epic" --color "a2eeef" --description "Large feature (multiple sprints)" || true
gh label create -R $REPO "story" --color "a2eeef" --description "User story" || true
gh label create -R $REPO "task" --color "a2eeef" --description "Technical task" || true
gh label create -R $REPO "bug" --color "d73a49" --description "Bug report" || true
gh label create -R $REPO "enhancement" --color "84b6eb" --description "Enhancement" || true

# Priority Labels
gh label create -R $REPO "critical" --color "ff0000" --description "Critical priority" || true
gh label create -R $REPO "high" --color "ff9900" --description "High priority" || true
gh label create -R $REPO "medium" --color "ffcc00" --description "Medium priority" || true
gh label create -R $REPO "low" --color "99cc00" --description "Low priority" || true

# Team Labels
gh label create -R $REPO "backend" --color "1f883d" --description "Backend team" || true
gh label create -R $REPO "frontend" --color "1f883d" --description "Frontend team" || true
gh label create -R $REPO "ml" --color "1f883d" --description "ML team" || true
gh label create -R $REPO "data-eng" --color "1f883d" --description "Data engineering" || true
gh label create -R $REPO "devops" --color "1f883d" --description "DevOps team" || true
gh label create -R $REPO "security" --color "1f883d" --description "Security & compliance" || true

# Status Labels
gh label create -R $REPO "needs-triage" --color "cccccc" --description "Needs review" || true
gh label create -R $REPO "needs-estimation" --color "cccccc" --description "Needs story points" || true
gh label create -R $REPO "blocked" --color "d73a49" --description "Blocked" || true
gh label create -R $REPO "documentation" --color "0075ca" --description "Documentation" || true

echo "✓ All labels created"
echo ""

# ============================================================================
# 3. PHASE 1 EPICS 생성
# ============================================================================
echo "📌 Phase 1 Epics 생성 중..."

gh issue create -R $REPO \
  --title "Epic: User Management & Authentication" \
  --body "User authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management  
- Profile customization
- Password recovery

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  --label "epic,phase-1,critical,backend" \
  --milestone "Q1 2026" > /dev/null
echo "✓ Epic 1: User Management"

gh issue create -R $REPO \
  --title "Epic: Meal Data Ingestion" \
  --body "Meal data ingestion pipeline with nutrition parsing.

## 🎯 Goals
- Manual meal entry API
- Nutrition fact parsing
- Food database integration

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  --label "epic,phase-1,critical,backend" \
  --milestone "Q1 2026" > /dev/null
echo "✓ Epic 2: Meal Data Ingestion"

gh issue create -R $REPO \
  --title "Epic: Food Image Analysis MVP" \
  --body "YOLOv8-based meal detection from photos.

## 🎯 Goals
- Meal detection from images
- Serving size estimation
- Nutrition fact lookup

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  --label "epic,phase-1,high,ml" \
  --milestone "Q1 2026" > /dev/null
echo "✓ Epic 3: Food Image Analysis"

gh issue create -R $REPO \
  --title "Epic: Rule-Based Recommendations" \
  --body "YAML-based recommendation engine with privacy-safe logic.

## 🎯 Goals
- Load YAML rules
- Evaluate conditions
- Score recommendations
- Generate explanations

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  --label "epic,phase-1,critical,backend" \
  --milestone "Q1 2026" > /dev/null
echo "✓ Epic 4: Rule-Based Recommendations"

gh issue create -R $REPO \
  --title "Epic: User Dashboard" \
  --body "Frontend dashboard for nutrition tracking and recommendations.

## 🎯 Goals
- Daily nutrition summary
- Trend visualization
- Recommendation feed
- Goal progress tracking

## 📚 Reference
See [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md) for details" \
  --label "epic,phase-1,high,frontend" \
  --milestone "Q1 2026" > /dev/null
echo "✓ Epic 5: User Dashboard"

echo ""
echo "✅ GitHub Project 설정 완료!"
echo ""
echo "📊 다음 단계:"
echo "  1. GitHub Project 열기: https://github.com/users/deokhwajeong/projects/2"
echo "  2. Automation → Workflows에서 4가지 규칙 추가 (웹 UI)"
echo "  3. 팀원 초대"
echo "  4. Sprint 계획"
echo ""
