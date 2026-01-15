# 👥 Team Collaboration & Project Management Guide

**Last Updated**: 2026-01-15  
**Audience**: All team members  
**Purpose**: Streamline communication, reduce friction, enable self-organization

---

## 📅 Weekly Schedule

### Every Day
- **10:00 AM**: Daily Standup (15 min)
  - What did you accomplish yesterday?
  - What are you working on today?
  - Any blockers?

### Every Monday
- **2:00 PM**: Sprint Planning & Refinement (1.5 hours)
  - Review backlog
  - Estimate new stories
  - Finalize Sprint n+1 goals

### Every Wednesday
- **3:00 PM**: Technical Design Review (1 hour)
  - Code architecture questions
  - Design pattern discussions
  - Refactoring opportunities

### Every Friday
- **4:00 PM**: Sprint Review & Retrospective (1.5 hours)
  - Demo completed work
  - Review metrics & velocity
  - Team retrospective
  - Plan next iteration

---

## 🎯 Sprint Ceremony Details

### Sprint Planning (Monday 2:00 PM)

**Duration**: 1.5 hours (30 min per week of sprint)  
**Attendees**: Entire team  
**Facilitator**: Product Manager  
**Goal**: Confirm Sprint n work and prepare for Sprint n+1

#### Agenda
1. **Review Metrics** (5 min)
   - Last sprint velocity
   - Burndown chart
   - Team capacity

2. **Product Demo** (10 min)
   - PMs share new requirements
   - Discuss priorities
   - Answer clarifying questions

3. **Backlog Refinement** (20 min)
   - Review top 20 backlog items
   - Break down large stories
   - Estimate story points
   - Discuss dependencies

4. **Sprint Commitment** (40 min)
   - Team self-organizes into tasks
   - Discuss realistic capacity
   - Confirm committed stories
   - Assign owners to critical path items

5. **Setup & Prep** (5 min)
   - Create GitHub issues
   - Set milestone
   - Add labels

#### Checklist
- [ ] Backlog groomed (top 20 items estimated)
- [ ] Capacity calculated (consider PTO, meetings)
- [ ] Sprint goal defined
- [ ] Stories have acceptance criteria
- [ ] Stories < 13 points (split if larger)
- [ ] Dependencies identified
- [ ] High-risk items flagged

---

### Daily Standup (10:00 AM every day)

**Duration**: 15 minutes  
**Format**: Synchronous (Zoom/Teams)  
**Structure**: Each person gets 2 minutes max

#### Speaking Order
1. Product Manager (context)
2. Backend engineers
3. Frontend engineers
4. DevOps/ML engineer

#### Required Info
```
✓ Yesterday:
  - "Completed X task (5 points)"
  
✓ Today:
  - "Working on Y task (8 points)"
  
✓ Blockers:
  - "Need decision on API schema"
  - "Waiting for code review"
```

#### Action Items
- Block blockers immediately
- Record decisions in Slack thread
- Schedule separate sync if discussion needed

---

### Sprint Review (Friday 4:00 PM)

**Duration**: 1 hour  
**Attendees**: Team + stakeholders  
**Facilitator**: Product Manager  
**Goal**: Demo completed work & gather feedback

#### Agenda
1. **Completed Stories Demo** (35 min)
   - Each engineer demos their work
   - Show working software
   - Discuss trade-offs
   - Gather feedback

2. **Metrics Review** (10 min)
   - Sprint velocity achieved
   - Stories completed vs. committed
   - Burndown trends
   - Team health metrics

3. **Q&A & Feedback** (15 min)
   - Stakeholders ask questions
   - Suggest improvements
   - Discuss next priorities

#### Demo Checklist
- [ ] Feature works in staging/main
- [ ] Tests passing (>80% coverage)
- [ ] Code reviewed & merged
- [ ] Documentation updated
- [ ] Performance acceptable
- [ ] No known bugs

---

### Retrospective (Friday 4:00 PM - after Review)

**Duration**: 30 minutes  
**Attendees**: Team only (no external stakeholders)  
**Facilitator**: Rotating team member  
**Goal**: Continuous improvement

#### Structure (3-column format)
```
Went Well          | Should Improve    | Action Items
─────────────────────────────────────────────────
✓ Pair programming | ✗ Code reviews    - Limit reviews to 1 hour
✓ Clear acceptance | ✗ Deployment bugs - Add E2E tests
  criteria         | ✗ Unclear specs   - Refine earlier
```

