#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Natural GitHub contribution generator v2
# - Randomly modifies multiple files to simulate real development
# - Differentiates activity patterns by year
# ═══════════════════════════════════════════════════════════════
set -e

REPO_DIR="$(git rev-parse --show-toplevel)"
cd "$REPO_DIR"

EXISTING_DATES=$(git log --format="%ad" --date=short | sort -u)

# ── Commit message pool (by category) ──
MSG_RESEARCH=(
  "research: survey personalized nutrition optimization methods"
  "research: review differential privacy in health data"
  "research: analyze CGM time-series patterns"
  "research: evaluate FHIR R4 resource models"
  "research: study genetic nutrient interaction pathways"
  "research: benchmark federated learning approaches"
  "research: explore graph neural networks for biomarker fusion"
  "research: compare meal image recognition architectures"
  "research: review metabolic syndrome biomarkers"
  "research: examine microbiome-diet interactions"
)

MSG_DOCS=(
  "docs: update architecture design notes"
  "docs: refine data flow diagrams"
  "docs: add API endpoint specifications"
  "docs: document privacy framework requirements"
  "docs: outline recommendation engine design"
  "docs: update system requirements"
  "docs: add biomarker integration notes"
  "docs: draft safety constraint specifications"
  "docs: update development guidelines"
  "docs: add deployment architecture notes"
)

MSG_FEAT=(
  "feat: add nutrient scoring utility"
  "feat: implement biomarker validation"
  "feat: add CGM data preprocessing"
  "feat: implement dietary constraint checker"
  "feat: add genetic risk factor mapping"
  "feat: implement temporal data alignment"
  "feat: add privacy-preserving data transform"
  "feat: implement recommendation scoring"
  "feat: add metabolic state estimator"
  "feat: implement safety override logic"
)

MSG_REFACTOR=(
  "refactor: improve data pipeline efficiency"
  "refactor: simplify biomarker processing"
  "refactor: optimize nutrient calculation"
  "refactor: restructure service layer"
  "refactor: improve error handling"
  "refactor: extract common utilities"
  "refactor: optimize database queries"
  "refactor: simplify configuration management"
  "refactor: improve type annotations"
  "refactor: modularize test fixtures"
)

MSG_FIX=(
  "fix: correct nutrient unit conversion"
  "fix: handle missing biomarker values"
  "fix: resolve timezone offset issue"
  "fix: correct statistical aggregation"
  "fix: handle edge case in scoring"
  "fix: resolve data validation error"
  "fix: correct interpolation boundary"
  "fix: handle concurrent access"
  "fix: resolve encoding issue"
  "fix: correct API response format"
)

MSG_CHORE=(
  "chore: update dependency versions"
  "chore: configure CI pipeline"
  "chore: update linting rules"
  "chore: clean up build artifacts"
  "chore: update test configuration"
  "chore: optimize Docker image"
  "chore: configure pre-commit hooks"
  "chore: update environment variables"
  "chore: reorganize project structure"
  "chore: update gitignore patterns"
)

MSG_TEST=(
  "test: add biomarker validation tests"
  "test: add nutrient calculation edge cases"
  "test: improve integration test coverage"
  "test: add privacy module tests"
  "test: add recommendation scoring tests"
  "test: add CGM preprocessing tests"
  "test: add API endpoint tests"
  "test: add safety constraint tests"
  "test: add data pipeline tests"
  "test: add temporal sync tests"
)

MSG_STYLE=(
  "style: format code with black"
  "style: fix import ordering"
  "style: apply consistent naming"
  "style: normalize whitespace"
  "style: fix line length issues"
)

# ── Collect actual file list within the project ──
mapfile -t PY_FILES < <(find . -name "*.py" -not -path "./.venv/*" -not -path "*node_modules*" -not -path "*__pycache__*" 2>/dev/null)
mapfile -t TS_FILES < <(find . \( -name "*.ts" -o -name "*.tsx" \) -not -path "*node_modules*" 2>/dev/null)
mapfile -t MD_FILES < <(find . -name "*.md" -not -path "./.venv/*" -not -path "*node_modules*" 2>/dev/null)
mapfile -t YAML_FILES < <(find . \( -name "*.yaml" -o -name "*.yml" \) -not -path "*node_modules*" -not -path "./.venv/*" 2>/dev/null)
mapfile -t JSON_FILES < <(find . -name "*.json" -not -path "./.venv/*" -not -path "*node_modules*" -not -name "pnpm-lock.yaml" -not -name "package-lock.json" 2>/dev/null)

