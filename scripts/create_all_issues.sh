#!/bin/bash

REPO="deokhwajeong/BioAI-Nutrition"
OWNER="deokhwajeong"
PROJECT_ID="2"
TOKEN=$(gh auth token)

echo "🏷️  Creating Labels first..."

# Create labels using API
create_label_api() {
    local name=$1
    local color=$2
    local description=$3
    
    curl -s -X POST \
        -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        https://api.github.com/repos/$OWNER/$REPO/labels \
        -d "{\"name\":\"$name\",\"color\":\"$color\",\"description\":\"$description\"}" | jq -r '.name // .message' 2>/dev/null
}

# Phase Labels
echo -n "  phase-1: "
create_label_api "phase-1" "0366d6" "Q1 2026 - MVP"

echo -n "  phase-2: "
create_label_api "phase-2" "0366d6" "Q2 2026 - Advanced ML"

echo -n "  phase-3: "
create_label_api "phase-3" "0366d6" "Q3 2026 - Community"

echo -n "  phase-4: "
create_label_api "phase-4" "0366d6" "Q4 2026 - Enterprise"

# Type Labels
echo -n "  epic: "
create_label_api "epic" "a2eeef" "Large feature (multiple sprints)"

echo -n "  story: "
create_label_api "story" "a2eeef" "User story"

echo -n "  task: "
create_label_api "task" "a2eeef" "Technical task"

echo -n "  bug: "
create_label_api "bug" "d73a49" "Bug report"

echo -n "  enhancement: "
create_label_api "enhancement" "84b6eb" "Enhancement"

# Priority Labels
echo -n "  critical: "
create_label_api "critical" "ff0000" "Critical priority"

echo -n "  high: "
create_label_api "high" "ff9900" "High priority"

echo -n "  medium: "
create_label_api "medium" "ffcc00" "Medium priority"

echo -n "  low: "
create_label_api "low" "99cc00" "Low priority"

# Team Labels
echo -n "  backend: "
create_label_api "backend" "1f883d" "Backend team"

echo -n "  frontend: "
create_label_api "frontend" "1f883d" "Frontend team"

echo -n "  ml: "
create_label_api "ml" "1f883d" "ML team"

echo -n "  data-eng: "
create_label_api "data-eng" "1f883d" "Data engineering"

echo -n "  devops: "
create_label_api "devops" "1f883d" "DevOps team"

echo -n "  security: "
create_label_api "security" "1f883d" "Security & compliance"

# Status Labels
echo -n "  needs-triage: "
create_label_api "needs-triage" "cccccc" "Needs review"

echo -n "  needs-estimation: "
create_label_api "needs-estimation" "cccccc" "Needs story points"

echo -n "  blocked: "
create_label_api "blocked" "d73a49" "Blocked"

echo -n "  documentation: "
create_label_api "documentation" "0075ca" "Documentation"

echo ""
echo "✓ All labels created"
echo ""
echo "📌 Creating Issues..."

# Function to create issue and add to project
create_issue() {
    local title=$1
    local body=$2
    local labels=$3
    local milestone=$4
    
    # Create issue
    ISSUE_NUM=$(gh issue create -R $REPO \
        --title "$title" \
        --body "$body" \
        --label "$labels" \
        --milestone "$milestone" \
        --json number -q '.number' 2>/dev/null)
    
    if [ -n "$ISSUE_NUM" ]; then
        echo "✓ #$ISSUE_NUM: $title"
        
        # Add to project
        gh project item-add $PROJECT_ID --owner $OWNER --content-id $ISSUE_NUM --content-type Issue 2>/dev/null
    fi
}

# Phase 1
create_issue \
  "Epic: User Management & Authentication" \
  "User authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management  
- Profile customization
- Password recovery" \
  "epic,phase-1,critical,backend" \
  "Q1 2026"

create_issue \
  "Epic: Meal Data Ingestion" \
  "Meal data ingestion pipeline with nutrition parsing.

## 🎯 Goals
- Manual meal entry API
- Nutrition fact parsing
- Food database integration" \
  "epic,phase-1,critical,backend" \
  "Q1 2026"

create_issue \
  "Epic: Food Image Analysis MVP" \
  "YOLOv8-based meal detection from photos.

## 🎯 Goals
- Meal detection from images
- Serving size estimation
- Nutrition fact lookup" \
  "epic,phase-1,high,ml" \
  "Q1 2026"

create_issue \
  "Epic: Rule-Based Recommendations" \
  "YAML-based recommendation engine with privacy-safe logic.

## 🎯 Goals
- Load YAML rules
- Evaluate conditions
- Score recommendations
- Generate explanations" \
  "epic,phase-1,critical,backend" \
  "Q1 2026"

create_issue \
  "Epic: User Dashboard" \
  "Frontend dashboard for nutrition tracking and recommendations.

## 🎯 Goals
- Daily nutrition summary
- Trend visualization
- Recommendation feed
- Goal progress tracking" \
  "epic,phase-1,high,frontend" \
  "Q1 2026"

# Phase 2
create_issue \
  "Epic: XGBoost-Based Personalization" \
  "ML model for personalized nutrition recommendations.

## 🎯 Goals
- Build XGBoost model
- User preference learning
- Real-time scoring" \
  "epic,phase-2,high,ml" \
  "Q2 2026"

create_issue \
  "Epic: Meal Planning & Scheduling" \
  "Weekly meal planning with goal optimization.

## 🎯 Goals
- Plan meals for week
- Optimize for goals
- Shopping list generation" \
  "epic,phase-2,high,backend" \
  "Q2 2026"

create_issue \
  "Epic: Advanced Image Analysis" \
  "Enhanced food detection with serving size estimation.

## 🎯 Goals
- Multi-item detection
- Improved accuracy
- Database expansion" \
  "epic,phase-2,high,ml" \
  "Q2 2026"

create_issue \
  "Epic: Analytics Dashboard" \
  "User analytics and health insights.

## 🎯 Goals
- Nutrition trends
- Health metrics
- Progress reports" \
  "epic,phase-2,medium,frontend" \
  "Q2 2026"

# Phase 3
create_issue \
  "Epic: Social Features & Community" \
  "Community-driven nutrition insights.

## 🎯 Goals
- User recipes sharing
- Meal recommendations
- Community challenges" \
  "epic,phase-3,medium,frontend" \
  "Q3 2026"

create_issue \
  "Epic: Integration Platform" \
  "Connect with health devices and APIs.

## 🎯 Goals
- FitBit integration
- Apple Health sync
- Google Fit integration" \
  "epic,phase-3,medium,backend" \
  "Q3 2026"

# Phase 4
create_issue \
  "Epic: Enterprise Features & SLA" \
  "Enterprise compliance and support.

## 🎯 Goals
- HIPAA compliance
- Multi-tenant support
- Premium support tier" \
  "epic,phase-4,high,backend" \
  "Q4 2026"

create_issue \
  "Epic: ML Optimization & Scale" \
  "Optimize models for production scale.

## 🎯 Goals
- Model optimization
- Caching strategy
- Performance tuning" \
  "epic,phase-4,high,ml" \
  "Q4 2026"

echo ""
echo "✅ All issues created and added to project!"
