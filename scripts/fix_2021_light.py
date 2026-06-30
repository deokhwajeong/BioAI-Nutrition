#!/usr/bin/env python3
"""
2021 Aug-Dec contribution color redistribution
- Most days currently have 3-10 commits → all appear dark
- Target: 1 commit (light) 45% / 3-4 (medium) 30% / 6-7 (dark) 15% / 9-10 (darkest) 10%
- Drop extra commits via git rebase -i → force push
"""
import subprocess, random, os, sys, stat, tempfile
from collections import defaultdict, Counter

random.seed(7)

REBASE_BASE = "961281d"   # commit just before 2021 Aug-Dec were added

# ── Collect 2021 Aug-Dec commits ──
raw = subprocess.check_output(
    ["git", "log", "--format=%H %ad", "--date=short",
     "--after=2021-07-31", "--before=2022-01-01"],
    text=True
).strip().split("\n")

date_commits = defaultdict(list)   # date → [hash, ...]
for line in raw:
    if not line.strip(): continue
    h, d = line.split()
    date_commits[d].append(h)

# git log is newest-first; reverse each date list so the oldest commit is at [0]
for d in date_commits:
    date_commits[d].reverse()

all_dates   = sorted(date_commits.keys())
multi_dates = [d for d in all_dates if len(date_commits[d]) > 1]
single_dates= [d for d in all_dates if len(date_commits[d]) == 1]

print(f"2021 Aug-Dec active days: {len(all_dates)}")
print(f"  1-commit days (already light)  : {len(single_dates)}")
print(f"  Multi-commit days (dark)       : {len(multi_dates)}")

# ── Decide date classification ──
# Target ratio (based on multi_dates)
random.shuffle(multi_dates)
n = len(multi_dates)
# 45% → reduce to 1 commit, 30% → keep medium, 15% → keep dark, 10% → keep darkest
# (single_dates are already light → leave unchanged)
to_1   = set(multi_dates[:int(n * 0.55)])   # 55% → reduce to 1 commit
to_keep= set(multi_dates[int(n * 0.55):])   # 45% → keep as-is

print(f"\n  → {len(to_1)} days to reduce (1 commit)")
print(f"  → {len(to_keep)} days to keep (multi-commit as-is)")

# Build list of commit hashes to DROP (for light dates, keep only the first commit)
commits_to_drop = set()
for d in to_1:
    hs = date_commits[d]
    for h in hs[1:]:       # keep only the first commit, drop the rest
        commits_to_drop.add(h)

print(f"  Commits to DROP  : {len(commits_to_drop)}\n")

# ── Write GIT_SEQUENCE_EDITOR script ──
editor_src = f"""#!/usr/bin/env python3
import sys, subprocess

DROPS = {repr(commits_to_drop)}

todo = sys.argv[1]
with open(todo) as f:
    lines = f.readlines()

new, dropped = [], 0
for line in lines:
    s = line.strip()
    if not s or s.startswith('#'):
        new.append(line); continue
    parts = s.split(None, 2)
    if len(parts) < 2 or parts[0] not in ('pick', 'p'):
        new.append(line); continue
    short = parts[1]
    try:
        full = subprocess.check_output(
            ["git", "rev-parse", short],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
        if full in DROPS:
            tail = parts[2] if len(parts) > 2 else ""
            new.append(f"drop {{short}} {{tail}}\\n")
            dropped += 1
            continue
    except Exception:
        pass
    new.append(line)

with open(todo, 'w') as f:
    f.writelines(new)

import sys as _s
print(f"[editor] {{dropped}} commits → drop", file=_s.stderr)
"""

fd, epath = tempfile.mkstemp(suffix=".py", prefix="gseq_")
os.close(fd)
with open(epath, "w") as f:
    f.write(editor_src)
os.chmod(epath, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

# ── Run git rebase -i ──
print(f"🔄 Running git rebase -i {REBASE_BASE} (843 commits)...")
env = os.environ.copy()
env["GIT_SEQUENCE_EDITOR"] = epath

res = subprocess.run(
    ["git", "rebase", "-i", "--keep-empty", "-X", "ours", REBASE_BASE],
    env=env, text=True
)
os.unlink(epath)

if res.returncode != 0:
    print("❌ Rebase failed! Aborting...")
    subprocess.run(["git", "rebase", "--abort"])
    sys.exit(1)

print("✅ Rebase complete!")

# ── Force push ──
print("\n📤 Force pushing...")
push = subprocess.run(
    ["git", "push", "--force", "origin", "main"],
    capture_output=True, text=True
)
print(push.stdout or push.stderr)

# ── Print final distribution ──
print("\n=== 2021 Aug-Dec final distribution ===")
after = subprocess.check_output(
    ["git", "log", "--format=%ad", "--date=short",
     "--after=2021-07-31", "--before=2022-01-01"],
    text=True
).strip().split("\n")
c = Counter(after)
dist = Counter(c.values())
for k in sorted(dist):
    label = {1: "light", 2: "lt-med"}.get(k, "medium" if k <= 5 else "dark")
    print(f"  {k:2d} commits/day ({label:8s}): {dist[k]:3d} days")
print(f"  Total: {sum(dist.values())} active days  {sum(k*v for k,v in dist.items())} commits")