#### Questions to Ask
1. What went well this sprint?
2. What could we improve?
3. What will we commit to next sprint?
4. What blockers are preventing us from being 10x better?

#### Outcome
- 3-5 action items for next sprint
- Share improvements with extended team
- Track progress on action items

---

## 🔀 Code Review Process

### Pull Request Workflow

```
1. Developer creates feature branch
   └─ git checkout -b feature/meal-logging

2. Developer opens Draft PR
   ├─ Title: "feat: Add meal logging endpoint"
   ├─ Description: Link to GitHub issue
   └─ Add: Acceptance criteria checklist

3. Continuous Integration (automated)
   ├─ Tests run
   ├─ Linting checks
   ├─ Code coverage report
   └─ Deploy to staging

4. Code Review (2 reviewers required)
   ├─ Architecture review
   ├─ Security check
   ├─ Test coverage
   └─ Documentation

5. Approval & Merge
   ├─ Squash & merge to main
   └─ Delete feature branch
```

### PR Description Template

```markdown
## Description
Fixes issue #123 - Add meal logging endpoint for users to log daily meals

## Related Issue
Closes #123

## Changes
- POST /events/meal_logged endpoint
- Nutrition fact parsing service
- Integration tests

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [x] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality)
- [ ] Documentation update

## Testing
- [x] Unit tests added/updated (95% coverage)
- [x] Integration tests added
- [x] Manual testing completed
  - Tested with valid meal data
  - Tested with edge cases (empty foods list)
  - Tested error handling

## Checklist
- [x] Code follows project style guidelines
- [x] Self-review completed
- [x] Comments added for complex logic
- [x] Documentation updated
- [x] Tests added/updated
- [x] All tests passing
- [x] No new warnings generated

## Screenshots (if applicable)
[Add screenshots or GIFs showing the feature]

## Performance Impact
- Database query: ~50ms
- API response time: <200ms
- No breaking changes
```

### Code Review Checklist (for Reviewers)

```
Architecture & Design
- [ ] Code follows project architecture patterns
- [ ] Database schema changes reviewed
- [ ] API contract is backward compatible
- [ ] No circular dependencies

Functionality
- [ ] Logic is correct and handles edge cases
- [ ] Accepts all valid inputs
- [ ] Rejects invalid inputs gracefully
- [ ] Error handling is appropriate
- [ ] Integrates with existing features

Testing
- [ ] Unit tests cover happy path + edge cases
- [ ] Integration tests pass
- [ ] No decrease in code coverage
- [ ] Tests are readable and maintainable

Code Quality
- [ ] Code is readable (clear naming, appropriate comments)
- [ ] No code duplication
- [ ] Follows style guide (linting passes)
- [ ] Performance is acceptable
- [ ] No security vulnerabilities

Documentation
- [ ] Code comments explain "why", not "what"
- [ ] Docstrings updated
- [ ] README updated if needed
- [ ] API documentation updated

Performance
- [ ] No unnecessary database queries
- [ ] No N+1 query problems
- [ ] Appropriate caching used
- [ ] Response times acceptable
```

### Review Comment Examples

#### ✅ Good Feedback
```
"I like how you extracted the nutrition parsing logic into a separate service.
This makes it testable and reusable. Consider adding type hints to the
parameters for better IDE support."
```

#### ❌ Avoid
```
"This is bad code."
"Why did you do this?"
"This will never work."
```

---

## 📊 Metrics & Tracking

### Velocity Tracking
```
Sprint | Committed | Completed | Velocity | Burndown
─────────────────────────────────────────────────────
1      | 95        | 90        | 95%      | 📉 Good
2      | 100       | 100       | 100%     | 📈 Strong
3      | 105       | 98        | 93%      | 📉 Good
4      | 110       | 105       | 95%      | 📈 Strong
───────────────────────────────────────────────────────
Avg Velocity: 95.75 points/sprint
```

### Team Health Metrics

Track weekly via brief survey:
```
1. How clear is the sprint goal? (1-5)
2. Do you feel blocked? (Y/N)
3. Are code reviews timely? (Y/N)
4. Team morale (1-5)
5. Overall happiness with work (1-5)
```

Target metrics:
- **Clarity**: > 4.0
- **Blockers**: < 1 per day
- **Review Time**: < 4 hours
- **Morale**: > 4.0
- **Happiness**: > 4.0

