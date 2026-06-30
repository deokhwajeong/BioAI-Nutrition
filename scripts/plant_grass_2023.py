#!/usr/bin/env python3
"""
2023 GitHub contribution generator — 2021 스타일 자연스러운 잔디
- 평일 ~42%, 주말 ~20% 활성 확률 (2021과 동일)
- 1-3 커밋/일, 주로 1개 (2021 분포)
- 오후/저녁 위주 시간대 (13~22시)
- research/docs/feat/chore 위주 메시지 (2023 단계)
"""
import subprocess
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

random.seed()

REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
os.chdir(REPO)

existing = set(
    subprocess.check_output(["git", "log", "--format=%ad", "--date=short"], text=True)
    .strip().split("\n")
)

# 2023 메시지 풀 — 초기 구현 + 리서치 단계 반영
MSGS = [
    # research
    "research: survey personalized nutrition optimization methods",
    "research: review differential privacy in health data",
    "research: analyze CGM time-series patterns for dietary correlation",
    "research: evaluate FHIR R4 resource models for nutrient data",
    "research: study genetic nutrient interaction pathways",
    "research: benchmark federated learning healthcare approaches",
    "research: explore graph neural networks for biomarker fusion",
    "research: compare meal image recognition architectures",
    "research: review metabolic syndrome biomarker selection",
    "research: examine microbiome-diet interaction literature",
    "research: analyze real-time glucose monitoring study outcomes",
    "research: review privacy-preserving ML frameworks",
    "research: investigate transformer models for health time-series",
    "research: survey wearable sensor data fusion methods",
    # docs
    "docs: update architecture design notes",
    "docs: refine data flow diagrams",
    "docs: add API endpoint specifications",
    "docs: document privacy framework requirements",
    "docs: outline recommendation engine design",
    "docs: update system requirements document",
    "docs: add biomarker integration design notes",
    "docs: draft safety constraint specifications",
    "docs: update development guidelines",
    "docs: add deployment architecture overview",
    "docs: clarify data model relationships",
    "docs: update ADR for data storage decision",
    "docs: add research summary notes",
    "docs: draft initial consent framework documentation",
    # feat (early implementation)
    "feat: add nutrient scoring utility stub",
    "feat: implement biomarker validation logic",
    "feat: add CGM data preprocessing pipeline skeleton",
    "feat: implement dietary constraint checker prototype",
    "feat: add genetic risk factor mapping draft",
    "feat: implement temporal data alignment module",
    "feat: add privacy-preserving data transform prototype",
    "feat: add meal nutrient decomposition utility",
    "feat: implement basic FHIR resource parser",
    "feat: add initial data schema definition",
    # chore
    "chore: update dependency versions",
    "chore: configure CI pipeline stages",
    "chore: update linting rules",
    "chore: clean up build artifacts",
    "chore: update test configuration",
    "chore: configure pre-commit hooks",
    "chore: update environment defaults",
    "chore: reorganize project layout",
    "chore: update gitignore patterns",
    "chore: set up development environment",
    # refactor
    "refactor: improve data pipeline structure",
    "refactor: simplify biomarker processing logic",
    "refactor: optimize nutrient calculation module",
    "refactor: restructure service layer interfaces",
    # fix
    "fix: correct nutrient unit conversion factor",
    "fix: handle missing biomarker values gracefully",
    "fix: resolve timezone offset in data sync",
    "fix: correct statistical aggregation formula",
    # style/test
    "style: format code with black",
    "style: fix import ordering with isort",
    "test: add biomarker validation edge cases",
    "test: add nutrient calculation regression tests",
]

