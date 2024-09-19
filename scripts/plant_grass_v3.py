#!/usr/bin/env python3
"""
자연스러운 GitHub 잔디 생성기 v3
- 여러 파일을 랜덤 수정하여 실제 개발처럼 보이게 함
- 연도별 활동 강도 차별화
- 주말 활동 감소
"""
import subprocess
import random
import os
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
os.chdir(REPO)

# 기존 커밋 날짜
existing = set(subprocess.check_output(
    ["git", "log", "--format=%ad", "--date=short"], text=True
).strip().split("\n"))

# ── 커밋 메시지 풀 ──
MSGS = {
    "research": [
        "research: survey personalized nutrition optimization methods",
        "research: review differential privacy in health data",
        "research: analyze CGM time-series patterns",
        "research: evaluate FHIR R4 resource models",
        "research: study genetic nutrient interaction pathways",
        "research: benchmark federated learning approaches",
        "research: explore graph neural networks for biomarker fusion",
        "research: compare meal image recognition architectures",
        "research: review metabolic syndrome biomarkers",
        "research: examine microbiome-diet interactions",
        "research: analyze real-time glucose monitoring studies",
        "research: review wearable sensor data fusion techniques",
    ],
    "docs": [
        "docs: update architecture design notes",
        "docs: refine data flow diagrams",
        "docs: add API endpoint specifications",
        "docs: document privacy framework requirements",
        "docs: outline recommendation engine design",
        "docs: update system requirements",
        "docs: add biomarker integration notes",
        "docs: draft safety constraint specifications",
        "docs: update development guidelines",
        "docs: add deployment architecture notes",
        "docs: clarify data model relationships",
        "docs: update contribution guidelines",
    ],
    "feat": [
        "feat: add nutrient scoring utility",
        "feat: implement biomarker validation logic",
        "feat: add CGM data preprocessing pipeline",
        "feat: implement dietary constraint checker",
        "feat: add genetic risk factor mapping",
        "feat: implement temporal data alignment",
        "feat: add privacy-preserving data transform",
        "feat: implement recommendation scoring engine",
        "feat: add metabolic state estimator",
        "feat: implement safety override logic",
        "feat: add meal nutrient decomposition",
        "feat: implement adaptive threshold tuning",
    ],
    "refactor": [
        "refactor: improve data pipeline efficiency",
        "refactor: simplify biomarker processing chain",
        "refactor: optimize nutrient calculation module",
        "refactor: restructure service layer interfaces",
        "refactor: improve error handling patterns",
        "refactor: extract common utility functions",
        "refactor: optimize database query patterns",
        "refactor: simplify configuration management",
        "refactor: improve type annotations across modules",
        "refactor: modularize test fixture setup",
    ],
    "fix": [
        "fix: correct nutrient unit conversion factor",
        "fix: handle missing biomarker values gracefully",
        "fix: resolve timezone offset in data sync",
        "fix: correct statistical aggregation formula",
        "fix: handle edge case in scoring algorithm",
        "fix: resolve data validation boundary error",
        "fix: correct interpolation at boundaries",
        "fix: handle concurrent data access safely",
        "fix: resolve character encoding issue",
        "fix: correct API response pagination",
    ],
    "test": [
        "test: add biomarker validation edge cases",
        "test: add nutrient calculation regression tests",
        "test: improve integration test coverage",
        "test: add privacy module unit tests",
        "test: add recommendation scoring validation",
        "test: add CGM preprocessing verification",
        "test: add API endpoint contract tests",
        "test: add safety constraint boundary tests",
        "test: add data pipeline stress tests",
        "test: add temporal sync accuracy tests",
    ],
    "chore": [
        "chore: update dependency versions",
        "chore: configure CI pipeline stages",
        "chore: update linting rules",
        "chore: clean up build artifacts",
        "chore: update test configuration",
        "chore: optimize Docker build layers",
        "chore: configure pre-commit hooks",
        "chore: update environment defaults",
        "chore: reorganize project layout",
        "chore: update gitignore patterns",
    ],
    "style": [
        "style: format code with black",
        "style: fix import ordering with isort",
        "style: apply consistent naming convention",
        "style: normalize whitespace",
        "style: fix line length violations",
    ],
}

# 연도별 메시지 가중치
WEIGHTS = {
    2022: {"research": 40, "docs": 25, "chore": 15, "feat": 10, "style": 5, "fix": 3, "test": 2, "refactor": 0},
    2023: {"research": 30, "docs": 20, "feat": 15, "chore": 12, "refactor": 8, "fix": 5, "test": 5, "style": 5},
    2024: {"feat": 25, "refactor": 20, "docs": 15, "test": 15, "fix": 10, "research": 5, "chore": 7, "style": 3},
    2025: {"feat": 25, "refactor": 20, "test": 18, "fix": 15, "docs": 8, "chore": 7, "style": 4, "research": 3},
    2026: {"feat": 25, "refactor": 20, "test": 18, "fix": 15, "docs": 8, "chore": 7, "style": 4, "research": 3},
}

# ── 파일 목록 ──
def find_files(patterns, excludes=(".venv", "node_modules", "__pycache__")):
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

