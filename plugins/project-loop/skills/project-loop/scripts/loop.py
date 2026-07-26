#!/usr/bin/env python3
"""
Project Loop state machine and deterministic gate checks.

Everything here is intentionally mechanical. Checks that a script can assert should never
cost model tokens, and a script asserts them more reliably.

Python 3.8+, standard library only, no network access.

  loop.py init [--brownfield]      scaffold loop-project/
  loop.py status                   compact state summary (run this first, every session)
  loop.py task new "<title>"       create the next TASK card
  loop.py task list                list tasks and their state
  loop.py reuse "currency format"  search registry + tree BEFORE building anything new
  loop.py verify TASK-007          run the deterministic REPORT, scope, integrity + craft checks
  loop.py cycle TASK-007           record a rework cycle, evaluate stop conditions
  loop.py gate g1 --check          run a gate's mechanical checks
  loop.py gate g1 --pass           advance the loop past a gate
  loop.py block "<reason>"         set status BLOCKED and write to the ledger

Exit codes: 0 pass, 1 fail (checks did not clear), 2 usage or state error.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

LOOP_DIR = "loop-project"
STATE_FILE = os.path.join(LOOP_DIR, "loop.json")
LEDGER = os.path.join(LOOP_DIR, "ledger.md")

PHASES = ["0-plan", "1-spec", "2-build", "3-verify"]
GATES = ["g0", "g1", "g2", "g3"]

REPORT_SECTIONS = [
    "Summary",
    "Files changed",
    "Commands run",
    "Reuse",
    "Acceptance",
    "Assumptions",
    "Risks",
    "Blocked",
]

MAX_CYCLES_PER_TASK = 5
MAX_REPEAT_FINDING = 3

CONVENTIONS = os.path.join(LOOP_DIR, "1-spec/conventions.md")

# Reusable units that must be registered in conventions.md when created.
REUSABLE_HINTS = ("component", "hook", "util", "helper", "lib", "service", "guard",
                  "middleware", "shared", "common", "ui/")

# Slop that a script can see. Kept tight on purpose — a noisy check gets ignored,
# and an ignored check is worse than no check.
SLOP_PATTERNS = [
    (r"catch\s*\([^)]*\)\s*\{\s*\}", "empty catch block"),
    (r"except[^\n:]*:\s*\n\s*pass\b", "bare except: pass"),
    (r"\bas\s+any\b|:\s*any\b", "any type escape hatch"),
    (r"@ts-ignore|#\s*type:\s*ignore|// eslint-disable-next-line(?!.*\S)", "suppressed check"),
    (r"\bconsole\.log\(|\bprint\(|\bdbg!\(", "debug output left in source"),
    (r"\b(TODO|FIXME|XXX|HACK)\b", "TODO introduced by this task"),
    (r"\b\w*(utils?|helpers?|manager|handler|misc|stuff)\d+\b", "placeholder-grade name", re.I),
    (r"\b(New|Old|Final|Copy|Updated)[A-Z]\w+|\b\w+(Final|Copy|V2|_v2|Old)\b", "versioned name"),
]
SLOP_PATTERNS = [(p[0], p[1], p[2] if len(p) > 2 else 0) for p in SLOP_PATTERNS]

# Names that carry no information. Whole-basename match only.
WEAK_BASENAMES = {"utils", "util", "helpers", "helper", "misc", "common", "stuff",
                  "data", "temp", "tmp", "manager", "handler", "index2", "new"}

NAME_NOISE = re.compile(r"(new|old|final|copy|updated|v\d+|\d+)", re.IGNORECASE)

TEST_PATH_HINTS = ("test", "spec", "__tests__", "e2e", "cypress", "playwright")

SKIP_MARKERS = [
    r"\bit\.skip\b", r"\bdescribe\.skip\b", r"\btest\.skip\b",
    r"\bit\.only\b", r"\bdescribe\.only\b", r"\btest\.only\b",
    r"\bxit\b", r"\bxdescribe\b",
    r"@pytest\.mark\.skip", r"@pytest\.mark\.xfail", r"\bpytest\.skip\(",
    r"@Disabled\b", r"@Ignore\b", r"#\[ignore\]",
    r"\bt\.Skip\(",
]

SECRET_PATTERNS = [
    (r"(?i)\b(aws_secret_access_key|aws_access_key_id)\b\s*[:=]\s*\S+", "aws credential"),
    (r"\bAKIA[0-9A-Z]{16}\b", "aws access key id"),
    (r"(?i)\b(api[_-]?key|secret[_-]?key|client[_-]?secret|private[_-]?key)\b\s*[:=]\s*['\"][^'\"]{12,}", "hardcoded secret"),
    (r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "private key block"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "provider token"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "github token"),
    (r"(?i)\bpassword\b\s*[:=]\s*['\"][^'\"]{6,}['\"]", "hardcoded password"),
]

PLACEHOLDER_HINTS = ("example", "changeme", "placeholder", "your-", "xxx", "dummy", "<", "test")


# --------------------------------------------------------------------------- helpers

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg, code=2):
    print("error: " + msg, file=sys.stderr)
    sys.exit(code)


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        return json.loads(read(STATE_FILE))
    except json.JSONDecodeError as e:
        die("%s is not valid JSON (%s). Fix it by hand; the loop will not guess." % (STATE_FILE, e))


def save_state(state):
    state["updated"] = now()
    write(STATE_FILE, json.dumps(state, indent=2) + "\n")


def require_state():
    state = load_state()
    if state is None:
        die("no loop found. Run: loop.py init")
    return state


def ledger(entry):
    line = "\n## %s\n%s\n" % (now(), entry.strip())
    if os.path.exists(LEDGER):
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        write(LEDGER, "# Loop ledger\n\nAppend-only. Decisions, deviations, escalations.\n" + line)


def git(*args):
    try:
        out = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=30)
        return out.returncode, out.stdout, out.stderr
    except (OSError, subprocess.SubprocessError):
        return 1, "", "git unavailable"


def has_git():
    return git("rev-parse", "--git-dir")[0] == 0


def sha256_of(path):
    if not os.path.exists(path):
        return None
    return hashlib.sha256(read(path).encode("utf-8")).hexdigest()


def is_test_path(path):
    low = path.lower()
    return any(h in low for h in TEST_PATH_HINTS)


class Result:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, note="", severity=""):
        self.rows.append((name, ok, note, severity))

    @property
    def failed(self):
        return [r for r in self.rows if not r[1]]

    def render(self, title):
        print("\n" + title)
        print("-" * len(title))
        for name, ok, note, sev in self.rows:
            mark = "PASS" if ok else "FAIL"
            sevs = (" [Sev-%s]" % sev) if sev and not ok else ""
            print("  %-4s  %-34s %s%s" % (mark, name, note, sevs))
        print("")
        if self.failed:
            print("%d of %d checks failed." % (len(self.failed), len(self.rows)))
        else:
            print("All %d checks passed." % len(self.rows))
        return 1 if self.failed else 0


# --------------------------------------------------------------------------- init

SEED = {
    "0-plan/research.md": "# Research\n\n## What exists\n\n## Hard constraints\n\n## Prior art\n\n## Decisions taken\n| Decision | Alternatives rejected | Why |\n|---|---|---|\n\n## Open questions\n",
    "0-plan/brd.md": "# Business requirements\n\n| ID | Outcome | For whom | Success measure | Cost of not doing it | Priority |\n|----|---------|----------|-----------------|----------------------|----------|\n| BR-001 | | | | | Must |\n\n## Won't do this cycle\n- \n",
    "0-plan/prd.md": "# Product specification\n\n## Functional requirements (EARS)\n\n| ID | Requirement | Pattern | Traces to |\n|----|-------------|---------|-----------|\n| FR-001 | When <trigger>, the system shall <response> | event-driven | BR-001 |\n\n## Unwanted behaviour\n\n| ID | Requirement | Traces to |\n|----|-------------|-----------|\n| FR-0xx | If <condition>, then the system shall <response> | BR-001 |\n\n## Non-functional requirements\n\n## Non-goals\n- \n",
    "0-plan/plan.md": "# Plan\n\n## Milestones\n| # | Demonstrable state | Target date | Closes |\n|---|--------------------|-------------|--------|\n| M1 | | | FR-001 |\n\n## Ownership boundaries\n| Area | Owner | Others may | Others must not |\n|------|-------|-----------|-----------------|\n",
    "0-plan/dod.md": "# Definition of Done\n\nFROZEN AT G0. Changes after G0 require a human decision recorded in ledger.md.\n\n## Project-level\n- [ ] All Must-have FR implemented and verified by a named test\n- [ ] Suite green; no skipped, disabled or weakened tests\n- [ ] Every blocking security rule satisfied\n- [ ] No open Sev-1 or Sev-2\n- [ ] Runs from a clean clone with documented commands\n- [ ] No secrets in the repository or its history\n- [ ] README covers install, run, test, deploy\n\n## Acceptance checklist\n| ID | Requirement | How it is proven | Evidence artifact |\n|----|-------------|------------------|-------------------|\n| AC-001 | FR-001: ... | | |\n",
    "1-spec/architecture.md": "# Architecture\n\n## Components\n| Component | Single responsibility | Owns |\n|-----------|----------------------|------|\n\n## Data flow and trust boundaries\n\n## Data model\n\n## Foundation build order\n1. \n\n## ADRs\n### ADR-001 <title>\nContext / Options / Decision / Consequences\n",
    "1-spec/interfaces.md": "# Interfaces\n\nThe only spec file most Workers read. Complete enough to build against without asking.\n\n## Module boundaries\n\n## API contracts\n### <METHOD> /path\nAuth: \nRequest: \nResponse: \nErrors: \n\n## Shared types\n\n## Events\n\n## Naming and file conventions\n",
    "1-spec/security.md": "# Security contract\n\nSelected from references/security-contract.md. Blocking rules only.\n\n| ID | Rule | Applies to | Check | Blocking |\n|----|------|-----------|-------|----------|\n\n## Threat notes\n\n## Accepted risks\n",
    "1-spec/qa-strategy.md": "# QA strategy\n\n## Layers\n| Layer | Covers | Tool |\n|-------|--------|------|\n\n## Coverage expectations by area\n\n## Acceptance mapping\n| AC | Test or procedure |\n|----|-------------------|\n\n## Commands\nFull suite: \nSingle file: \nSingle test: \n\n## What reproducible means here\n",
    "1-spec/conventions.md": "# Conventions, registry and bound decisions\n\nThe loop's memory. In every Worker's read-set, so keep it compact — tables, not prose.\n\n## 1. Conventions\nOnly decisions different Workers would otherwise make differently.\n\n| Concern | Decision |\n|---------|----------|\n| File and directory layout | |\n| Naming | |\n| Validation | |\n| Errors | |\n| Async | |\n| Dates | |\n| State | |\n| Tests | |\n| Imports | |\n\n## 2. Reuse registry\nAppend-only. One line per reusable unit, written the moment it is created.\n\n| Name | Path | Purpose | Created by | Used by |\n|------|------|---------|-----------|---------|\n\n## 3. Bound decisions\nConstraints on later tasks. Breaking one requires an amendment, not a local judgement call.\n\n| ID | Decision | Binds | Taken in |\n|----|----------|-------|----------|\n",
    "1-spec/design-contract.md": "# Design contract\n\nDelete this file if the project has no UI.\n\n## Tokens\n## Component inventory and required states\n## Accessibility bar\n## Responsive floor\n## Character (2-3 adjectives with consequences)\n## Anti-generic bans\n## Performance budget\n",
}


def cmd_init(args):
    if os.path.exists(STATE_FILE) and not args.force:
        die("a loop already exists here. Use --force to overwrite (this discards state).")

    for phase in PHASES:
        os.makedirs(os.path.join(LOOP_DIR, phase), exist_ok=True)
    for sub in ("2-build/tasks", "2-build/reports", "3-verify/qa", "3-verify/verdicts", "3-verify/rework"):
        os.makedirs(os.path.join(LOOP_DIR, sub), exist_ok=True)

    for rel, body in SEED.items():
        path = os.path.join(LOOP_DIR, rel)
        if not os.path.exists(path):
            write(path, body)

    state = {
        "version": 1,
        "created": now(),
        "updated": now(),
        "phase": 0,
        "status": "ACTIVE",
        "cursor": "0.1 research",
        "brownfield": bool(args.brownfield),
        "human_gates": ["g0"],
        "gates": {g: {"passed": False, "at": None} for g in GATES},
        "dod_hash": None,
        "tasks": {},
        "blocked_reason": None,
    }
    save_state(state)
    ledger("Loop initialised (%s)." % ("brownfield" if args.brownfield else "greenfield"))

    print("Initialised loop-project/")
    print("Phase 0. Next: research.md, then brd.md, prd.md, plan.md, dod.md.")
    if args.brownfield:
        print("Brownfield: survey the existing repo into 0-plan/research.md before writing requirements.")
    return 0


# --------------------------------------------------------------------------- status

def cmd_status(args):
    state = load_state()
    if state is None:
        print("no loop found")
        print("Run: loop.py init   (add --brownfield for an existing codebase)")
        return 0

    tasks = state.get("tasks", {})
    open_tasks = [t for t, v in tasks.items() if v.get("verdict") != "PASS"]

    print("phase:   %d (%s)" % (state["phase"], PHASES[state["phase"]]))
    print("status:  %s" % state["status"])
    print("cursor:  %s" % state.get("cursor", "-"))
    print("gates:   %s" % " ".join(
        "%s=%s" % (g, "pass" if state["gates"][g]["passed"] else "-") for g in GATES))
    print("tasks:   %d total, %d open" % (len(tasks), len(open_tasks)))

    if state["status"] == "BLOCKED":
        print("\nBLOCKED: %s" % state.get("blocked_reason", "see ledger.md"))
        print("Do not continue. Present the decision to the human and wait.")
        return 0

    if state["dod_hash"]:
        current = sha256_of(os.path.join(LOOP_DIR, "0-plan/dod.md"))
        if current != state["dod_hash"]:
            print("\nWARNING: dod.md changed after it was frozen at G0.")
            print("This is scope drift. Record a human decision in ledger.md or restore the file.")

    if open_tasks:
        print("\nopen tasks:")
        for t in sorted(open_tasks):
            v = tasks[t]
            print("  %-10s cycles=%d  verdict=%s  %s" % (
                t, v.get("cycles", 0), v.get("verdict", "-"), v.get("title", "")))
    return 0


# --------------------------------------------------------------------------- tasks

TASK_TEMPLATE = """# {tid} — {title}