ALL_EDITABLE=("${PY_FILES[@]}" "${TS_FILES[@]}" "${MD_FILES[@]}" "${YAML_FILES[@]}" "${JSON_FILES[@]}")

# ── File modification functions ──

# Add/modify comments/docstrings in Python files
modify_py_file() {
  local file="$1"
  local date="$2"
  [[ ! -f "$file" ]] && return 1
  
  local line_count=$(wc -l < "$file")
  [[ $line_count -lt 3 ]] && return 1
  
  local action=$((RANDOM % 5))
  case $action in
    0) # Append comment at end of file
      echo "# Updated: ${date}" >> "$file"
      ;;
    1) # Update module docstring
      if head -1 "$file" | grep -q '"""'; then
        sed -i "1s/.*/\"\"\"Module updated ${date}.\"\"\"/" "$file"
      else
        sed -i "1i\\# ${date} revision" "$file"
      fi
      ;;
    2) # Add TODO comment
      local todos=("TODO: optimize this section" "TODO: add type hints" "TODO: improve error handling" "TODO: add unit tests" "TODO: refactor for clarity")
      local todo="${todos[$((RANDOM % ${#todos[@]}))]}"
      local insert_line=$((RANDOM % line_count + 1))
      sed -i "${insert_line}a\\# ${todo}" "$file"
      ;;
    3) # Clean up empty lines (collapse consecutive empty lines to one)
      sed -i '/^$/N;/^\n$/d' "$file"
      echo "" >> "$file"
      ;;
    4) # Remove trailing whitespace + add date comment
      sed -i 's/[[:space:]]*$//' "$file"
      echo "# Last reviewed: ${date}" >> "$file"
      ;;
  esac
  return 0
}

# Modify TypeScript/TSX files
modify_ts_file() {
  local file="$1"
  local date="$2"
  [[ ! -f "$file" ]] && return 1
  
  local action=$((RANDOM % 4))
  case $action in
    0) echo "// Updated: ${date}" >> "$file" ;;
    1) sed -i "1i\\// ${date} revision" "$file" ;;
    2) sed -i 's/[[:space:]]*$//' "$file" ;;
    3) echo "" >> "$file" ;;
  esac
  return 0
}

# Modify Markdown files
modify_md_file() {
  local file="$1"
  local date="$2"
  [[ ! -f "$file" ]] && return 1
  
  local action=$((RANDOM % 3))
  case $action in
    0) echo "" >> "$file" ;; # Add empty line
    1) sed -i 's/[[:space:]]*$//' "$file" ;; # Remove trailing whitespace
    2) echo "<!-- Last updated: ${date} -->" >> "$file" ;;
  esac
  return 0
}

# Create new files (notes, logs, drafts, etc.)
create_note_file() {
  local date="$1"
  local type=$((RANDOM % 4))
  local month=$(echo "$date" | cut -d'-' -f2)
  local year=$(echo "$date" | cut -d'-' -f1)
  
  case $type in
    0)
      local dir="docs/notes"
      mkdir -p "$dir"
      local f="$dir/${date}-research.md"
      echo "# Research Notes - ${date}" > "$f"
      echo "" >> "$f"
      echo "## Topics Explored" >> "$f"
      echo "- Biomarker data integration patterns" >> "$f"
      echo "- Privacy-preserving computation methods" >> "$f"
      echo "$f"
      ;;
    1)
      local dir="docs/design"
      mkdir -p "$dir"
      local f="$dir/${date}-design.md"
      echo "# Design Notes - ${date}" > "$f"
      echo "" >> "$f"
      echo "## Architecture Decisions" >> "$f"
      echo "- Reviewed data pipeline structure" >> "$f"
      echo "$f"
      ;;
    2)
      local dir="scripts/utils"
      mkdir -p "$dir"
      local f="$dir/helper_${year}${month}.py"
      if [[ ! -f "$f" ]]; then
        echo '"""Utility helpers."""' > "$f"
        echo "" >> "$f"
        echo "# ${date}" >> "$f"
      else
        echo "# ${date} update" >> "$f"
      fi
      echo "$f"
      ;;
    3)
      local dir="docs/adr"
      mkdir -p "$dir"
      local idx=$(find "$dir" -name "*.md" 2>/dev/null | wc -l)
      idx=$((idx + 1))
      local f="$dir/$(printf '%04d' $idx)-decision.md"
      if [[ ! -f "$f" ]]; then
        echo "# ADR-${idx}: Architecture Decision" > "$f"
        echo "" >> "$f"
        echo "**Date:** ${date}" >> "$f"
        echo "" >> "$f"
        echo "## Context" >> "$f"
        echo "Evaluated approach for data processing." >> "$f"
        echo "" >> "$f"
        echo "## Decision" >> "$f"
        echo "Adopted modular pipeline architecture." >> "$f"
      fi
      echo "$f"
      ;;
  esac
}

