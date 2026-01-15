#!/bin/bash

# Project configuration using GitHub API
# Milestones, Labels, Issues creation

REPO="deokhwajeong/BioAI-Nutrition"
OWNER="deokhwajeong"

echo "🚀 Starting GitHub Project automatic configuration..."
echo ""

# ============================================================================
# 1. MILESTONES CREATION (GitHub API)
# ============================================================================
echo "📅 Creating Milestones..."

create_milestone() {
    local title=$1
    local due_on=$2
    local description=$3
    
    curl -s -X POST \
        -H "Authorization: token $(gh auth token)" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d "{\"title\":\"$title\",\"due_on\":\"$due_on\",\"description\":\"$description\"}" > /dev/null
    echo "✓ $title created"
}

create_milestone "Q1 2026" "2026-03-31T23:59:59Z" "MVP: Core features (Jan-Mar 2026)"
create_milestone "Q2 2026" "2026-06-30T23:59:59Z" "Advanced ML: Personalization (Apr-Jun 2026)"
create_milestone "Q3 2026" "2026-09-30T23:59:59Z" "Community: Social features (Jul-Sep 2026)"
create_milestone "Q4 2026" "2026-12-31T23:59:59Z" "Enterprise: Compliance & scaling (Oct-Dec 2026)"

echo ""

# ============================================================================
# 2. LABELS CREATION (GitHub API)
# ============================================================================
echo "🏷️  Creating Labels..."

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

echo "✓ All labels created"
echo ""

# ============================================================================
# 3. PHASE 1 EPICS CREATION (gh issue)
# ============================================================================
echo "📌 Creating Phase 1 Epics..."

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
  --milestone "Q1 2026" > /dev/null 2>&1
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
  --milestone "Q1 2026" > /dev/null 2>&1
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
  --milestone "Q1 2026" > /dev/null 2>&1
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
  --milestone "Q1 2026" > /dev/null 2>&1
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
  --milestone "Q1 2026" > /dev/null 2>&1
echo "✓ Epic 5: User Dashboard"

echo ""
echo "✅ GitHub Project configuration complete!"
echo ""
echo "📊 Created items:"
echo "  ✓ Milestones: 4 (Q1-Q4 2026)"
echo "  ✓ Labels: 24 (Phase, Type, Priority, Team, Status)"
echo "  ✓ Epics: 5 (Phase 1)"
echo ""
echo "📋 Next steps:"
echo "  1. GitHub Project: https://github.com/users/deokhwajeong/projects/2"
echo "  2. Automation → Workflows configuration (from web UI)"
echo "  3. Invite team memberse team members"
echo ""