### Code Quality Metrics

```
Metric              | Target  | Current | Status
─────────────────────────────────────────────
Code Coverage       | ≥ 80%   | 82%     | ✅
Linting Pass Rate   | 100%    | 100%    | ✅
API Response Time   | < 200ms | 145ms   | ✅
Test Pass Rate      | 100%    | 100%    | ✅
```

---

## 🤝 Collaboration Best Practices

### Communication Norms

#### Synchronous (Real-time)
- **Use for**: Quick decisions, complex discussions, blockers
- **Channels**: Standup, scheduled meetings, Slack video
- **Response time**: Immediate

#### Asynchronous (Recorded)
- **Use for**: Documentation, decisions, context
- **Channels**: GitHub Issues, PRs, Slack threads, Wiki
- **Response time**: Within business hours

#### Escalation Path
1. Try to resolve with direct teammate (Slack DM)
2. Raise in standup (2 min discussion)
3. Schedule 1:1 with tech lead
4. Schedule team sync if affects many people
5. Escalate to manager if blocking progress

### Decision-Making Framework

**For Technical Decisions**:
1. Document decision in ADR (Architecture Decision Record)
2. Post in #technical-decisions Slack channel
3. Allow 24 hours for feedback
4. Final call with tech lead
5. Archive decision in wiki

**For Product Decisions**:
1. Discuss in Sprint Planning
2. Verify with stakeholders
3. Document in GitHub issue
4. Implement with feedback integrated

### Pair Programming

**When to Use**:
- Complex features requiring multiple people
- Code review of critical paths
- Onboarding new team members
- Debugging difficult issues

**Guidelines**:
- 45-min sessions (Pomodoro)
- Driver & navigator swap every 15 min
- Record learnings in shared doc

---

## 🔐 GitHub Project Management

### Issue Lifecycle

```
1. BACKLOG (Created by PM)
   └─ Priority set, no milestone
   
2. REFINED (Estimated by team)
   ├─ Story points assigned
   ├─ Acceptance criteria defined
   └─ Ready for sprint planning
   
3. SPRINT (Committed in sprint)
   ├─ Milestone set
   ├─ Owner assigned
   └─ Status: Todo
   
4. IN PROGRESS (Developer working)
   ├─ Branch created
   ├─ Status: In Progress
   └─ Updates in PR
   
5. IN REVIEW (Code review)
   ├─ PR created
   ├─ Status: In Review
   └─ 2 approvals needed
   
6. DONE (Merged to main)
   ├─ Tests passing
   ├─ Status: Done
   └─ Closed issue

7. DEPLOYED (In production)
   └─ Feature released
```

### Label System

**Type**:
- `type/feature` - New feature
- `type/bug` - Bug fix
- `type/docs` - Documentation
- `type/refactor` - Code refactoring
- `type/test` - Testing

**Priority**:
- `priority/critical` - Blocks other work
- `priority/high` - Important, do soon
- `priority/medium` - Normal priority
- `priority/low` - Nice to have

**Epic**:
- `epic/user-management` - User features
- `epic/meal-ingestion` - Data input
- `epic/food-recognition` - ML features
- `epic/recommendations` - Suggestion engine
- `epic/privacy-security` - Privacy/security
- `epic/frontend` - UI/UX
- `epic/infrastructure` - DevOps/platform

**Status** (managed by automation):
- `status/todo` - Not started
- `status/in-progress` - Currently working
- `status/in-review` - Code review
- `status/done` - Completed

---

## 📚 Documentation Standards

### Code Comments

```python
# ❌ BAD - Explains what the code does (obvious)
def calculate_calories(foods):
    total = 0  # Initialize total to 0
    for food in foods:  # Loop through foods
        total += food.calories  # Add food calories
    return total  # Return total

# ✅ GOOD - Explains why, not what
def calculate_calories(foods):
    """
    Calculate total calories from multiple food items.
    
    Uses food database nutritional info rather than user estimates
    to ensure accuracy for recommendation engine.
    """
    return sum(food.calories for food in foods)
```

### Docstring Format

```python
def create_user(email: str, password: str) -> User:
    """
    Create a new user account with authentication.
    
    Args:
        email: User email address (must be unique)
        password: User password (minimum 12 characters)
        
    Returns:
        User: Created user object with ID
        
    Raises:
        ValueError: If email already exists
        ValueError: If password too short
        
    Example:
        >>> user = create_user("alice@example.com", "secure_password123")
        >>> user.id
        'usr_12345'
    """
```

