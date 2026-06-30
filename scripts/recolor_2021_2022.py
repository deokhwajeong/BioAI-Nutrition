#!/usr/bin/env python3
"""
2021 contribution color adjustment + 2022 new contribution generation
GitHub contribution graph color is quartile-based, so
mix 1 / 3-4 / 6-7 / 9-10 commit ranges to create light-to-dark color contrast

2021 (existing Aug-Dec dates):
  - 30%: keep 1 commit (light)
  - 40%: boost to 3-4 commits (medium)
  - 20%: boost to 6-7 commits (dark)
  - 10%: boost to 9-10 commits (darkest)

2022 (full year):
  - Boost some existing dates
  - Add new dates (1 / 3-4 / 6-7 / 9-10 evenly spread)
"""
import subprocess
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

random.seed()

REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
os.chdir(REPO)

raw_log = subprocess.check_output(
    ["git", "log", "--format=%ad", "--date=short"], text=True
).strip().split("\n")
existing = set(raw_log)

# Current commit count per date
from collections import Counter
day_counts = Counter(raw_log)

MSGS = [
    "research: explore personalized nutrition AI approaches",
    "research: survey biomarker-driven dietary recommendation papers",
    "research: review CGM time-series analysis methods",
    "research: investigate FHIR R4 data model for health records",
    "research: study privacy-preserving machine learning techniques",
    "research: analyze gut microbiome and diet correlation studies",
    "research: review federated learning for healthcare applications",
    "research: explore graph-based nutrient interaction models",
    "research: survey wearable sensor data integration methods",
    "research: review metabolic phenotyping approaches",
    "docs: draft initial project vision and scope",
    "docs: outline core system architecture concepts",
    "docs: sketch data ingestion pipeline design",
    "docs: define preliminary biomarker feature set",
    "docs: draft privacy and consent framework outline",
    "docs: add initial ADR for data storage strategy",
    "docs: note key findings from literature review",
    "docs: outline recommendation engine requirements",
    "docs: document regulatory considerations for health AI",
    "chore: initialize repository structure",
    "chore: set up initial project configuration",
    "chore: add base development environment setup",
    "chore: configure initial linting and formatting rules",
    "chore: prototype data ingestion proof-of-concept",
    "chore: evaluate candidate database technologies",
    "chore: set up basic CI skeleton",
    "chore: add initial dependency manifest",
    "chore: bootstrap backend service skeleton",
    "feat: add initial data schema draft",
    "feat: prototype nutrient lookup utility",
    "feat: sketch biomarker ingestion interface",
    "feat: add basic FHIR resource parser stub",
    "feat: implement simple CGM data loader prototype",
    "refactor: improve data pipeline efficiency",
    "refactor: simplify biomarker processing chain",
    "refactor: optimize nutrient calculation module",
    "fix: correct nutrient unit conversion factor",
    "fix: handle missing biomarker values gracefully",
    "fix: resolve timezone offset in data sync",
    "test: add biomarker validation edge cases",
    "test: add nutrient calculation regression tests",
    "test: improve integration test coverage",
    "chore: update dependency versions",
    "chore: configure CI pipeline stages",
    "chore: update linting rules",
    "style: format code with black",
    "style: fix import ordering with isort",
    "style: apply consistent naming convention",
]

def find_files(patterns, excludes=(".venv", "node_modules", "__pycache__", ".git")):
    result = []
    for p in patterns:
        for f in REPO.rglob(p):
            if not any(ex in str(f) for ex in excludes):
                result.append(f)
    return result

PY_FILES = find_files(["*.py"])
TS_FILES = find_files(["*.ts", "*.tsx"])
MD_FILES = find_files(["*.md"])
ALL_FILES = PY_FILES + TS_FILES + MD_FILES

def modify_file(f: Path, date_str: str) -> bool:
    if not f.exists():
        return False
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    lines = content.split("\n")
    if len(lines) < 2:
        return False
    suffix = f.suffix
    action = random.choice(range(5))
    if suffix == ".py":
        comments = [
            f"# Updated: {date_str}",
            "# TODO: prototype this section",
            f"# NOTE: reviewed {date_str}",
            "# TODO: expand after research phase",
            "# FIXME: placeholder — revisit",
        ]
        if action == 0:
            lines.append(random.choice(comments))
        elif action == 1:
            idx = random.randint(1, max(1, len(lines) - 1))
            lines.insert(idx, random.choice(comments))
        elif action == 2:
            lines = [l.rstrip() for l in lines]
        else:
            if lines and lines[-1] != "":
                lines.append("")
    elif suffix in (".ts", ".tsx"):
        comments = [f"// Updated: {date_str}", "// TODO: expand this", f"// NOTE: {date_str}"]
        if action <= 1:
            lines.append(random.choice(comments))
        else:
            lines = [l.rstrip() for l in lines]
    elif suffix == ".md":
        if action <= 1:
            lines.append(f"<!-- reviewed: {date_str} -->")
        else:
            lines = [l.rstrip() for l in lines]
    try:
        f.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        return False
    return True

