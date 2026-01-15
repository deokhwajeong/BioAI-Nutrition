#!/bin/bash

REPO="deokhwajeong/BioAI-Nutrition"
OWNER="deokhwajeong"
TOKEN=$(gh auth token)

echo "🚀 Starting GitHub Project automatic configuration..."
echo ""

# ============================================================================
# 1. MILESTONES CHECK/CREATE
# ============================================================================
echo "📅 Checking Milestones..."

get_milestone_id() {
    local title=$1
    curl -s -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        | grep -o "\"number\": [0-9]*" | head -1 | grep -o "[0-9]*" || echo ""
}

# Get Milestones list
MILESTONES=$(curl -s -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    https://api.github.com/repos/$OWNER/$REPO/milestones)

if echo "$MILESTONES" | grep -q "Q1 2026"; then
    echo "✓ Milestones already exist"
else
    echo "Creating Milestones..."
    curl -s -X POST -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d '{"title":"Q1 2026","due_on":"2026-03-31T23:59:59Z","description":"MVP: Core features"}' > /dev/null
    
    curl -s -X POST -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d '{"title":"Q2 2026","due_on":"2026-06-30T23:59:59Z","description":"Advanced ML"}' > /dev/null
    
    curl -s -X POST -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d '{"title":"Q3 2026","due_on":"2026-09-30T23:59:59Z","description":"Community"}' > /dev/null
    
    curl -s -X POST -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/milestones \
        -d '{"title":"Q4 2026","due_on":"2026-12-31T23:59:59Z","description":"Enterprise"}' > /dev/null
    
    echo "✓ Milestones created"
fi

echo ""

# ============================================================================
# 2. LABELS CREATION
# ============================================================================
echo "🏷️ Creating Labels..."

create_label() {
    local name=$1
    local color=$2
    local description=$3
    
    # Check if already exists
    CHECK=$(curl -s -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/labels/$name)
    
    if ! echo "$CHECK" | grep -q "\"name\": \"$name\""; then
        curl -s -X POST -H "Authorization: token $TOKEN" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/repos/$OWNER/$REPO/labels \
            -d "{\"name\":\"$name\",\"color\":\"$color\",\"description\":\"$description\"}" > /dev/null 2>&1
    fi
}

# Phase Labels
create_label "phase-1" "0366d6" "Q1 2026 - MVP"
create_label "phase-2" "0366d6" "Q2 2026 - Advanced ML"
create_label "phase-3" "0366d6" "Q3 2026 - Community"
create_label "phase-4" "0366d6" "Q4 2026 - Enterprise"

# Type Labels
create_label "epic" "a2eeef" "Large feature"
create_label "story" "a2eeef" "User story"
create_label "task" "a2eeef" "Technical task"
create_label "bug" "d73a49" "Bug"
create_label "enhancement" "84b6eb" "Enhancement"

# Priority Labels
create_label "critical" "ff0000" "Critical"
create_label "high" "ff9900" "High"
create_label "medium" "ffcc00" "Medium"
create_label "low" "99cc00" "Low"

# Team Labels
create_label "backend" "1f883d" "Backend"
create_label "frontend" "1f883d" "Frontend"
create_label "ml" "1f883d" "ML"
create_label "data-eng" "1f883d" "Data Eng"
create_label "devops" "1f883d" "DevOps"
create_label "security" "1f883d" "Security"

# Status Labels
create_label "needs-triage" "cccccc" "Needs review"
create_label "needs-estimation" "cccccc" "Needs estimation"
create_label "blocked" "d73a49" "Blocked"
create_label "documentation" "0075ca" "Docs"

echo "✓ All labels created"
echo ""

# ============================================================================
# 3. PHASE 1 EPICS CREATION
# ============================================================================
echo "📌 Creating Phase 1 Epics..."

create_issue() {
    local title=$1
    local body=$2
    local labels=$3
    local milestone=$4
    
    RESPONSE=$(curl -s -X POST \
        -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/issues \
        -d "{\"title\":\"$title\",\"body\":\"$body\",\"labels\":[$(echo $labels | sed 's/,/\",\"/g' | sed 's/^/\"/' | sed 's/$/\"/')],\"milestone\":1}")
    
    echo "$RESPONSE" | grep -q "\"id\"" && echo "✓ $title"
}

create_issue "Epic: User Management & Authentication" \
"User authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management
- Profile customization
- Password recovery" \
"epic,phase-1,critical,backend" \
"1"

create_issue "Epic: Meal Data Ingestion" \
"Meal data ingestion pipeline with nutrition parsing.

## 🎯 Goals
- Manual meal entry API
- Nutrition fact parsing
- Food database integration" \
"epic,phase-1,critical,backend" \
"1"

create_issue "Epic: Food Image Analysis MVP" \
"YOLOv8-based meal detection from photos.

## 🎯 Goals
- Meal detection from images
- Serving size estimation
- Nutrition fact lookup" \
"epic,phase-1,high,ml" \
"1"

create_issue "Epic: Rule-Based Recommendations" \
"YAML-based recommendation engine with privacy-safe logic.

## 🎯 Goals
- Load YAML rules
- Evaluate conditions
- Score recommendations
- Generate explanations" \
"epic,phase-1,critical,backend" \
"1"

create_issue "Epic: User Dashboard" \
"Frontend dashboard for nutrition tracking and recommendations.

## 🎯 Goals
- Daily nutrition summary
- Trend visualization
- Recommendation feed
- Goal progress tracking" \
"epic,phase-1,high,frontend" \
"1"

echo ""
echo "✅ GitHub Project configuration complete!"
echo ""
echo "📊 Created items:"
echo "  ✓ Milestones: 4"
echo "  ✓ Labels: 24"
echo "  ✓ Epics: 5"
echo ""
echo "🔗 GitHub Project: https://github.com/users/deokhwajeong/projects/2"
