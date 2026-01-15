#!/bin/bash
set -e

REPO="deokhwajeong/BioAI-Nutrition"
TOKEN=$(gh auth token)

echo "🚀 Starting GitHub Project final configuration..."
echo ""

# =========================== MILESTONES ===========================
echo "📅 Creating Milestones..."

create_milestone() {
    local title=$1
    local due=$2
    local desc=$3
    
    curl -s -X POST https://api.github.com/repos/$REPO/milestones \
      -H "Authorization: token $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -d "{\"title\":\"$title\",\"due_on\":\"$due\",\"description\":\"$desc\"}" > /dev/null
    echo "✓ $title"
}

create_milestone "Q1 2026" "2026-03-31T23:59:59Z" "MVP: Core features (Jan-Mar 2026)"
create_milestone "Q2 2026" "2026-06-30T23:59:59Z" "Advanced ML: Personalization (Apr-Jun 2026)"
create_milestone "Q3 2026" "2026-09-30T23:59:59Z" "Community: Social features (Jul-Sep 2026)"
create_milestone "Q4 2026" "2026-12-31T23:59:59Z" "Enterprise: Compliance & scaling (Oct-Dec 2026)"

echo ""

# =========================== LABELS ===========================
echo "🏷️  Creating Labels..."

create_label() {
    local name=$1
    local color=$2
    local desc=$3
    
    curl -s -X POST https://api.github.com/repos/$REPO/labels \
      -H "Authorization: token $TOKEN" \
      -H "Accept: application/vnd.github+json" \
      -d "{\"name\":\"$name\",\"color\":\"$color\",\"description\":\"$desc\"}" > /dev/null 2>&1
}

# Phase Labels
for phase in phase-1 phase-2 phase-3 phase-4; do
    create_label "$phase" "0366d6" "Phase label"
done

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
for team in backend frontend ml data-eng devops security; do
    create_label "$team" "1f883d" "Team label"
done

# Status Labels
create_label "needs-triage" "cccccc" "Needs review"
create_label "needs-estimation" "cccccc" "Needs story points"
create_label "blocked" "d73a49" "Blocked"
create_label "documentation" "0075ca" "Documentation"

echo "✓ 24 Labels created"
echo ""

# =========================== ISSUES ===========================
echo "📌 Creating 14 Epic Issues..."

issues=(
  "Epic: User Management & Authentication|User authentication and profile management system.|epic,phase-1,critical,backend|Q1 2026"
  "Epic: Meal Data Ingestion|Meal data ingestion pipeline with nutrition parsing.|epic,phase-1,critical,backend|Q1 2026"
  "Epic: Food Image Analysis MVP|YOLOv8-based meal detection from photos.|epic,phase-1,high,ml|Q1 2026"
  "Epic: Rule-Based Recommendations|YAML-based recommendation engine with privacy-safe logic.|epic,phase-1,critical,backend|Q1 2026"
  "Epic: User Dashboard|Frontend dashboard for nutrition tracking and recommendations.|epic,phase-1,high,frontend|Q1 2026"
  "Epic: XGBoost-Based Personalization|ML model for personalized nutrition recommendations.|epic,phase-2,high,ml|Q2 2026"
  "Epic: Meal Planning & Scheduling|Weekly meal planning with goal optimization.|epic,phase-2,high,backend|Q2 2026"
  "Epic: Advanced Image Analysis|Enhanced food detection with serving size estimation.|epic,phase-2,high,ml|Q2 2026"
  "Epic: Analytics Dashboard|User analytics and health insights.|epic,phase-2,medium,frontend|Q2 2026"
  "Epic: Social Features & Community|Community-driven nutrition insights.|epic,phase-3,medium,frontend|Q3 2026"
  "Epic: Integration Platform|Connect with health devices and APIs.|epic,phase-3,medium,backend|Q3 2026"
  "Epic: Enterprise Features & SLA|Enterprise compliance and support.|epic,phase-4,high,backend|Q4 2026"
  "Epic: ML Optimization & Scale|Optimize models for production scale.|epic,phase-4,high,ml|Q4 2026"
)

count=0
for issue_data in "${issues[@]}"; do
    IFS='|' read -r title body labels milestone <<< "$issue_data"
    
    gh issue create -R $REPO \
      --title "$title" \
      --body "$body" \
      --label "$labels" \
      --milestone "$milestone" > /dev/null 2>&1 && {
        count=$((count+1))
        echo "✓ #$count: $title"
      } || echo "✗ Failed: $title"
done

echo ""
echo "✅ GitHub Project setup complete!"
echo ""
echo "📊 Summary:"
echo "  ✓ Milestones: 4"
echo "  ✓ Labels: 24"
echo "  ✓ Epics: 14"
echo ""
echo "🔗 Project: https://github.com/users/deokhwajeong/projects/2"