# Select and modify random file
modify_random_file() {
  local date="$1"
  local attempts=0
  
  while [[ $attempts -lt 10 ]]; do
    local action=$((RANDOM % 10))
    
    if [[ $action -lt 3 ]] && [[ ${#PY_FILES[@]} -gt 0 ]]; then
      local idx=$((RANDOM % ${#PY_FILES[@]}))
      local file="${PY_FILES[$idx]}"
      if modify_py_file "$file" "$date"; then
        git add "$file" 2>/dev/null
        return 0
      fi
    elif [[ $action -lt 5 ]] && [[ ${#TS_FILES[@]} -gt 0 ]]; then
      local idx=$((RANDOM % ${#TS_FILES[@]}))
      local file="${TS_FILES[$idx]}"
      if modify_ts_file "$file" "$date"; then
        git add "$file" 2>/dev/null
        return 0
      fi
    elif [[ $action -lt 7 ]] && [[ ${#MD_FILES[@]} -gt 0 ]]; then
      local idx=$((RANDOM % ${#MD_FILES[@]}))
      local file="${MD_FILES[$idx]}"
      if modify_md_file "$file" "$date"; then
        git add "$file" 2>/dev/null
        return 0
      fi
    else
      # Create new file
      local new_file=$(create_note_file "$date")
      if [[ -n "$new_file" ]] && [[ -f "$new_file" ]]; then
        git add "$new_file" 2>/dev/null
        return 0
      fi
    fi
    attempts=$((attempts + 1))
  done
  
  # Fallback: create a new note file
  local new_file=$(create_note_file "$date")
  git add "$new_file" 2>/dev/null
  return 0
}

# Select message category (varies by year)
get_message() {
  local year="$1"
  local roll=$((RANDOM % 100))
  
  if [[ "$year" == "2022" ]] || [[ "$year" == "2023" ]]; then
    # Early stage: higher research/docs weight
    if [[ $roll -lt 35 ]]; then
      echo "${MSG_RESEARCH[$((RANDOM % ${#MSG_RESEARCH[@]}))]}"
    elif [[ $roll -lt 60 ]]; then
      echo "${MSG_DOCS[$((RANDOM % ${#MSG_DOCS[@]}))]}"
    elif [[ $roll -lt 75 ]]; then
      echo "${MSG_CHORE[$((RANDOM % ${#MSG_CHORE[@]}))]}"
    elif [[ $roll -lt 85 ]]; then
      echo "${MSG_FEAT[$((RANDOM % ${#MSG_FEAT[@]}))]}"
    elif [[ $roll -lt 95 ]]; then
      echo "${MSG_STYLE[$((RANDOM % ${#MSG_STYLE[@]}))]}"
    else
      echo "${MSG_FIX[$((RANDOM % ${#MSG_FIX[@]}))]}"
    fi
  elif [[ "$year" == "2024" ]]; then
    # Mid stage: increasing feat/refactor weight
    if [[ $roll -lt 20 ]]; then
      echo "${MSG_RESEARCH[$((RANDOM % ${#MSG_RESEARCH[@]}))]}"
    elif [[ $roll -lt 40 ]]; then
      echo "${MSG_FEAT[$((RANDOM % ${#MSG_FEAT[@]}))]}"
    elif [[ $roll -lt 55 ]]; then
      echo "${MSG_REFACTOR[$((RANDOM % ${#MSG_REFACTOR[@]}))]}"
    elif [[ $roll -lt 70 ]]; then
      echo "${MSG_DOCS[$((RANDOM % ${#MSG_DOCS[@]}))]}"
    elif [[ $roll -lt 80 ]]; then
      echo "${MSG_TEST[$((RANDOM % ${#MSG_TEST[@]}))]}"
    elif [[ $roll -lt 90 ]]; then
      echo "${MSG_FIX[$((RANDOM % ${#MSG_FIX[@]}))]}"
    else
      echo "${MSG_CHORE[$((RANDOM % ${#MSG_CHORE[@]}))]}"
    fi
  else
    # 2025: full-scale development, feat/test/fix focused
    if [[ $roll -lt 25 ]]; then
      echo "${MSG_FEAT[$((RANDOM % ${#MSG_FEAT[@]}))]}"
    elif [[ $roll -lt 45 ]]; then
      echo "${MSG_REFACTOR[$((RANDOM % ${#MSG_REFACTOR[@]}))]}"
    elif [[ $roll -lt 60 ]]; then
      echo "${MSG_TEST[$((RANDOM % ${#MSG_TEST[@]}))]}"
    elif [[ $roll -lt 75 ]]; then
      echo "${MSG_FIX[$((RANDOM % ${#MSG_FIX[@]}))]}"
    elif [[ $roll -lt 85 ]]; then
      echo "${MSG_DOCS[$((RANDOM % ${#MSG_DOCS[@]}))]}"
    elif [[ $roll -lt 95 ]]; then
      echo "${MSG_CHORE[$((RANDOM % ${#MSG_CHORE[@]}))]}"
    else
      echo "${MSG_STYLE[$((RANDOM % ${#MSG_STYLE[@]}))]}"
    fi
  fi
}

# ── Main loop ──
generate_year() {
  local start="$1"
  local end="$2"
  local prob="$3"      # Probability (%) to commit on a given date
  local min_commits="$4"
  local max_commits="$5"
  local year_label="$6"
  
  local current="$start"
  local day_count=0
  local commit_count=0
  
  while [[ "$current" < "$end" ]] || [[ "$current" == "$end" ]]; do
    # Skip if commits already exist
    if echo "$EXISTING_DATES" | grep -q "^${current}$"; then
      current=$(date -d "$current + 1 day" +%Y-%m-%d)
      continue
    fi
    
    # Adjust probability by day of week (lower on weekends)
    local dow=$(date -d "$current" +%u)  # 1=Mon, 7=Sun
    local adjusted_prob=$prob
    if [[ $dow -ge 6 ]]; then
      adjusted_prob=$((prob * 60 / 100))  # Weekends reduced to 60%
    fi
    
    # Randomly decide whether to commit on this date
    local roll=$((RANDOM % 100))
    if [[ $roll -ge $adjusted_prob ]]; then
      current=$(date -d "$current + 1 day" +%Y-%m-%d)
      continue
    fi
    
    # Determine number of commits
    local num=$((RANDOM % (max_commits - min_commits + 1) + min_commits))
    local year=$(echo "$current" | cut -d'-' -f1)
    
    for ((i=1; i<=num; i++)); do
      local hour=$((RANDOM % 14 + 9))
      local minute=$((RANDOM % 60))
      local second=$((RANDOM % 60))
      local timestamp="${current}T$(printf '%02d:%02d:%02d' $hour $minute $second)"
      
      local message=$(get_message "$year")
      
      # Randomly modify 1~3 files
      local file_count=$((RANDOM % 3 + 1))
      for ((f=1; f<=file_count; f++)); do
        modify_random_file "$current"
      done
      
      # Check staging and commit
      if git diff --cached --quiet 2>/dev/null; then
        # Create note file if no changes exist
        local nf=$(create_note_file "$current")
        git add "$nf" 2>/dev/null
      fi
      
      GIT_AUTHOR_DATE="$timestamp" GIT_COMMITTER_DATE="$timestamp" \
        git commit -m "$message" --quiet --allow-empty 2>/dev/null || true
      
      commit_count=$((commit_count + 1))
    done
    
    day_count=$((day_count + 1))
    current=$(date -d "$current + 1 day" +%Y-%m-%d)
  done
  
  echo "✅ ${year_label} complete: ${day_count} days, ${commit_count} commits"
}

echo "🌱 Starting natural contribution generation..."
echo ""

# 2022: Early research stage, sparse (~30%)
echo "📅 Generating 2022..."
generate_year "2022-01-01" "2022-12-31" 30 1 2 "2022"

# 2023: Research + prototyping (~35%)
echo "📅 Generating 2023..."
generate_year "2023-01-01" "2023-12-31" 35 1 3 "2023"

# 2024: Full-scale development begins (~45%)
echo "📅 Generating 2024..."
generate_year "2024-01-01" "2024-12-31" 45 1 4 "2024"

# 2025: Active development (~55%), before 2025-11-11 only
echo "📅 Generating 2025..."
generate_year "2025-01-01" "2025-12-31" 55 1 5 "2025"

# 2026: Fill empty dates only (~90%)
echo "📅 Filling 2026 empty dates..."
generate_year "2026-01-01" "2026-02-23" 90 2 4 "2026"

echo ""
echo "🌱 Contribution generation complete!"
echo "📊 Total commits: $(git log --oneline | wc -l)"
echo "📅 Active days: $(git log --format='%ad' --date=short | sort -u | wc -l)"
echo ""
echo "📌 Run 'git push --force origin main' to push to remote."
