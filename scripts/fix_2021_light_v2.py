#!/usr/bin/env python3
"""
2021 Aug-Dec contribution color redistribution v2
- Auto-resolve DROP conflicts with --theirs and retry rebase --continue
- Target: 1 commit (light) ~50% / 3-5 (medium) ~25% / 6-7 (dark) ~15% / 9-10 (darkest) ~10%
"""
import subprocess, random, os, sys, stat, tempfile
from collections import defaultdict, Counter

random.seed(13)
REBASE_BASE = "961281d"

# ── Collect 2021 Aug-Dec commits (oldest first in DAG) ──
raw = subprocess.check_output(
    ["git", "log", "--format=%H %ad", "--date=short",
     "--after=2021-07-31", "--before=2022-01-01", "--reverse"],
    text=True
).strip().split("\n")

date_commits = defaultdict(list)  # date → [oldest, ..., newest]
for line in raw:
    if not line.strip(): continue
    h, d = line.split()
    date_commits[d].append(h)

all_dates    = sorted(date_commits.keys())
multi_dates  = [d for d in all_dates if len(date_commits[d]) > 1]
single_dates = [d for d in all_dates if len(date_commits[d]) == 1]

print(f"2021 Aug-Dec active days: {len(all_dates)}")
print(f"  1-commit days (already light): {len(single_dates)}")
print(f"  Multi-commit days (dark)     : {len(multi_dates)}")

# ── Classify dates ──
random.shuffle(multi_dates)
n = len(multi_dates)
to_light = set(multi_dates[:int(n * 0.55)])   # 55% → reduce to 1 commit
to_keep  = set(multi_dates[int(n * 0.55):])   # 45% → keep multi-commit

print(f"\n  → {len(to_light)} days to reduce (1 commit)")
print(f"  → {len(to_keep)} days to keep (multi-commit)")

# ── Determine commits to DROP ──
# For each 'light' date, keep only the first (oldest) commit, drop the rest
commits_to_drop = set()
for d in to_light:
    hs = date_commits[d]  # oldest first
    for h in hs[1:]:
        commits_to_drop.add(h)

print(f"\nCommits to DROP: {len(commits_to_drop)}")

# short→full reverse mapping (used in GIT_SEQUENCE_EDITOR)
short_to_full = {}
for h in commits_to_drop:
    for l in (7, 8, 9, 10):
        short_to_full[h[:l]] = h

# ── GIT_SEQUENCE_EDITOR script ──
editor_src = f"""#!/usr/bin/env python3
import sys, subprocess
DROPS = {repr(commits_to_drop)}
SHORT_MAP = {repr(short_to_full)}

def resolve(short):
    if short in SHORT_MAP:
        return SHORT_MAP[short]
    try:
        return subprocess.check_output(
            ["git","rev-parse",short], text=True,
            stderr=subprocess.DEVNULL).strip()
    except: return None

todo = sys.argv[1]
with open(todo) as f: lines = f.readlines()

out, dropped = [], 0
for line in lines:
    s = line.strip()
    if not s or s.startswith('#'):
        out.append(line); continue
    parts = s.split(None, 2)
    if len(parts) < 2 or parts[0] not in ('pick','p'):
        out.append(line); continue
    full = resolve(parts[1])
    if full and full in DROPS:
        tail = parts[2] if len(parts)>2 else ""
        out.append(f"drop {{parts[1]}} {{tail}}\\n")
        dropped += 1
    else:
        out.append(line)

with open(todo,'w') as f: f.writelines(out)
import sys as s
print(f"[editor] {{dropped}} → drop", file=s.stderr)
"""

fd, epath = tempfile.mkstemp(suffix=".py", prefix="gseq_")
os.close(fd)
with open(epath, "w") as f: f.write(editor_src)
os.chmod(epath, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

# ── Run rebase + auto conflict-resolution loop ──
print(f"\n🔄 Starting git rebase -i {REBASE_BASE} (843 commits)...")

env = os.environ.copy()
env["GIT_SEQUENCE_EDITOR"] = epath
env["GIT_EDITOR"] = "true"        # prevent interactive commit message editor

res = subprocess.run(
    ["git", "rebase", "-i", "--keep-empty", REBASE_BASE],
    env=env, text=True
)
os.unlink(epath)

def auto_resolve():
    """Auto-resolve conflict files with --theirs, then run rebase --continue"""
    # Get list of conflicted files
    conflicted = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        text=True
    ).strip().split("\n")
    conflicted = [c for c in conflicted if c.strip()]

    if not conflicted:
        # No conflicts but there may be untracked/modified files
        subprocess.run(["git", "add", "-u"], capture_output=True)
    else:
        for f in conflicted:
            r = subprocess.run(["git", "checkout", "--theirs", f],
                               capture_output=True, text=True)
            if r.returncode == 0:
                subprocess.run(["git", "add", f], capture_output=True)
            else:
                # File absent in 'theirs' → remove it
                subprocess.run(["git", "rm", "-f", f], capture_output=True)

    return subprocess.run(
        ["git", "rebase", "--continue"],
        env={**os.environ, "GIT_EDITOR": "true"},
        capture_output=True, text=True
    ).returncode

if res.returncode != 0:
    print("⚠️  Conflicts detected → starting auto-resolution loop...")
    resolved = 0
    for attempt in range(300):
        status = subprocess.check_output(
            ["git", "status", "--short"], text=True
        )
        # Check if rebase is complete
        rebase_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], text=True
        ).strip()
        import pathlib
        if not (pathlib.Path(rebase_dir) / "rebase-merge").exists() and \
           not (pathlib.Path(rebase_dir) / "rebase-apply").exists():
            print(f"  ✅ Completed automatically ({attempt} conflicts resolved)")
            break
        rc = auto_resolve()
        resolved += 1
        if rc == 0:
            print(f"  ✅ Rebase complete ({resolved} conflicts resolved)")
            break
        if attempt % 20 == 0:
            print(f"  ... attempt {attempt} in progress...")
    else:
        print("❌ Max attempts exceeded, aborting")
        subprocess.run(["git", "rebase", "--abort"])
        sys.exit(1)
else:
    print("✅ Rebase complete with no conflicts!")

# ── force push ──
print("\n📤 Force pushing...")
push = subprocess.run(
    ["git", "push", "--force", "origin", "main"],
    capture_output=True, text=True
)
print((push.stdout + push.stderr).strip())

# ── Verify final distribution ──
print("\n=== 2021 Aug-Dec final distribution ===")
after = subprocess.check_output(
    ["git", "log", "--format=%ad", "--date=short",
     "--after=2021-07-31", "--before=2022-01-01"],
    text=True
).strip().split("\n")
c = Counter(after)
dist = Counter(c.values())
for k in sorted(dist):
    bar = "█" * min(k, 10)
    tag = "light" if k == 1 else ("medium" if k <= 5 else ("dark" if k <= 7 else "darkest"))
    print(f"  {k:2d} commits/day [{tag:7s}] {bar:10s} {dist[k]:3d} days")
total_active = sum(dist.values())
total_commits = sum(k*v for k,v in dist.items())
print(f"\n  Active: {total_active} days / Total: {total_commits} commits")