## Scope
<what is being built, one paragraph>

Out of scope:
- 

## Read-set
- loop-project/2-build/tasks/{tid}.md
- loop-project/1-spec/interfaces.md
- loop-project/1-spec/security.md (relevant rules only)

## Write-set
- src/**

## Acceptance
| AC | Requirement | Proven by |
|----|-------------|-----------|
| AC-00x | FR-00x: ... | |

## Depends on
- none
"""


def next_id(directory, prefix):
    os.makedirs(directory, exist_ok=True)
    nums = []
    for name in os.listdir(directory):
        m = re.match(re.escape(prefix) + r"-(\d{3})", name)
        if m:
            nums.append(int(m.group(1)))
    return "%s-%03d" % (prefix, (max(nums) + 1) if nums else 1)


def cmd_task(args):
    state = require_state()
    tdir = os.path.join(LOOP_DIR, "2-build/tasks")

    if args.action == "list":
        tasks = state.get("tasks", {})
        if not tasks:
            print("no tasks yet")
            return 0
        for t in sorted(tasks):
            v = tasks[t]
            print("%-10s cycles=%d verdict=%-7s %s" % (
                t, v.get("cycles", 0), v.get("verdict", "-"), v.get("title", "")))
        return 0

    if args.action == "new":
        if not args.title:
            die('task new needs a title: loop.py task new "Session revocation"')
        tid = next_id(tdir, "TASK")
        write(os.path.join(tdir, tid + ".md"), TASK_TEMPLATE.format(tid=tid, title=args.title))
        state.setdefault("tasks", {})[tid] = {
            "title": args.title, "cycles": 0, "verdict": None, "findings": {}
        }
        save_state(state)
        print("created loop-project/2-build/tasks/%s.md" % tid)
        print("Fill in scope, read-set, write-set and acceptance before handing it to a Worker.")
        return 0

    die("unknown task action: %s" % args.action)


def parse_section(text, heading):
    """Return the body under '## <heading>' up to the next '## '."""
    pattern = r"^##\s+" + re.escape(heading) + r"\s*$"
    lines = text.splitlines()
    out, capturing = [], False
    for line in lines:
        if re.match(pattern, line.strip(), re.IGNORECASE):
            capturing = True
            continue
        if capturing and line.startswith("## "):
            break
        if capturing:
            out.append(line)
    return "\n".join(out).strip()


def parse_globs(section_body):
    globs = []
    for line in section_body.splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            item = line[2:].strip().split("#")[0].strip()
            item = item.split("(")[0].strip()
            if item and item.lower() != "none":
                globs.append(item)
    return globs


def matches_any(path, globs):
    norm = path.replace("\\", "/")
    for g in globs:
        g = g.replace("\\", "/")
        if fnmatch.fnmatch(norm, g):
            return True
        if g.endswith("/**") and norm.startswith(g[:-3].rstrip("/") + "/"):
            return True
        if g.endswith("/") and norm.startswith(g):
            return True
        if norm == g:
            return True
    return False


# --------------------------------------------------------------------------- verify

def changed_files():
    if not has_git():
        return None
    # --untracked-files=all matters: without it git collapses a new directory to one
    # entry, and every new file inside it becomes invisible to the checks below.
    code, out, _ = git("status", "--porcelain", "--untracked-files=all")
    if code != 0:
        return None
    files = []
    for line in out.splitlines():
        if len(line) > 3:
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ")[-1]
            files.append(path.strip('"'))
    return files


def diff_for(path):
    code, out, _ = git("diff", "--unified=0", "--", path)
    if code != 0 or not out:
        code, out, _ = git("diff", "--cached", "--unified=0", "--", path)
    return out


def check_test_tampering(files):
    findings = []
    test_files = [f for f in files if is_test_path(f)]
    for f in test_files:
        if not os.path.exists(f):
            findings.append("%s: test file deleted" % f)
            continue
        d = diff_for(f)
        if not d:
            continue
        added = [l[1:] for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in d.splitlines() if l.startswith("-") and not l.startswith("---")]
        for line in added:
            for pat in SKIP_MARKERS:
                if re.search(pat, line):
                    findings.append("%s: skip/only marker added -> %s" % (f, line.strip()[:70]))
                    break
        assert_re = re.compile(r"\b(expect|assert\w*|should)\s*[\(\.]")
        removed_asserts = sum(len(assert_re.findall(l)) for l in removed)
        added_asserts = sum(len(assert_re.findall(l)) for l in added)
        if removed_asserts > added_asserts:
            findings.append("%s: %d assertion line(s) removed, %d added"
                            % (f, removed_asserts, added_asserts))
    return findings


def check_secrets(files):
    findings = []
    for f in files:
        if not os.path.isfile(f):
            continue
        if any(seg in f for seg in ("loop-project/", "node_modules/", ".git/", "dist/", "build/")):
            continue
        try:
            if os.path.getsize(f) > 2_000_000:
                continue
            content = read(f)
        except OSError:
            continue
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, content):
                snippet = m.group(0)
                if any(h in snippet.lower() for h in PLACEHOLDER_HINTS):
                    continue
                line_no = content[:m.start()].count("\n") + 1
                findings.append("%s:%d %s" % (f, line_no, label))
                break
    return findings


def source_files(root="."):
    """Every plausible source file, excluding vendored and generated trees."""
    skip = {".git", "node_modules", "dist", "build", ".next", ".venv", "__pycache__",
            "vendor", "target", "loop-project", "coverage"}
    exts = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java", ".rb", ".php",
            ".svelte", ".vue", ".css", ".scss", ".sql", ".kt", ".swift"}
    out = []
    for base, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for n in names:
            if os.path.splitext(n)[1] in exts:
                out.append(os.path.relpath(os.path.join(base, n), root))
    return out


def normalise_name(path):
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = NAME_NOISE.sub("", stem)
    return re.sub(r"[^a-z]", "", stem.lower())


def normalise_content(text):
    text = re.sub(r"//.*|#.*|/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"['\"].*?['\"]", "S", text, flags=re.DOTALL)
    return re.sub(r"\s+", "", text).lower()


def check_duplication(new_files, all_files):
    """Near-duplicate names or bodies. This is what stops task 9 rebuilding task 4's work."""
    import difflib
    findings = []
    others = [f for f in all_files if f not in new_files]

    for nf in new_files:
        stem = normalise_name(nf)
        if not stem:
            continue
        base = os.path.splitext(os.path.basename(nf))[0].lower()
        if base in WEAK_BASENAMES:
            findings.append("%s: name carries no information" % nf)
        for of in others:
            if normalise_name(of) == stem and os.path.dirname(of) != os.path.dirname(nf):
                findings.append("%s: near-identical name to existing %s" % (nf, of))
                break

        if not os.path.isfile(nf):
            continue
        try:
            if os.path.getsize(nf) > 200_000:
                continue
            a = normalise_content(read(nf))
        except OSError:
            continue
        if len(a) < 200:
            continue
        ext = os.path.splitext(nf)[1]
        for of in others:
            if os.path.splitext(of)[1] != ext or not os.path.isfile(of):
                continue
            try:
                if abs(os.path.getsize(of) - os.path.getsize(nf)) > os.path.getsize(nf):
                    continue
                b = normalise_content(read(of))
            except OSError:
                continue
            if len(b) < 200:
                continue
            ratio = difflib.SequenceMatcher(None, a, b).quick_ratio()
            if ratio > 0.85:
                real = difflib.SequenceMatcher(None, a, b).ratio()
                if real > 0.85:
                    findings.append("%s: %d%% similar to existing %s — reuse or extend it"
                                    % (nf, int(real * 100), of))
                    break
    return findings


def check_slop(files):
    findings = []
    for f in files:
        if not os.path.isfile(f) or is_test_path(f):
            continue
        if any(seg in f for seg in ("node_modules/", "loop-project/", "dist/", "build/")):
            continue
        try:
            if os.path.getsize(f) > 500_000:
                continue
            content = read(f)
        except OSError:
            continue

        for pattern, label, flags in SLOP_PATTERNS:
            m = re.search(pattern, content, re.MULTILINE | flags)
            if m:
                line_no = content[:m.start()].count("\n") + 1
                findings.append("%s:%d %s" % (f, line_no, label))

        # A comment whose words all reappear in the very next line says nothing.
        lines = content.splitlines()
        for i in range(len(lines) - 1):
            c = re.match(r"\s*(?://|#)\s*(.+)", lines[i])
            if not c:
                continue
            words = [w.lower() for w in re.findall(r"[A-Za-z]{4,}", c.group(1))]
            if not (1 <= len(words) <= 6):
                continue
            nxt = re.findall(r"[A-Za-z]{4,}", lines[i + 1])
            nxt = set(w.lower() for part in nxt
                      for w in re.findall(r"[A-Z]?[a-z]+", part) or [part])
            nxt |= set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", lines[i + 1]))
            if words and all(w in nxt for w in words):
                findings.append("%s:%d comment restates the line below" % (f, i + 1))
    return findings


def check_registry(new_files, report_text):
    """New reusable units must be registered the moment they are created."""
    findings = []
    reusable = [f for f in new_files
                if any(h in f.replace("\\", "/").lower() for h in REUSABLE_HINTS)]
    if not reusable:
        return findings
    if not os.path.exists(CONVENTIONS):
        return ["%d reusable unit(s) created but 1-spec/conventions.md does not exist" % len(reusable)]
    registry = read(CONVENTIONS)
    for f in reusable:
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem not in registry and f not in registry:
            findings.append("%s: reusable unit not added to the conventions.md registry" % f)
    return findings


def cmd_reuse(args):
    """Search before building. The step that stops near-duplicates existing at all."""
    terms = [t.lower() for t in re.findall(r"[a-z]{3,}", args.query.lower())]
    if not terms:
        die('give something to search for: loop.py reuse "currency format"')

    print("searching for: %s\n" % " ".join(terms))
    hits = 0

    if os.path.exists(CONVENTIONS):
        print("registry (loop-project/1-spec/conventions.md)")
        for line in read(CONVENTIONS).splitlines():
            low = line.lower()
            if line.strip().startswith("|") and any(t in low for t in terms):
                print("  " + line.strip())
                hits += 1
        if hits == 0:
            print("  no registry entry matched")
    else:
        print("registry: 1-spec/conventions.md not found — the loop has no memory yet")

    print("\nworking tree")
    tree_hits = 0
    for f in source_files():
        name = normalise_name(f)
        if any(t in name for t in terms):
            print("  %s  (name match)" % f)
            tree_hits += 1
            continue
        try:
            if os.path.getsize(f) > 200_000:
                continue
            content = read(f).lower()
        except OSError:
            continue
        for t in terms:
            if re.search(r"\b(function|const|def|class|export)\s+\w*%s" % re.escape(t), content):
                print("  %s  (declares something matching '%s')" % (f, t))
                tree_hits += 1
                break
        if tree_hits > 25:
            print("  ... more matches; narrow the query")
            break
    if tree_hits == 0:
        print("  no match")

    print("")
    if hits or tree_hits:
        print("Something exists. Import it, or extend it if extending keeps it single-purpose.")
        print("If neither fits, say in the REPORT what you searched for and why it did not fit.")
    else:
        print("Nothing found. Build it, then add one line to the conventions.md registry")
        print("immediately — a registry written at the end is an inventory, not a memory.")
    return 0


def validate_report(text):
    problems = []
    if not re.search(r"^#\s+REPORT\s+TASK-\d{3}", text, re.MULTILINE):
        problems.append("missing '# REPORT TASK-###' heading")

    m = re.search(r"^Status:\s*(\w+)", text, re.MULTILINE)
    if not m:
        problems.append("missing 'Status:' line")
    elif m.group(1) not in ("Done", "Partial", "Blocked"):
        problems.append("Status must be Done, Partial or Blocked (found '%s')" % m.group(1))

    found = [h.strip() for h in re.findall(r"^##\s+(.+)$", text, re.MULTILINE)]
    lowered = [h.lower() for h in found]
    for section in REPORT_SECTIONS:
        if section.lower() not in lowered:
            problems.append("missing section '## %s'" % section)

    present = [s for s in REPORT_SECTIONS if s.lower() in lowered]
    order = [lowered.index(s.lower()) for s in present]
    if order != sorted(order):
        problems.append("sections are out of order")

    summary = parse_section(text, "Summary")
    if not summary:
        problems.append("Summary is empty")
    elif len(summary.split()) > 150:
        problems.append("Summary is %d words (limit 150)" % len(summary.split()))

    if not parse_section(text, "Commands run").strip():
        problems.append("Commands run is empty — evidence is required")

    acc = parse_section(text, "Acceptance")
    rows = [l for l in acc.splitlines() if l.strip().startswith("|") and "AC-" in l]
    if not rows:
        problems.append("Acceptance has no AC- rows")
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[2]:
            problems.append("Acceptance row has no result: %s" % row.strip()[:60])

    for section in ("Assumptions", "Risks", "Blocked"):
        if not parse_section(text, section).strip():
            problems.append("%s is empty — write 'none' if it genuinely is" % section)

    return problems


def cmd_verify(args):
    state = require_state()
    tid = args.task.upper()
    if not re.match(r"^TASK-\d{3}$", tid):
        die("task id must look like TASK-007")

    card_path = os.path.join(LOOP_DIR, "2-build/tasks", tid + ".md")
    report_path = os.path.join(LOOP_DIR, "2-build/reports", tid + ".report.md")
    r = Result()

    if not os.path.exists(card_path):
        die("no task card at %s" % card_path)
    card = read(card_path)

    # 1 evidence
    if not os.path.exists(report_path):
        r.add("evidence complete", False, "no REPORT at %s" % report_path, "2")
        code = r.render("verify %s" % tid)
        print("\nVerdict input: REWORK. Do not open the diff — the missing report is the finding.")
        return code
    report = read(report_path)
    problems = validate_report(report)
    r.add("report schema", not problems,
          "ok" if not problems else "%d problem(s)" % len(problems), "2")
    for p in problems:
        print("    - " + p)

    # 2 scope
    files = changed_files()
    write_globs = parse_globs(parse_section(card, "Write-set"))
    if files is None:
        r.add("scope intact", True, "skipped (no git repository)")
    elif not write_globs:
        r.add("scope intact", False, "task card declares no write-set", "2")
    else:
        code_files = [f for f in files if not f.startswith(LOOP_DIR + os.sep)
                      and not f.startswith(LOOP_DIR + "/")]
        outside = [f for f in code_files if not matches_any(f, write_globs)]
        r.add("scope intact", not outside,
              "%d changed, %d outside write-set" % (len(code_files), len(outside)), "2")
        for f in outside:
            print("    - outside write-set: %s" % f)

    # 3 test integrity
    if files is None:
        r.add("test integrity", True, "skipped (no git repository)")
    else:
        tamper = check_test_tampering(files)
        r.add("test integrity", not tamper,
              "clean" if not tamper else "%d finding(s)" % len(tamper), "1")
        for t in tamper:
            print("    - " + t)

    # 4 secrets
    scan_targets = files if files is not None else []
    secrets = check_secrets(scan_targets)
    r.add("no secrets introduced", not secrets,
          "clean" if not secrets else "%d finding(s)" % len(secrets), "1")
    for s in secrets:
        print("    - " + s)

    # 5 files-changed listed
    if files is not None:
        listed = parse_section(report, "Files changed")
        code_files = [f for f in files if not f.startswith(LOOP_DIR)]
        unlisted = [f for f in code_files if os.path.basename(f) not in listed and f not in listed]
        r.add("files changed listed", not unlisted,
              "ok" if not unlisted else "%d not in REPORT" % len(unlisted), "2")
        for f in unlisted:
            print("    - not listed in REPORT: %s" % f)

    # 6-8 craft: reuse, consistency, slop
    if files is not None:
        code_files = [f for f in files
                      if not f.startswith(LOOP_DIR) and os.path.isfile(f)]
        new_files = []
        for f in code_files:
            code_g, out_g, _ = git("ls-files", "--error-unmatch", f)
            if code_g != 0:
                new_files.append(f)

        dupes = check_duplication(new_files, source_files())
        r.add("no duplicated components", not dupes,
              "clean" if not dupes else "%d finding(s)" % len(dupes), "2")
        for d in dupes:
            print("    - " + d)

        slop = check_slop(code_files)
        r.add("no slop patterns", not slop,
              "clean" if not slop else "%d finding(s)" % len(slop), "3")
        for s in slop[:10]:
            print("    - " + s)
        if len(slop) > 10:
            print("    - ... and %d more" % (len(slop) - 10))

        unreg = check_registry(new_files, report)
        r.add("reusables registered", not unreg,
              "clean" if not unreg else "%d unregistered" % len(unreg), "3")
        for u in unreg:
            print("    - " + u)

    reuse_section = parse_section(report, "Reuse")
    r.add("reuse search recorded", bool(reuse_section.strip()),
          "ok" if reuse_section.strip() else "REPORT has no Reuse section content", "3")

    code = r.render("verify %s" % tid)
    print("\nRemaining checks are for the Judge: acceptance quality, QA findings, security")
    print("contract, design contract, craft judgement, regression. See references/judge-rubric.md.")
    return code


# --------------------------------------------------------------------------- cycle

def cmd_cycle(args):
    state = require_state()
    tid = args.task.upper()
    tasks = state.setdefault("tasks", {})
    if tid not in tasks:
        tasks[tid] = {"title": "", "cycles": 0, "verdict": None, "findings": {}}
    t = tasks[tid]
    t["cycles"] = t.get("cycles", 0) + 1
    t["verdict"] = "REWORK"

    if args.finding:
        f = t.setdefault("findings", {})
        f[args.finding] = f.get(args.finding, 0) + 1

    reasons = []
    if t["cycles"] > MAX_CYCLES_PER_TASK:
        reasons.append("%s exceeded %d cycles — the task was cut wrong (Phase 0/1 defect)"
                       % (tid, MAX_CYCLES_PER_TASK))
    for finding, count in t.get("findings", {}).items():
        if count >= MAX_REPEAT_FINDING:
            reasons.append("finding '%s' has failed %d cycles on %s" % (finding, count, tid))

    print("%s cycle %d" % (tid, t["cycles"]))

    if reasons:
        state["status"] = "BLOCKED"
        state["blocked_reason"] = "; ".join(reasons)
        save_state(state)
        ledger("BLOCKED on %s.\n%s\n\nWrite the options and a recommendation, then stop."
               % (tid, "\n".join("- " + x for x in reasons)))
        print("\nBLOCKED:")
        for x in reasons:
            print("  - " + x)
        print("\nStop. Write the decision the human needs into ledger.md and present it.")
        return 1

    save_state(state)
    print("Within limits (%d/%d). Issue rework orders and continue."
          % (t["cycles"], MAX_CYCLES_PER_TASK))
    return 0


# --------------------------------------------------------------------------- gates

PLACEHOLDER_MARKERS = [
    r"<[a-z][a-z ]{2,}>",          # <trigger>, <response>, <what is being built>
    r"\bFR-00x\b", r"\bAC-00x\b", r"\bBR-00x\b",
    r"^\s*-\s*$",                   # a bullet with nothing after it
    r"\|\s*\|\s*\|\s*\|",           # an all-empty table row
    r"\bTODO\b", r"\bTBD\b",
]


def placeholders_in(path):
    """Unfilled template markers. A gate that passes a stub is worse than no gate."""
    if not os.path.exists(path):
        return ["file missing"]
    text = read(path)
    hits = []
    for pat in PLACEHOLDER_MARKERS:
        found = re.findall(pat, text, re.MULTILINE | re.IGNORECASE)
        if found:
            hits.append("%s (x%d)" % (pat, len(found)))
    if re.search(r"\.\.\.", text):
        hits.append("ellipsis placeholder")
    return hits


def gate_checks(gate, state):
    r = Result()
    p = lambda *a: os.path.join(LOOP_DIR, *a)

    def nonempty(path, min_chars=120):
        return os.path.exists(path) and len(read(path).strip()) >= min_chars

    def filled(label, rel):
        hits = placeholders_in(p(rel))
        r.add("%s filled in" % label, not hits,
              "clean" if not hits else "%d placeholder pattern(s) remain" % len(hits))
        for h in hits[:4]:
            print("    - unfilled: %s" % h)

    if gate == "g0":
        for name, path in [("research", "0-plan/research.md"), ("brd", "0-plan/brd.md"),
                           ("prd", "0-plan/prd.md"), ("plan", "0-plan/plan.md"),
                           ("dod", "0-plan/dod.md")]:
            r.add("%s written" % name, nonempty(p(path)), path)
        for label, path in [("prd", "0-plan/prd.md"), ("dod", "0-plan/dod.md"),
                            ("brd", "0-plan/brd.md")]:
            filled(label, path)
        if os.path.exists(p("0-plan/prd.md")):
            prd = read(p("0-plan/prd.md"))
            frs = re.findall(r"\bFR-\d{3}\b", prd)
            r.add("FR ids present", bool(frs), "%d found" % len(set(frs)))
            ears = re.findall(r"(?i)\b(when|while|if|where)\b[^|\n]*\bshall\b", prd)
            r.add("EARS phrasing used", bool(ears), "%d shall-statements" % len(ears))
            weak = re.findall(r"(?i)\bthe system (should|could|might)\b", prd)
            r.add("no weak modals", not weak, "%d found" % len(weak))
        if os.path.exists(p("0-plan/dod.md")):
            dod = read(p("0-plan/dod.md"))
            acs = re.findall(r"\bAC-\d{3}\b", dod)
            r.add("acceptance rows exist", bool(acs), "%d found" % len(set(acs)))

    elif gate == "g1":
        for name, path in [("architecture", "1-spec/architecture.md"),
                           ("interfaces", "1-spec/interfaces.md"),
                           ("security", "1-spec/security.md"),
                           ("qa strategy", "1-spec/qa-strategy.md"),
                           ("conventions", "1-spec/conventions.md")]:
            r.add("%s written" % name, nonempty(p(path)), path)
        for label, path in [("interfaces", "1-spec/interfaces.md"),
                            ("qa strategy", "1-spec/qa-strategy.md")]:
            filled(label, path)
        if os.path.exists(p("1-spec/qa-strategy.md")) and os.path.exists(p("0-plan/dod.md")):
            acs = set(re.findall(r"\bAC-\d{3}\b", read(p("0-plan/dod.md"))))
            mapped = set(re.findall(r"\bAC-\d{3}\b", read(p("1-spec/qa-strategy.md"))))
            missing = sorted(acs - mapped)
            r.add("every AC mapped to a test", not missing,
                  "unmapped: %s" % (", ".join(missing) if missing else "none"))
        if os.path.exists(p("1-spec/security.md")):
            sec = read(p("1-spec/security.md"))
            rules = re.findall(r"\bSEC-[A-Z]?\d+\b", sec)
            r.add("security rules selected", bool(rules), "%d rules" % len(set(rules)))
        if os.path.exists(p("1-spec/architecture.md")):
            arch = read(p("1-spec/architecture.md"))
            r.add("trust boundaries marked", "trust boundar" in arch.lower(),
                  "search for 'trust boundar'")
            r.add("foundation order stated", "foundation" in arch.lower(), "")

    elif gate == "g2":
        tasks = state.get("tasks", {})
        r.add("tasks exist", bool(tasks), "%d tasks" % len(tasks))
        missing_reports = [t for t in tasks
                           if not os.path.exists(p("2-build/reports", t + ".report.md"))]
        r.add("every task has a REPORT", not missing_reports,
              "missing: %s" % (", ".join(sorted(missing_reports)) or "none"))

    elif gate == "g3":
        tasks = state.get("tasks", {})
        open_tasks = [t for t, v in tasks.items() if v.get("verdict") != "PASS"]
        r.add("all tasks PASS", not open_tasks,
              "open: %s" % (", ".join(sorted(open_tasks)) or "none"))
        current = sha256_of(p("0-plan/dod.md"))
        frozen = state.get("dod_hash")
        r.add("DoD unchanged since G0", bool(frozen) and current == frozen,
              "hash match" if frozen and current == frozen else "drift or never frozen", "1")
        files = changed_files()
        if files is not None:
            secrets = check_secrets(files)
            r.add("no secrets in working tree", not secrets,
                  "%d finding(s)" % len(secrets), "1")
        r.add("README present", os.path.exists("README.md") or os.path.exists("readme.md"),
              "install, run, test, deploy")

    return r


def cmd_gate(args):
    state = require_state()
    gate = args.gate.lower()
    if gate not in GATES:
        die("gate must be one of: %s" % ", ".join(GATES))

    r = gate_checks(gate, state)
    code = r.render("gate %s" % gate.upper())

    if not args.pass_gate:
        if gate in state.get("human_gates", []):
            print("\n%s requires a human. Present a summary and ask for approval." % gate.upper())
        return code

    if r.failed:
        print("\nRefusing to pass %s with %d failing check(s)." % (gate.upper(), len(r.failed)))
        print("Fix them, or record a deliberate exception in ledger.md and re-run.")
        return 1

    state["gates"][gate] = {"passed": True, "at": now()}

    if gate == "g0":
        h = sha256_of(os.path.join(LOOP_DIR, "0-plan/dod.md"))
        state["dod_hash"] = h
        state["phase"] = 1
        state["cursor"] = "1.1 architecture"
        ledger("G0 passed. Definition of Done frozen at sha256 %s." % (h[:16] if h else "unknown"))
        print("\nG0 passed. DoD frozen. Any later change to dod.md is reported as drift.")
    elif gate == "g1":
        state["phase"] = 2
        state["cursor"] = "2.1 cut tasks"
        ledger("G1 passed. Spec complete; build may start, foundation first.")
        print("\nG1 passed. Cut tasks, foundation first.")
    elif gate == "g2":
        state["phase"] = 3
        state["cursor"] = "3.1 tester pass"
        ledger("G2 passed. All tasks reported.")
        print("\nG2 passed. Verification.")
    elif gate == "g3":
        state["phase"] = 3
        state["status"] = "PASS"
        state["cursor"] = "closed"
        ledger("G3 passed. Loop closed.")
        print("\nG3 passed. The loop is closed.")
        print("Report what was built, what was deliberately not built, where the evidence lives,")
        print("and the residual risks.")

    save_state(state)
    return 0


# --------------------------------------------------------------------------- block

def cmd_block(args):
    state = require_state()
    state["status"] = "BLOCKED"
    state["blocked_reason"] = args.reason
    save_state(state)
    ledger("BLOCKED: %s\n\nOptions and recommendation belong here." % args.reason)
    print("Status set to BLOCKED.")
    print("Write the options and your recommendation into loop-project/ledger.md, then stop.")
    return 0


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="loop.py", description="Project Loop state machine")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("init")
    p.add_argument("--brownfield", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("status")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("task")
    p.add_argument("action", choices=["new", "list"])
    p.add_argument("title", nargs="?")
    p.set_defaults(fn=cmd_task)

    p = sub.add_parser("reuse")
    p.add_argument("query", help='what you are about to build, e.g. "currency format"')
    p.set_defaults(fn=cmd_reuse)

    p = sub.add_parser("verify")
    p.add_argument("task")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("cycle")
    p.add_argument("task")
    p.add_argument("--finding", help="short stable label, to detect a recurring finding")
    p.set_defaults(fn=cmd_cycle)

    p = sub.add_parser("gate")
    p.add_argument("gate")
    p.add_argument("--check", action="store_true")
    p.add_argument("--pass", dest="pass_gate", action="store_true")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("block")
    p.add_argument("reason")
    p.set_defaults(fn=cmd_block)

    args = ap.parse_args()
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