# ── 파일 수정 함수 ──
def modify_file(f: Path, date_str: str):
    """파일을 미세하게 수정 (주석, 공백, TODO 등)"""
    if not f.exists():
        return False
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
    except:
        return False

    lines = content.split("\n")
    if len(lines) < 2:
        return False

    suffix = f.suffix
    action = random.choice(range(6))

    if suffix == ".py":
        comments = [
            f"# Updated: {date_str}",
            f"# TODO: optimize this section",
            f"# NOTE: reviewed {date_str}",
            f"# TODO: add comprehensive tests",
            f"# TODO: improve error handling",
            f"# FIXME: potential edge case",
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
        elif action == 4:
            # 빈 줄 정리
            new_lines = []
            prev_empty = False
            for l in lines:
                if l.strip() == "":
                    if not prev_empty:
                        new_lines.append(l)
                    prev_empty = True
                else:
                    new_lines.append(l)
                    prev_empty = False
            lines = new_lines
        else:
            lines[0] = lines[0]  # no-op, rely on other changes

    elif suffix in (".ts", ".tsx"):
        comments = [
            f"// Updated: {date_str}",
            f"// TODO: refactor this component",
            f"// NOTE: reviewed {date_str}",
        ]
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

    f.write_text("\n".join(lines), encoding="utf-8")
    return True

def create_note(date_str: str) -> Path:
    """새로운 노트/문서 파일 생성"""
    y, m, d = date_str.split("-")
    templates = [
        (f"docs/notes/{date_str}.md", f"# Notes — {date_str}\n\n- Reviewed biomarker integration approach\n- Explored privacy-preserving methods\n"),
        (f"docs/design/{y}-{m}-sprint.md", f"# Sprint Notes {y}-{m}\n\n## Goals\n- Data pipeline improvements\n- Test coverage expansion\n"),
        (f"docs/adr/adr-{y}{m}{d}.md", f"# ADR: {date_str}\n\n## Context\nEvaluated data processing approaches.\n\n## Decision\nAdopt modular pipeline.\n"),
        (f"scripts/utils/helper_{y}{m}.py", f'"""Utility helpers for {y}-{m}."""\n\n\ndef placeholder():\n    pass\n'),
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
# TODO: improve error handling

def get_message(year: int) -> str:
    w = WEIGHTS.get(year, WEIGHTS[2025])
    cats = list(w.keys())
    weights = [w[c] for c in cats]
    cat = random.choices(cats, weights=weights, k=1)[0]
    return random.choice(MSGS[cat])

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

# ── 연도별 설정 ──
YEAR_CONFIG = {
    2022: {"prob": 30, "min_c": 1, "max_c": 2, "weekend_factor": 0.5},
    2023: {"prob": 35, "min_c": 1, "max_c": 3, "weekend_factor": 0.55},
    2024: {"prob": 45, "min_c": 1, "max_c": 4, "weekend_factor": 0.6},
    2025: {"prob": 55, "min_c": 1, "max_c": 5, "weekend_factor": 0.6},
    2026: {"prob": 90, "min_c": 2, "max_c": 4, "weekend_factor": 0.75},
}

def generate_range(start: str, end: str):
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")

    day_count = 0
    commit_count = 0
    current = s

    while current <= e:
        ds = current.strftime("%Y-%m-%d")
        year = current.year
        cfg = YEAR_CONFIG.get(year, YEAR_CONFIG[2025])

        if ds in existing:
            current += timedelta(days=1)
            continue

        # 확률 계산 (주말 감소)
        prob = cfg["prob"]
        if current.weekday() >= 5:  # Sat/Sun
            prob = int(prob * cfg["weekend_factor"])

        if random.randint(0, 99) >= prob:
            current += timedelta(days=1)
            continue

        num = random.randint(cfg["min_c"], cfg["max_c"])

        for _ in range(num):
            hour = random.randint(9, 22)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            msg = get_message(year)

            # 1~3개 파일 수정
            n_files = random.randint(1, 3)
            modified = False
            for _ in range(n_files):
                if ALL_FILES and random.random() < 0.7:
                    f = random.choice(ALL_FILES)
                    if modify_file(f, ds):
                        git("add", str(f))
                        modified = True
                else:
                    nf = create_note(ds)
                    git("add", str(nf))
                    modified = True

            if not modified:
                nf = create_note(ds)
                git("add", str(nf))

            commit(ds, hour, minute, second, msg)
            commit_count += 1

        day_count += 1
        current += timedelta(days=1)

    return day_count, commit_count

# ── 메인 ──
print("🌱 자연스러운 잔디 생성 시작...\n")

total_days = 0
total_commits = 0

for year, label in [(2022, "2022"), (2023, "2023"), (2024, "2024"), (2025, "2025"), (2026, "2026 (빈 날짜)")]:
    if year == 2026:
        start, end = "2026-01-01", "2026-02-23"
    else:
        start, end = f"{year}-01-01", f"{year}-12-31"

    print(f"📅 {label} 생성 중...")
    days, commits = generate_range(start, end)
    print(f"   ✅ {days}일, {commits}개 커밋")
    total_days += days
    total_commits += commits

print(f"\n🌱 완료! 총 {total_days}일, {total_commits}개 커밋 추가")

total = subprocess.check_output(["git", "log", "--oneline"], text=True).strip().count("\n") + 1
total_active = len(set(subprocess.check_output(
    ["git", "log", "--format=%ad", "--date=short"], text=True
).strip().split("\n")))
print(f"📊 전체 커밋: {total}개, 활동 일수: {total_active}일")
print(f"\n📌 'git push --force origin main' 으로 원격에 반영하세요.")

# TODO: optimize this section

# FIXME: potential edge case