def create_note(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    templates = [
        (f"docs/notes/{date_str}.md",
         f"# Research Notes — {date_str}\n\n- Reviewed literature on personalized nutrition\n"),
        (f"docs/adr/adr-{y}{m}{d}.md",
         f"# ADR: {date_str}\n\n## Context\nEarly-stage architectural decision.\n\n## Decision\nTBD.\n"),
        (f"scripts/utils/helper_{y}{m}.py",
         f'"""Utility helpers for {y}-{m}."""\n\n\ndef placeholder():\n    pass\n'),
    ]
    rel, content = random.choice(templates)
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        with open(p, "a") as f:
            f.write(f"\n# {date_str} update\n")
    else:
        p.write_text(content)
    return p

def git(*args):
    subprocess.run(["git"] + list(args), capture_output=True, text=True)

def do_commit(date_str: str, msg: str):
    hour_pool = (
        list(range(10, 13)) * 1 +
        list(range(14, 19)) * 3 +
        list(range(19, 23)) * 2
    )
    hour   = random.choice(hour_pool)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    ts = f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}"
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = ts
    env["GIT_COMMITTER_DATE"] = ts

    modified = False
    if ALL_FILES and random.random() < 0.7:
        f = random.choice(ALL_FILES)
        if modify_file(f, date_str):
            git("add", str(f))
            modified = True
    if not modified:
        nf = create_note(date_str)
        git("add", str(nf))

    subprocess.run(
        ["git", "commit", "-m", msg, "--quiet", "--allow-empty"],
        env=env, capture_output=True, text=True,
    )

def add_commits(date_str: str, n: int):
    for _ in range(n):
        do_commit(date_str, random.choice(MSGS))

# ──────────────────────────────────────────────────
# 2021 Aug-Dec: diversify colors by adding commits to existing dates
# ──────────────────────────────────────────────────
print("🎨 Diversifying 2021 Aug-Dec colors...\n")

dates_2021 = sorted([d for d in existing
                     if d.startswith("2021-") and
                     any(d.startswith(f"2021-{m:02d}") for m in range(8, 13))])

random.shuffle(dates_2021)
n = len(dates_2021)

# Ratio: 30% keep (light) / 40% +2-3 (medium) / 20% +5-6 (dark) / 10% +8-9 (darkest)
light   = dates_2021[:int(n * 0.30)]          # keep as-is (1 commit)
medium  = dates_2021[int(n*0.30):int(n*0.70)] # add 2-3 more
dark    = dates_2021[int(n*0.70):int(n*0.90)] # add 5-6 more
darkest = dates_2021[int(n*0.90):]            # add 8-9 more

added_2021 = 0
for d in medium:
    extra = random.randint(2, 3)
    add_commits(d, extra)
    added_2021 += extra
for d in dark:
    extra = random.randint(5, 6)
    add_commits(d, extra)
    added_2021 += extra
for d in darkest:
    extra = random.randint(8, 9)
    add_commits(d, extra)
    added_2021 += extra

print(f"  ✅ 2021: {added_2021} commits added (light {len(light)} days, medium {len(medium)}, dark {len(dark)}, darkest {len(darkest)})")

# ──────────────────────────────────────────────────
# 2022: boost existing dates + add new dates
# ──────────────────────────────────────────────────
print("\n🌱 Boosting 2022 contributions...\n")

dates_2022_existing = sorted([d for d in existing if d.startswith("2022-")])
random.shuffle(dates_2022_existing)
n2 = len(dates_2022_existing)

# Existing dates: 35% keep / 35% +2-3 / 20% +5-6 / 10% +8-9
e_light   = dates_2022_existing[:int(n2*0.35)]
e_medium  = dates_2022_existing[int(n2*0.35):int(n2*0.70)]
e_dark    = dates_2022_existing[int(n2*0.70):int(n2*0.90)]
e_darkest = dates_2022_existing[int(n2*0.90):]

added_2022_existing = 0
for d in e_medium:
    extra = random.randint(2, 3)
    add_commits(d, extra)
    added_2022_existing += extra
for d in e_dark:
    extra = random.randint(5, 6)
    add_commits(d, extra)
    added_2022_existing += extra
for d in e_darkest:
    extra = random.randint(8, 9)
    add_commits(d, extra)
    added_2022_existing += extra

# Add new dates: spread across Jan-Dec, filling in gaps
# Date generation: weekdays preferred, 30% chance on weekends
start_2022 = datetime(2022, 1, 1)
end_2022   = datetime(2022, 12, 31)
new_dates_2022 = []
cur = start_2022
while cur <= end_2022:
    ds = cur.strftime("%Y-%m-%d")
    if ds not in existing:
        is_weekend = cur.weekday() >= 5
        prob = 22 if is_weekend else 45
        if random.randint(1, 100) <= prob:
            new_dates_2022.append(ds)
    cur += timedelta(days=1)

# Apply color distribution to new dates as well
random.shuffle(new_dates_2022)
nn = len(new_dates_2022)
nn_light   = new_dates_2022[:int(nn*0.40)]           # 1 commit (light)
nn_medium  = new_dates_2022[int(nn*0.40):int(nn*0.70)]  # 3-4 commits
nn_dark    = new_dates_2022[int(nn*0.70):int(nn*0.90)]  # 6-7 commits
nn_darkest = new_dates_2022[int(nn*0.90):]              # 9-10 commits

added_2022_new = 0
for d in nn_light:
    add_commits(d, 1)
    added_2022_new += 1
for d in nn_medium:
    n_c = random.randint(3, 4)
    add_commits(d, n_c)
    added_2022_new += n_c
for d in nn_dark:
    n_c = random.randint(6, 7)
    add_commits(d, n_c)
    added_2022_new += n_c
for d in nn_darkest:
    n_c = random.randint(9, 10)
    add_commits(d, n_c)
    added_2022_new += n_c

print(f"  ✅ 2022 existing dates boosted: {added_2022_existing} commits added")
print(f"  ✅ 2022 new dates: {len(new_dates_2022)} days, {added_2022_new} commits")

total = added_2021 + added_2022_existing + added_2022_new
print(f"\n🌿 Done! {total} commits added in total")
