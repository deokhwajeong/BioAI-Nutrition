#!/bin/bash

# GitHub Project Issues 자동 생성 스크립트
# 용도: PROJECT_ROADMAP.md 기반 Phase 1 이슈 자동 생성
# 사용법: ./scripts/create_phase1_issues.sh

set -e

REPO="deokhwajeong/BioAI-Nutrition"
PHASE="phase-1"
MILESTONE="Q1 2026"

# 컬러 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  GitHub Issues 자동 생성 - Phase 1 (Q1 2026)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

# gh CLI 확인
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ Error: GitHub CLI (gh) not found.${NC}"
    echo "Install: https://cli.github.com/"
    exit 1
fi

# gh 인증 확인
if ! gh auth status &> /dev/null; then
    echo -e "${RED}❌ Error: Not authenticated. Run: gh auth login${NC}"
    exit 1
fi

echo -e "${YELLOW}✓ GitHub CLI authenticated${NC}\n"

# ============================================================================
# EPIC 1: User Management & Authentication
# ============================================================================
echo -e "${YELLOW}📌 Creating Epic 1: User Management & Authentication...${NC}"

EPIC1=$(gh issue create -R $REPO \
  --title "Epic: User Management & Authentication" \
  --body "## 📖 Epic Overview
Complete user authentication and profile management system.

## 🎯 Goals
- Secure user registration & login
- API key management  
- Profile customization
- Password recovery & 2FA

## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#user-management--authentication)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#backend-implementation-details)
- [GITHUB_PROJECT_SETUP.md](GITHUB_PROJECT_SETUP.md)" \
  --label "epic,$PHASE,critical,backend" \
  --milestone "$MILESTONE" \
  --json number \
  --jq '.number')

echo -e "${GREEN}✓ Epic created: #${EPIC1}${NC}"

# ============================================================================
# EPIC 1 STORIES
# ============================================================================

# Story 1.1: User Registration
echo -e "${YELLOW}  📖 Story 1.1: User Registration...${NC}"
gh issue create -R $REPO \
  --title "Story: Implement user registration endpoint" \
  --body "## 👤 User Story
As a new user, I want to register with email and password, so I can access the platform.

## ✅ Acceptance Criteria
- [ ] POST /users endpoint accepts email, password, name
- [ ] Password hashed with bcrypt (min 12 rounds)
- [ ] Returns user_id and auth_token on success
- [ ] Duplicate email returns 409 Conflict
- [ ] Invalid input returns 422 validation error
- [ ] Email validation (RFC 5322 compliant)
- [ ] Password validation (min 8 chars, 1 uppercase, 1 number, 1 special)
- [ ] Unit tests cover happy path and error cases

## 🔗 Epic
#${EPIC1}

## 📚 Reference
[ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#backend-implementation-details)" \
  --label "story,$PHASE,backend,critical" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 1.1 created${NC}"

# Story 1.2: API Key Authentication
echo -e "${YELLOW}  📖 Story 1.2: API Key Authentication...${NC}"
gh issue create -R $REPO \
  --title "Story: Add API key authentication" \
  --body "## 👤 User Story
As a backend service, I want to validate API keys, so only authorized clients access the API.

## ✅ Acceptance Criteria
- [ ] X-API-Key header validation on protected endpoints
- [ ] Invalid keys return 401 Unauthorized
- [ ] Key validation logged with PII filtering
- [ ] Tests for valid/invalid key scenarios
- [ ] Rate limiting (max 10 failed attempts per hour)
- [ ] API key rotation endpoint
- [ ] API key expiration support (optional)

## 🔗 Epic
#${EPIC1}

## 📚 Reference
[ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#security-implementation)" \
  --label "story,$PHASE,backend,critical" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 1.2 created${NC}"

# Story 1.3: User Profile Management
echo -e "${YELLOW}  📖 Story 1.3: User Profile Management...${NC}"
gh issue create -R $REPO \
  --title "Story: Create user profile management API" \
  --body "## 👤 User Story
As a user, I want to manage my profile information, so I can keep my data updated.

## ✅ Acceptance Criteria
- [ ] GET /users/{user_id} returns user profile
- [ ] PUT /users/{user_id} updates profile fields
- [ ] Supported fields: name, email, phone, bio, preferences
- [ ] Users can only modify their own profile (authorization check)
- [ ] Changes logged for audit trail
- [ ] Returns 400 for invalid updates
- [ ] Unit & integration tests

## 🔗 Epic
#${EPIC1}" \
  --label "story,$PHASE,backend" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 1.3 created${NC}"

# ============================================================================
# EPIC 2: Meal Data Ingestion
# ============================================================================
echo -e "${YELLOW}📌 Creating Epic 2: Meal Data Ingestion...${NC}"

EPIC2=$(gh issue create -R $REPO \
  --title "Epic: Meal Data Ingestion" \
  --body "## 📖 Epic Overview
Complete meal data ingestion pipeline with nutrition parsing.

## 🎯 Goals
- Manual meal entry API
- Nutrition fact parsing
- Food database integration
- Event classification (diet, activity, sleep)

## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#meal-data-ingestion)
- [DATABASE_SETUP.md](DATABASE_SETUP.md)" \
  --label "epic,$PHASE,critical,backend" \
  --milestone "$MILESTONE" \
  --json number \
  --jq '.number')

echo -e "${GREEN}✓ Epic created: #${EPIC2}${NC}"

# Story 2.1: Meal Event Ingestion
echo -e "${YELLOW}  📖 Story 2.1: Meal Event Ingestion...${NC}"
gh issue create -R $REPO \
  --title "Story: Build meal event ingestion endpoint" \
  --body "## 👤 User Story
As a user, I want to log meals with nutrition facts, so I can track my diet.

## ✅ Acceptance Criteria
- [ ] POST /events endpoint accepts meal data
- [ ] Validates required fields: food_name, calories, timestamp
- [ ] Calculates macros if provided: protein_g, carbs_g, fat_g
- [ ] Stores in database with user_id reference
- [ ] Returns event_id and computed metrics
- [ ] Pagination support for GET /events
- [ ] 80%+ test coverage

## 🔗 Epic
#${EPIC2}" \
  --label "story,$PHASE,backend,critical" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 2.1 created${NC}"

# Story 2.2: Nutrition Fact Parsing
echo -e "${YELLOW}  📖 Story 2.2: Nutrition Fact Parsing...${NC}"
gh issue create -R $REPO \
  --title "Story: Add nutrition fact parsing from food items" \
  --body "## 👤 User Story
As a nutrition app, I want to extract macros from meal descriptions, so I calculate totals accurately.

## ✅ Acceptance Criteria
- [ ] Extract food items from meal description (NLP)
- [ ] Look up nutrition from food database (FDA FoodData Central)
- [ ] Aggregate macros/micros for complete meal
- [ ] Handle food aliases and partial matches
- [ ] Flag missing or low-confidence items
- [ ] Unit tests for 50+ common foods

## 🔗 Epic
#${EPIC2}" \
  --label "story,$PHASE,backend,ml" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 2.2 created${NC}"

# ============================================================================
# EPIC 3: Food Image Analysis
# ============================================================================
echo -e "${YELLOW}📌 Creating Epic 3: Food Image Analysis...${NC}"

EPIC3=$(gh issue create -R $REPO \
  --title "Epic: Food Image Analysis MVP" \
  --body "## 📖 Epic Overview
YOLOv8-based meal detection from photos with serving size estimation.

## 🎯 Goals
- Meal detection from images
- Serving size estimation
- Nutrition fact lookup
- User feedback loop

## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#food-image-analysis-mvp)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#ml-pipeline-architecture)" \
  --label "epic,$PHASE,high,ml" \
  --milestone "$MILESTONE" \
  --json number \
  --jq '.number')

echo -e "${GREEN}✓ Epic created: #${EPIC3}${NC}"

# Story 3.1: YOLOv8 Inference
echo -e "${YELLOW}  📖 Story 3.1: YOLOv8 Inference Service...${NC}"
gh issue create -R $REPO \
  --title "Story: Implement YOLOv8 meal detection inference" \
  --body "## 👤 User Story
As a computer vision system, I want to detect meals in photos, so I can analyze food automatically.

## ✅ Acceptance Criteria
- [ ] Load YOLOv8 pretrained model
- [ ] Run inference on uploaded image
- [ ] Detect multiple food items in single image
- [ ] Confidence score filtering (>0.5)
- [ ] Bounding box output
- [ ] Async processing with task queue
- [ ] Timeout handling (max 30s)

## 🔗 Epic
#${EPIC3}" \
  --label "story,$PHASE,ml,high" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 3.1 created${NC}"

# ============================================================================
# EPIC 4: Rule-Based Recommendations
# ============================================================================
echo -e "${YELLOW}📌 Creating Epic 4: Rule-Based Recommendations...${NC}"

EPIC4=$(gh issue create -R $REPO \
  --title "Epic: Rule-Based Recommendations" \
  --body "## 📖 Epic Overview
YAML-based recommendation engine with privacy-safe logic.

## 🎯 Goals
- Load YAML recommendation rules
- Evaluate conditions against user features
- Score recommendations by confidence
- Generate explanation rationale

## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#rule-based-recommendations)
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md#recommendations-engine)" \
  --label "epic,$PHASE,critical,backend" \
  --milestone "$MILESTONE" \
  --json number \
  --jq '.number')

echo -e "${GREEN}✓ Epic created: #${EPIC4}${NC}"

# Story 4.1: Rule Engine Implementation
echo -e "${YELLOW}  📖 Story 4.1: Rule-Based Recommendation Engine...${NC}"
gh issue create -R $REPO \
  --title "Story: Implement YAML rule-based recommendation engine" \
  --body "## 👤 User Story
As a recommendation system, I want to evaluate YAML rules, so I generate personalized recommendations.

## ✅ Acceptance Criteria
- [ ] Load rules from rules/*.yaml directory
- [ ] Parse YAML with 'when' (conditions) and 'then' (actions)
- [ ] Evaluate conditions against user features (7-day rolling averages)
- [ ] Return top-K recommendations (default 5)
- [ ] Include confidence scores (0.0-1.0)
- [ ] Include guardrails (e.g., vegan-aware)
- [ ] Unit tests for 10+ rules

## Example Rule
\`\`\`yaml
id: fiber_boost_simple
when:
  daily_features.fiber_g: \"< user_targets.fiber_g * 0.8\"
then:
  message: \"Increase fiber by adding an apple and almonds\"
  rationale: \"Your 7-day average fiber is below target\"
  guardrails: [\"vegan-aware\", \"non-diagnostic\"]
  confidence: 0.85
\`\`\`

## 🔗 Epic
#${EPIC4}" \
  --label "story,$PHASE,backend,critical" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 4.1 created${NC}"

# ============================================================================
# EPIC 5: User Dashboard
# ============================================================================
echo -e "${YELLOW}📌 Creating Epic 5: User Dashboard...${NC}"

EPIC5=$(gh issue create -R $REPO \
  --title "Epic: User Dashboard" \
  --body "## 📖 Epic Overview
Frontend dashboard for nutrition tracking and recommendations.

## 🎯 Goals
- Daily nutrition summary
- Trend visualization
- Recommendation feed
- Goal progress tracking

## 📚 Related Documentation
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md#user-dashboard)" \
  --label "epic,$PHASE,high,frontend" \
  --milestone "$MILESTONE" \
  --json number \
  --jq '.number')

echo -e "${GREEN}✓ Epic created: #${EPIC5}${NC}"

# Story 5.1: Dashboard Prototype
echo -e "${YELLOW}  📖 Story 5.1: Dashboard UI Prototype...${NC}"
gh issue create -R $REPO \
  --title "Story: Build nutrition dashboard UI" \
  --body "## 👤 User Story
As a user, I want to see my daily nutrition summary, so I can track my progress.

## ✅ Acceptance Criteria
- [ ] Display daily macros (protein, carbs, fat, fiber)
- [ ] Show progress toward targets (% complete)
- [ ] Display calories consumed vs target
- [ ] Nutrition breakdown chart (Recharts)
- [ ] Responsive design (mobile-first)
- [ ] Performance: <2s load time

## 🔗 Epic
#${EPIC5}" \
  --label "story,$PHASE,frontend,high" \
  --milestone "$MILESTONE" > /dev/null

echo -e "${GREEN}✓ Story 5.1 created${NC}"

# ============================================================================
# Summary
# ============================================================================
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Phase 1 Issues Created Successfully!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}Summary:${NC}"
echo "  📌 Epics: 5 (User Auth, Meal Ingestion, Image Analysis, Recommendations, Dashboard)"
echo "  📖 Stories: 10 (2 per epic)"
echo "  🏷️ Labels: phase-1, epic, story, critical, backend, frontend, ml"
echo "  📅 Milestone: Q1 2026"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. View project: https://github.com/users/deokhwajeong/projects/2"
echo "  2. Configure workflows in project settings"
echo "  3. Assign team members to issues"
echo "  4. Start Sprint 1 planning"
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"

