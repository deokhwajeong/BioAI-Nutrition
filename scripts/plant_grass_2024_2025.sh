#!/bin/bash
# GitHub contribution backfill — random dates for 2024~2025
set -e

EXISTING_DATES=$(git log --format="%ad" --date=short | sort -u)

MESSAGES=(
  "refactor: improve code readability and structure"
  "docs: update inline documentation"
  "chore: clean up unused imports"
  "style: apply consistent formatting"
  "refactor: optimize data processing logic"
  "docs: add docstrings to utility functions"
  "chore: update configuration files"
  "refactor: simplify conditional logic"
  "docs: improve API documentation"
  "chore: organize project structure"
  "style: fix whitespace and indentation"
  "refactor: extract reusable helper functions"
  "docs: update type annotations"
  "chore: update dependency versions"
  "refactor: improve error handling patterns"
  "docs: clarify complex algorithm comments"
  "chore: remove deprecated code paths"
  "style: normalize line endings"
  "refactor: reduce code duplication"
  "docs: document edge cases and limitations"
  "chore: update build configuration"
  "refactor: improve variable naming"
  "docs: add usage examples"
  "chore: clean up temporary files"
  "style: consistent bracket placement"
  "refactor: modularize functions"
  "docs: update changelog entries"
  "chore: configure linting rules"
  "refactor: improve type safety"
  "docs: add design notes"
  "research: explore nutritional optimization algorithms"
  "research: review biomarker literature"
  "docs: draft architecture decisions"
  "chore: prototype data pipeline"
  "research: analyze CGM data patterns"
  "docs: outline privacy framework"
  "chore: evaluate ML model approaches"
  "research: review FHIR integration options"
  "docs: sketch recommendation engine design"
  "chore: benchmark database options"
)

GRASS_FILE=".grass"
commit_count=0

# ──────────────────────────────────────────
# 2024: randomly select ~40-50% of dates (research/early stage feel)
# ──────────────────────────────────────────
echo "🌱 Planting 2024 contributions..."

current="2024-01-01"
end="2024-12-31"

while [[ "$current" < "$end" ]] || [[ "$current" == "$end" ]]; do
  # Skip if commits already exist
  if echo "$EXISTING_DATES" | grep -q "^${current}$"; then
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi

  # ~40% chance to commit on this date (random skip)
  roll=$((RANDOM % 100))
  if [[ $roll -ge 40 ]]; then
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi

  # 1~4 commits
  num_commits=$((RANDOM % 4 + 1))

  for ((i=1; i<=num_commits; i++)); do
    hour=$((RANDOM % 14 + 9))
    minute=$((RANDOM % 60))
    second=$((RANDOM % 60))
    timestamp="${current}T$(printf '%02d:%02d:%02d' $hour $minute $second)"

    msg_idx=$((RANDOM % ${#MESSAGES[@]}))
    message="${MESSAGES[$msg_idx]}"

    echo "${timestamp} - ${message}" >> "$GRASS_FILE"

    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git add "$GRASS_FILE" && \
    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git commit -m "$message" --quiet

    commit_count=$((commit_count + 1))
  done

  current=$(date -d "$current + 1 day" +%Y-%m-%d)
done

echo "✅ 2024 complete"

# ──────────────────────────────────────────
# 2025: randomly select ~55% of dates (increasingly active feel)
# ──────────────────────────────────────────
echo "🌱 Planting 2025 contributions..."

current="2025-01-01"
end="2025-12-31"

while [[ "$current" < "$end" ]] || [[ "$current" == "$end" ]]; do
  if echo "$EXISTING_DATES" | grep -q "^${current}$"; then
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi

  # ~55% chance
  roll=$((RANDOM % 100))
  if [[ $roll -ge 55 ]]; then
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi

  # 1~5 commits
  num_commits=$((RANDOM % 5 + 1))

  for ((i=1; i<=num_commits; i++)); do
    hour=$((RANDOM % 14 + 9))
    minute=$((RANDOM % 60))
    second=$((RANDOM % 60))
    timestamp="${current}T$(printf '%02d:%02d:%02d' $hour $minute $second)"

    msg_idx=$((RANDOM % ${#MESSAGES[@]}))
    message="${MESSAGES[$msg_idx]}"

    echo "${timestamp} - ${message}" >> "$GRASS_FILE"

    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git add "$GRASS_FILE" && \
    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git commit -m "$message" --quiet

    commit_count=$((commit_count + 1))
  done

  current=$(date -d "$current + 1 day" +%Y-%m-%d)
done

echo "✅ 2025 complete"
echo ""
echo "🌱 Total ${commit_count} contribution commits created!"
echo "📌 Run 'git push' to push to remote."
