#!/bin/bash
# GitHub contribution graph backfill script
# Creates past commits for empty dates.

set -e

# List of dates with existing commits
EXISTING_DATES=$(git log --format="%ad" --date=short | sort -u)

# Commit message pool
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
  "docs: add usage examples to README"
  "chore: clean up temporary files"
  "style: consistent bracket placement"
  "refactor: modularize monolithic functions"
  "docs: update changelog entries"
  "chore: configure linting rules"
  "refactor: improve type safety"
  "docs: add architectural decision records"
)

# Grass file (for commit records)
GRASS_FILE=".grass"

START_DATE="2026-01-01"
END_DATE="2026-02-23"

# Iterate over dates
current="$START_DATE"
commit_count=0

while [[ "$current" < "$END_DATE" ]] || [[ "$current" == "$END_DATE" ]]; do
  # Skip dates that already have commits
  if echo "$EXISTING_DATES" | grep -q "^${current}$"; then
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
    continue
  fi

  # Random commit count: 3~5
  num_commits=$((RANDOM % 3 + 3))

  for ((i=1; i<=num_commits; i++)); do
    # Generate random time (09:00 ~ 22:00)
    hour=$((RANDOM % 14 + 9))
    minute=$((RANDOM % 60))
    second=$((RANDOM % 60))
    timestamp="${current}T$(printf '%02d:%02d:%02d' $hour $minute $second)"

    # Select random message
    msg_idx=$((RANDOM % ${#MESSAGES[@]}))
    message="${MESSAGES[$msg_idx]}"

    # Record timestamp in grass file
    echo "${timestamp} - ${message}" >> "$GRASS_FILE"

    # Commit with past date
    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git add "$GRASS_FILE" && \
    GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
      git commit -m "$message" --quiet

    commit_count=$((commit_count + 1))
  done

  echo "✅ $current — $num_commits commits"
  current=$(date -d "$current + 1 day" +%Y-%m-%d)
done

echo ""
echo "🌱 Total ${commit_count} contribution commits created!"
echo "📌 Run 'git push' to push to remote."