# 메시지 가중치 (2023: research/docs 위주, feat 중간, chore 약간)
MSG_WEIGHTS = (
    [14] * 14 +   # research x14
    [13] * 14 +   # docs x14
    [8]  * 10 +   # feat x10
    [6]  * 10 +   # chore x10
    [4]  * 4  +   # refactor x4
    [3]  * 4  +   # fix x4
    [2]  * 4      # style/test x4
)

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
        elif action == 3:
            if lines and lines[-1] != "":
                lines.append("")
        else:
            lines = [l.rstrip() for l in lines]
    elif suffix in (".ts", ".tsx"):
        comments = [f"// Updated: {date_str}", "// TODO: expand this", f"// NOTE: {date_str}"]
        if action <= 1:
            lines.append(random.choice(comments))
        elif action <= 3:
            lines = [l.rstrip() for l in lines]
        else:
            if lines and lines[-1] != "":
                lines.append("")
    elif suffix == ".md":
        if action <= 1:
            lines.append(f"<!-- reviewed: {date_str} -->")
        elif action <= 3:
            lines = [l.rstrip() for l in lines]
        else:
            if lines and lines[-1] != "":
                lines.append("")
    try:
        f.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        return False
    return True

def create_note(date_str: str) -> Path:
    y, m, d = date_str.split("-")
    templates = [
        (f"docs/notes/{date_str}.md",
         f"# Research Notes — {date_str}\n\n- Reviewed literature on personalized nutrition\n- Explored privacy-preserving ML options\n"),
        (f"docs/adr/adr-{y}{m}{d}.md",
         f"# ADR: {date_str}\n\n## Context\nEarly-stage architectural decision.\n\n## Decision\nTBD — further research needed.\n"),
        (f"scripts/utils/helper_{y}{m}.py",
         f'"""Utility helpers drafted for {y}-{m}."""\n\n\ndef placeholder():\n    """Placeholder for future implementation."""\n    pass\n'),
    ]
    rel, content = random.choice(templates)
    p = REPO / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        with open(p, "a") as fh:
            fh.write(f"\n# {date_str} update\n")
    else:
        p.write_text(content)
    return p

def git(*args):
    subprocess.run(["git"] + list(args), capture_output=True, text=True)

def commit(date_str: str, hour: int, minute: int, second: int, message: str):
    ts = f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}"
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = ts
    env["GIT_COMMITTER_DATE"] = ts
    subprocess.run(
        ["git", "commit", "-m", message, "--quiet", "--allow-empty"],
        env=env, capture_output=True, text=True,
    )

# 2021 스타일 커밋 수 분포: 1(60%), 2(30%), 3(10%)
COMMIT_COUNTS  = [1, 2, 3]
COMMIT_WEIGHTS = [60, 30, 10]

start = datetime(2023, 1, 1)
end   = datetime(2023, 12, 31)

total_commits = 0
current = start

print("🌱 Starting 2023 contribution generation (2021-style natural pattern)...\n")

while current <= end:
    ds = current.strftime("%Y-%m-%d")
    is_weekend = current.weekday() >= 5

    # 2021 스타일: 평일 42%, 주말 20%
    prob = 20 if is_weekend else 42

    if ds not in existing and random.randint(1, 100) <= prob:
        num = random.choices(COMMIT_COUNTS, weights=COMMIT_WEIGHTS, k=1)[0]

        for _ in range(num):
            # 2021 스타일 시간대: 오후/저녁 위주
            hour_pool = (
                list(range(13, 18)) * 3 +
                list(range(19, 23)) * 2 +
                list(range(10, 13)) * 1
            )
            hour   = random.choice(hour_pool)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            msg    = random.choices(MSGS, weights=MSG_WEIGHTS, k=1)[0]

            modified = False
            if ALL_FILES and random.random() < 0.65:
                f = random.choice(ALL_FILES)
                if modify_file(f, ds):
                    git("add", str(f))
                    modified = True

            if not modified:
                nf = create_note(ds)
                git("add", str(nf))

            commit(ds, hour, minute, second, msg)
            total_commits += 1

    current += timedelta(days=1)

active_days = len(set(
    d for d in
    subprocess.check_output(["git", "log", "--format=%ad", "--date=short"], text=True)
    .strip().split("\n")
    if d.startswith("2023-")
))

print(f"✅ Done! {total_commits} commits created")
print(f"📅 2023 total active days: {active_days}")
