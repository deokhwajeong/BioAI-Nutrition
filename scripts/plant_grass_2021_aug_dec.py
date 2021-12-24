#!/usr/bin/env python3
"""
2021년 8~12월 GitHub 잔디 생성 — 프로젝트 초기 탐색 단계
- 평일 ~42%, 주말 ~20% 확률
- 하루 1~3개 커밋 (1개 위주)
- research / docs / chore 중심의 초기 단계 메시지
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

# 2021년 초기 단계 — 리서치·기획 중심 메시지
MSGS = [
    # research
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
    "research: investigate genetic variant impact on nutrient metabolism",
    "research: explore transformer architectures for health time-series",
    "research: survey meal image recognition state-of-the-art",
    "research: review differential privacy frameworks",
    # docs / planning
    "docs: draft initial project vision and scope",
    "docs: outline core system architecture concepts",
    "docs: sketch data ingestion pipeline design",
    "docs: define preliminary biomarker feature set",
    "docs: draft privacy and consent framework outline",
    "docs: add initial ADR for data storage strategy",
    "docs: note key findings from literature review",
    "docs: outline recommendation engine requirements",
    "docs: draft data model concepts for nutrient tracking",
    "docs: add research notes on CGM integration",
    "docs: document regulatory considerations for health AI",
    # chore / init
    "chore: initialize repository structure",
    "chore: set up initial project configuration",
    "chore: add base development environment setup",
    "chore: configure initial linting and formatting rules",
    "chore: prototype data ingestion proof-of-concept",
    "chore: evaluate candidate database technologies",
    "chore: set up basic CI skeleton",
    "chore: add initial dependency manifest",
    "chore: organize research reference materials",
    "chore: bootstrap backend service skeleton",
    # feat (initial spikes)
    "feat: add initial data schema draft",
    "feat: prototype nutrient lookup utility",
    "feat: sketch biomarker ingestion interface",
    "feat: add basic FHIR resource parser stub",
    "feat: implement simple CGM data loader prototype",
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
        with open(p, "a") as f:
            f.write(f"\n# {date_str} update\n")
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

# 커밋 수 분포: 1개(60%), 2개(30%), 3개(10%) — 초기 단계라 가볍게
COMMIT_COUNTS  = [1, 2, 3]
COMMIT_WEIGHTS = [60, 30, 10]

start = datetime(2021, 8, 1)
end   = datetime(2021, 12, 31)

total_commits = 0
current = start

print("🌱 2021년 8~12월 잔디 심기 시작 (프로젝트 초기 단계)...\n")

while current <= end:
    ds = current.strftime("%Y-%m-%d")
    is_weekend = current.weekday() >= 5
    prob = 20 if is_weekend else 42

    if ds not in existing and random.randint(1, 100) <= prob:
        num = random.choices(COMMIT_COUNTS, weights=COMMIT_WEIGHTS, k=1)[0]

        for _ in range(num):
            # 초기 단계: 주로 오후~저녁 (점심 이후 리서치 패턴)
            hour_pool = (
                list(range(13, 18)) * 3 +
                list(range(19, 23)) * 2 +
                list(range(10, 13)) * 1
            )
            hour   = random.choice(hour_pool)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            msg    = random.choice(MSGS)

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
    if "2021-" in d and any(f"2021-{m:02d}" in d for m in range(8, 13))
))

print(f"✅ 완료! 커밋 {total_commits}개 생성, 활성 일수 {active_days}일 (8~12월 기준)")