### README Quality

Every module should have a README with:
- **Purpose**: What does this module do?
- **Dependencies**: What does it need?
- **Usage**: How do I use it?
- **Examples**: Code samples
- **Testing**: How to run tests
- **Contributing**: How to improve it

---

## 🚀 Release Process

### Release Checklist

- [ ] All tests passing
- [ ] Code coverage > 80%
- [ ] No critical security vulnerabilities
- [ ] Documentation updated
- [ ] Database migrations prepared
- [ ] Performance metrics acceptable
- [ ] Deployment checklist completed

### Deployment Steps

```bash
# 1. Create release branch
git checkout -b release/v0.1.0

# 2. Update version
echo "0.1.0" > VERSION

# 3. Update CHANGELOG
# Document new features, bug fixes, breaking changes

# 4. Create release PR
git push origin release/v0.1.0
# Create PR: release/v0.1.0 → main

# 5. After approval, merge
git checkout main
git pull
git merge release/v0.1.0

# 6. Tag release
git tag -a v0.1.0 -m "Release v0.1.0 - MVP Launch"
git push origin v0.1.0

# 7. Deploy to production
bash scripts/deploy.sh v0.1.0
```

---

## 📞 Escalation & Support

### Blockers Protocol

**If blocked for > 1 hour**:
1. Post in #blockers Slack channel
2. Tag tech lead
3. Post in standup
4. Schedule quick sync

**Common Blockers & Solutions**:
- "Can't connect to database" → Restart container, check credentials
- "API timeout" → Check logs, profile slow queries
- "Test failures" → Run locally, check environment
- "Merge conflicts" → Rebase on main, resolve conflicts

### Off-hours Support

**Incident Response** (for production issues):
1. Post in #incidents Slack channel
2. Determine severity (Critical/High/Medium/Low)
3. Page on-call engineer if Critical
4. Documented post-mortem within 24 hours

---

## 🎓 Onboarding Checklist

For new team members:

**Week 1**:
- [ ] Send welcome package & links
- [ ] Set up development environment (see DEVELOPMENT_SETUP.md)
- [ ] Join team Slack, attend standup
- [ ] Complete code review of sample PRs
- [ ] Read architecture docs

**Week 2**:
- [ ] Complete first small bug fix (~3 points)
- [ ] Pair program with senior engineer
- [ ] Present learnings to team
- [ ] Get code review feedback

**Week 3-4**:
- [ ] Take on feature story (~5 points)
- [ ] Contribute to sprint planning
- [ ] Attend retrospective
- [ ] Give feedback on setup process

**Month 2**:
- [ ] Fully productive (contributing full sprint worth of work)
- [ ] Reviewing other PRs
- [ ] Mentoring newer team members
- [ ] Making architectural decisions

---

## 📖 Template: Weekly Status Report

**Sent Friday 5 PM to leadership**:

```
WEEK OF JAN 15-19

🎯 SPRINT PROGRESS
- Completed: 23/30 story points (77%)
- Remaining: 7/30 story points
- On track for Sprint 1 completion

🔧 COMPLETED THIS WEEK
1. User authentication API (5 pts) - DONE
2. Meal ingestion endpoint (8 pts) - IN REVIEW
3. Dashboard layout (5 pts) - IN PROGRESS

🚨 BLOCKERS & RISKS
- YOLOv8 model training (high risk) - Need ML expertise
- Database schema review needed - Blocking 2 PRs
- Waiting on security audit results

📊 METRICS
- Team velocity: 95 points/sprint (healthy)
- Code coverage: 82% (target: 80%)
- Code review time: 2.5 hours (target: 4 hours)
- Team morale: 4.2/5 (good)

🎯 NEXT WEEK FOCUS
- Complete food recognition service
- Finish recommendations engine
- Deploy to staging
- Begin end-to-end testing
```

---

## 🔗 Related Documents
- [PROJECT_BACKLOG.md](PROJECT_BACKLOG.md) - Sprint & backlog details
- [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) - Setup guide
- [ADVANCED_IMPLEMENTATION_GUIDE.md](ADVANCED_IMPLEMENTATION_GUIDE.md) - Technical reference

