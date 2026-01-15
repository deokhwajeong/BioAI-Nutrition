#!/bin/bash
# GitHub Project Automation - Create Sprints and Backlog Items
# This script creates GitHub project structure with sprints and issues

set -e

OWNER="deokhwajeong"
REPO="BioAI-Nutrition"
GH_TOKEN="${GITHUB_TOKEN}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitHub Project Automation - Sprint Setup${NC}"
echo "==============================================="

# Create Sprint 1 milestone
echo -e "${YELLOW}Creating Sprint 1 milestone...${NC}"
gh milestone create \
  --repo "$OWNER/$REPO" \
  --title "Sprint 1: Jan 15 - Jan 29 (MVP Foundation)" \
  --description "User auth, meal ingestion, basic recommendations" \
  --due-date "2026-01-29" || echo "Sprint 1 milestone already exists"

# Create Sprint 2 milestone
echo -e "${YELLOW}Creating Sprint 2 milestone...${NC}"
gh milestone create \
  --repo "$OWNER/$REPO" \
  --title "Sprint 2: Jan 30 - Feb 12 (Food Recognition)" \
  --description "YOLOv8 integration, image analysis, recommendations UI" \
  --due-date "2026-02-12" || echo "Sprint 2 milestone already exists"

# Create Sprint 3 milestone
echo -e "${YELLOW}Creating Sprint 3 milestone...${NC}"
gh milestone create \
  --repo "$OWNER/$REPO" \
  --title "Sprint 3: Feb 13 - Feb 27 (Polish & Test)" \
  --description "E2E testing, performance optimization, documentation" \
  --due-date "2026-02-27" || echo "Sprint 3 milestone already exists"

# Create Sprint 4 milestone
echo -e "${YELLOW}Creating Sprint 4 milestone...${NC}"
gh milestone create \
  --repo "$OWNER/$REPO" \
  --title "Sprint 4: Feb 28 - Mar 13 (MVP Launch)" \
  --description "Production deployment, monitoring, launch preparation" \
  --due-date "2026-03-13" || echo "Sprint 4 milestone already exists"

# Create Epic labels
EPICS=(
  "epic/user-management"
  "epic/meal-ingestion"
  "epic/food-recognition"
  "epic/recommendations"
  "epic/privacy-security"
  "epic/frontend"
  "epic/infrastructure"
)

for epic in "${EPICS[@]}"; do
  echo -e "${YELLOW}Creating label: $epic${NC}"
  gh label create "$epic" \
    --repo "$OWNER/$REPO" \
    --color "FF6B6B" \
    --description "Epic tracking label" 2>/dev/null || echo "Label $epic already exists"
done

# Create priority labels
PRIORITIES=(
  "priority/critical:E50000"
  "priority/high:FF6B6B"
  "priority/medium:FFA500"
  "priority/low:90EE90"
)

for priority in "${PRIORITIES[@]}"; do
  IFS=':' read -r label color <<< "$priority"
  echo -e "${YELLOW}Creating label: $label${NC}"
  gh label create "$label" \
    --repo "$OWNER/$REPO" \
    --color "${color}" \
    --description "Priority label" 2>/dev/null || echo "Label $label already exists"
done

# Create status labels
STATUSES=(
  "status/todo:CCCCCC"
  "status/in-progress:1F6FEB"
  "status/in-review:0366D6"
  "status/done:27AE60"
)

for status in "${STATUSES[@]}"; do
  IFS=':' read -r label color <<< "$status"
  echo -e "${YELLOW}Creating label: $label${NC}"
  gh label create "$label" \
    --repo "$OWNER/$REPO" \
    --color "${color}" \
    --description "Status label" 2>/dev/null || echo "Label $status already exists"
done

# Create Sprint 1 issues
echo -e "${BLUE}Creating Sprint 1 issues...${NC}"

SPRINT1_ISSUES=(
  # Backend
  "BE-001: User registration endpoint|3|5|epic/user-management|priority/high"
  "BE-002: API key authentication middleware|3|3|epic/user-management|priority/high"
  "BE-003: User profile management API|3|5|epic/user-management|priority/high"
  "BE-004: Meal event ingestion endpoint|3|8|epic/meal-ingestion|priority/critical"
  "BE-005: Nutrition fact parsing service|3|8|epic/meal-ingestion|priority/high"
  "BE-006: Basic recommendation rules engine|3|13|epic/recommendations|priority/high"
  "BE-007: PII filtering service|3|5|epic/privacy-security|priority/critical"
  "BE-008: Database migrations setup|3|3|epic/infrastructure|priority/high"
  # Frontend
  "FE-001: Dashboard layout with TailwindCSS|3|8|epic/frontend|priority/high"
  "FE-002: Login and registration page|3|8|epic/frontend|priority/high"
  "FE-003: Daily metrics cards component|3|5|epic/frontend|priority/high"
  "FE-004: Meal logging form|3|8|epic/frontend|priority/high"
  "FE-005: API integration for meal data|3|5|epic/frontend|priority/high"
  # DevOps
  "OPS-001: GitHub Actions CI/CD pipeline|3|5|epic/infrastructure|priority/high"
  "OPS-002: Docker containerization|3|3|epic/infrastructure|priority/high"
  "OPS-003: Testing infrastructure setup|3|3|epic/infrastructure|priority/high"
)

for issue in "${SPRINT1_ISSUES[@]}"; do
  IFS='|' read -r title milestone points epic priority <<< "$issue"
  echo -e "${YELLOW}Creating issue: $title${NC}"
  
  gh issue create \
    --repo "$OWNER/$REPO" \
    --title "$title" \
    --milestone "Sprint 1: Jan 15 - Jan 29 (MVP Foundation)" \
    --label "$epic" \
    --label "$priority" \
    --label "status/todo" \
    --body "**Story Points**: $points

## Acceptance Criteria
- [ ] Feature implemented
- [ ] Unit tests written (>80% coverage)
- [ ] Code review approved
- [ ] Integrated with main branch
- [ ] Documented

## Related
- Part of Q1 MVP Sprint 1" 2>/dev/null || echo "Issue might already exist"
done

echo -e "${GREEN}✅ GitHub Project setup complete!${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo "1. View project: https://github.com/$OWNER/$REPO/projects"
echo "2. Assign team members to issues"
echo "3. Start Sprint 1 planning"
