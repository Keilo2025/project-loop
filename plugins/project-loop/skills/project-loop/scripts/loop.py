#!/usr/bin/env python3
"""
Project Loop state machine and deterministic gate checks.

Everything here is intentionally mechanical. Checks that a script can assert should never
cost model tokens, and a script asserts them more reliably.

Python 3.8+, standard library only, no network access.

  loop.py init [--brownfield]      scaffold /loop-project
  loop.py status                   compact state summary (run this first, every session)
  loop.py roles --list             show the 18 roles, their class, and what is enabled
  loop.py roles --recommend        propose a role set from the shape of this project
  loop.py roles --preset growth    core 5 | standard 8 | product 12 | growth 15 | full 18
  loop.py roles --enable designer  turn individual roles on or off (--disable too)
  loop.py roles --vertical fintech set the Domain Analyst's vertical (--vertical list to see them)
  loop.py task new "<title>"       create the next TASK card
  loop.py task list                list tasks and their state
  loop.py reuse "currency format"  search registry + tree BEFORE building anything new
  loop.py verify TASK-007          run the deterministic REPORT, scope, integrity + craft checks
  loop.py verdict TASK-007 pass    record a typed Judge outcome and its evidence
  loop.py gate g1 --check          run a gate's mechanical checks
  loop.py gate g1 --pass           advance the loop past a gate
  loop.py block "<reason>"         set status BLOCKED and write to the ledger
  loop.py unblock --by NAME ...    resume only after a recorded human decision
  loop.py migrate --by NAME ...    attest a legacy roster or missing Git baseline

Exit codes: 0 pass, 1 fail (checks did not clear), 2 usage or state error.
"""

import argparse
from contextlib import contextmanager
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

LOOP_DIR = "loop-project"
STATE_FILE = os.path.join(LOOP_DIR, "loop.json")
LEDGER = os.path.join(LOOP_DIR, "ledger.md")

PHASES = ["0-plan", "1-spec", "2-build", "3-verify"]
GATES = ["g0", "g1", "g2", "g3"]

# Four authority classes. A role belongs to exactly one and inherits its prohibitions whole,
# which is why the roster can grow to twelve without the permission model growing at all.
CLASSES = {
    "PLAN": "writes specification artifacts; never source code, never a verdict",
    "CODE": "writes source inside a declared write-set; never judges its own output",
    "TEST": "executes and reproduces; never fixes what it finds",
    "JUDGE": "grades evidence; never writes source",
}

# key -> (display name, class, artifact owned, is core, why you would enable it)
# Order matters: it is the display order, and it groups by class.
ROLES = {
    "analyst": ("Analyst", "PLAN", "0-plan/research.md", False,
                "unfamiliar domain, fast-moving stack, or constraints nobody has checked"),
    "domain-analyst": ("Domain Analyst", "PLAN", "0-plan/domain.md", False,
                       "a regulated or convention-heavy vertical whose table stakes you do not know"),
    "planner": ("Planner", "PLAN", "0-plan/brd,prd,plan,dod.md", True, ""),
    "architect": ("Architect", "PLAN", "1-spec/architecture,interfaces,conventions.md + tasks", True, ""),
    "ux-researcher": ("UX Researcher", "PLAN", "1-spec/ux-contract.md", False,
                      "the users are not you, and a wrong flow costs more than a wrong colour"),
    "designer": ("Designer", "PLAN", "1-spec/design-contract.md", False,
                 "the project has a UI a human will look at"),
    "content-strategist": ("Content Strategist", "PLAN", "1-spec/content-contract.md", False,
                           "shipped words have to persuade or instruct a specific audience"),
    "seo-specialist": ("SEO Specialist", "PLAN", "1-spec/seo-contract.md", False,
                       "there are public pages that have to be found by search"),
    "llm-specialist": ("LLM Specialist", "PLAN", "1-spec/ai-readiness.md", False,
                       "the platform should be readable, citable and operable by AI systems"),
    "security-architect": ("Security Architect", "PLAN", "1-spec/security.md", False,
                           "auth, personal data, payments, uploads or third-party input"),
    "worker": ("Worker", "CODE", "application source in its write-set", True, ""),
    "integrator": ("Integrator", "CODE", "build, CI, migrations, deploy plumbing", False,
                   "the build has to run somewhere other than this machine"),
    "scribe": ("Scribe", "CODE", "README.md and user-facing docs", False,
               "someone other than the author will have to run this"),
    "tester": ("Tester", "TEST", "3-verify/qa/QA-###.md", True, ""),
    "adversary": ("Adversary", "TEST", "3-verify/qa/SEC-###.md", False,
                  "a security rule is blocking and somebody should try to break it"),
    "ui-critic": ("UI Critic", "TEST", "3-verify/qa/UI-###.md", False,
                  "somebody has to look at what rendered and say whether it looks generated"),
    "judge": ("Judge", "JUDGE", "3-verify/verdicts/V-###.md + rework/R-###.md", True, ""),
    "product-owner": ("Product Owner", "JUDGE", "3-verify/verdicts/PO-###.md", False,
                      "a stakeholder cares whether the outcome moved, not just whether it shipped"),
}

CORE_ROLES = [k for k, v in ROLES.items() if v[3]]

# Roles whose artifact nobody else absorbs. Disabling any other optional role hands its work to the
# core role in the same class; disabling one of these means the work is simply not done. Said plainly
# because "nothing is skipped by disabling a role" is otherwise a false claim.
UNABSORBED_ROLES = ["seo-specialist", "llm-specialist"]

# The Domain Analyst is a specialist in one vertical. A section per key lives in
# references/verticals.md; "other" is legitimate and means "research it, there is no section".
VERTICALS = [
    "fintech", "healthtech", "proptech", "agritech", "regtech", "insurtech", "legaltech",
    "edtech", "climatetech", "martech", "hrtech", "logistics", "govtech", "defencetech",
    "commerce", "wealthtech", "cybersecurity", "biotech", "traveltech", "foodtech", "other",
]

PRESETS = {
    "core": list(CORE_ROLES),
    "standard": CORE_ROLES + ["analyst", "designer", "adversary"],
    "product": CORE_ROLES + ["analyst", "ux-researcher", "designer", "adversary", "ui-critic",
                             "scribe", "product-owner"],
    "growth": CORE_ROLES + ["analyst", "ux-researcher", "designer", "content-strategist",
                            "seo-specialist", "llm-specialist", "adversary", "ui-critic",
                            "scribe", "product-owner"],
    "full": list(ROLES),
}

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
MAX_TEXT_BYTES = 5_000_000

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

# Strong, low-noise signatures that Git can search across reachable patches. Generic assignments
# are intentionally left to the current-tree scanner because history contains too many examples
# and fixtures for those patterns to remain actionable.
HISTORY_SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "aws access key id"),
    (r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "private key block"),
    (r"sk-[A-Za-z0-9]{20,}", "provider token"),
    (r"gh[pousr]_[A-Za-z0-9]{20,}", "github token"),
]

PLACEHOLDER_HINTS = ("example", "changeme", "placeholder", "your-", "xxx", "dummy", "<", "test")


# --------------------------------------------------------------------------- helpers

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(msg, code=2):
    print("error: " + msg, file=sys.stderr)
    sys.exit(code)


def read(path):
    candidate = os.path.abspath(path)
    loop_root = os.path.abspath(LOOP_DIR)
    try:
        owned = os.path.commonpath([loop_root, candidate]) == loop_root
    except ValueError:
        owned = False
    if owned and not loop_owned_path_is_safe(path):
        die("refusing to read through an unsafe loop-project path: %s" % path)
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        die("cannot read %s (%s)" % (path, exc))
    if size > MAX_TEXT_BYTES:
        die("refusing to read %s: %d bytes exceeds the %d-byte text limit"
            % (path, size, MAX_TEXT_BYTES))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as exc:
        die("cannot read %s (%s)" % (path, exc))


def write(path, content):
    candidate = os.path.abspath(path)
    loop_root = os.path.abspath(LOOP_DIR)
    try:
        owned = os.path.commonpath([loop_root, candidate]) == loop_root
    except ValueError:
        owned = False
    if owned and not loop_owned_path_is_safe(path):
        die("refusing to write through an unsafe loop-project path: %s" % path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


@contextmanager
def project_lock(timeout_seconds=10):
    """Serialize lifecycle commands so parallel agents cannot lose state updates."""
    project_id = hashlib.sha256(
        os.path.realpath(".").encode("utf-8", errors="surrogateescape")
    ).hexdigest()[:24]
    lock_path = os.path.join(tempfile.gettempdir(), "project-loop-%s.lock" % project_id)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    deadline = time.monotonic() + timeout_seconds
    unlock = None
    try:
        try:
            import fcntl

            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    unlock = lambda: fcntl.flock(descriptor, fcntl.LOCK_UN)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        die("another Project Loop command still holds the project lock")
                    time.sleep(0.05)
        except ImportError:  # pragma: no cover - exercised on Windows
            import msvcrt

            if os.path.getsize(lock_path) == 0:
                os.write(descriptor, b"0")
            while True:
                try:
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                    unlock = lambda: (
                        os.lseek(descriptor, 0, os.SEEK_SET),
                        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1),
                    )
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        die("another Project Loop command still holds the project lock")
                    time.sleep(0.05)
        yield
    finally:
        if unlock is not None:
            unlock()
        os.close(descriptor)


def loop_root_is_confined():
    """The loop root itself must be a real directory owned by this project."""
    if not os.path.lexists(LOOP_DIR):
        return True
    if os.path.islink(LOOP_DIR):
        return False
    project_root = os.path.realpath(".")
    loop_root = os.path.realpath(LOOP_DIR)
    try:
        return (loop_root != project_root
                and os.path.commonpath([project_root, loop_root]) == project_root)
    except ValueError:
        return False


def first_loop_symlink():
    """Return the first symlink anywhere in the owned evidence tree."""
    if not os.path.isdir(LOOP_DIR) or os.path.islink(LOOP_DIR):
        return LOOP_DIR if os.path.islink(LOOP_DIR) else None
    for base, dirs, names in os.walk(LOOP_DIR, followlinks=False):
        for name in dirs + names:
            path = os.path.join(base, name)
            if os.path.islink(path):
                return path
    return None


def loop_owned_path_is_safe(path):
    """Require every existing component of an owned path to be a real in-tree path."""
    if not loop_root_is_confined():
        return False
    project_root = os.path.realpath(".")
    loop_root = os.path.abspath(LOOP_DIR)
    candidate = os.path.abspath(path)
    try:
        if os.path.commonpath([loop_root, candidate]) != loop_root:
            return False
    except ValueError:
        return False
    current = loop_root
    relative = os.path.relpath(candidate, loop_root)
    if relative != ".":
        for component in relative.split(os.sep):
            current = os.path.join(current, component)
            if os.path.lexists(current) and os.path.islink(current):
                return False
    resolved = os.path.realpath(candidate)
    try:
        return (os.path.commonpath([project_root, resolved]) == project_root
                and os.path.commonpath([os.path.realpath(loop_root), resolved])
                == os.path.realpath(loop_root))
    except ValueError:
        return False


def load_state():
    if not loop_root_is_confined():
        die("loop-project must be a real directory inside the project")
    unsafe_link = first_loop_symlink()
    if unsafe_link:
        die("loop-project contains a symlink at %s; owned evidence paths must be real"
            % unsafe_link)
    if not os.path.exists(STATE_FILE):
        return None
    try:
        state = json.loads(read(STATE_FILE))
    except json.JSONDecodeError as e:
        die("%s is not valid JSON (%s). Fix it by hand; the loop will not guess." % (STATE_FILE, e))
    if not isinstance(state, dict):
        die("loop.json must contain a JSON object")
    phase = state.get("phase")
    if isinstance(phase, bool) or not isinstance(phase, int) or not 0 <= phase < len(PHASES):
        die("loop.json has invalid phase; expected an integer from 0 to 3")
    if state.get("status") not in ("ACTIVE", "BLOCKED", "PASS"):
        die("loop.json has invalid status; expected ACTIVE, BLOCKED or PASS")
    gates = state.get("gates")
    if not isinstance(gates, dict):
        die("loop.json has invalid gates; expected an object")
    for gate in GATES:
        value = gates.get(gate)
        if not isinstance(value, dict) or not isinstance(value.get("passed"), bool):
            die("loop.json has invalid %s gate state" % gate.upper())
    if not isinstance(state.get("tasks"), dict):
        die("loop.json has invalid tasks; expected an object")
    for tid, task in state["tasks"].items():
        if not re.match(r"^TASK-\d{3}$", tid) or not isinstance(task, dict):
            die("loop.json has invalid task entry: %s" % tid)
    roles = state.get("roles")
    if roles is not None and not isinstance(roles, dict):
        die("loop.json has invalid roles; expected an object")
    if isinstance(roles, dict):
        enabled = roles.get("enabled")
        if enabled is not None and (
                not isinstance(enabled, list)
                or any(role not in ROLES for role in enabled)
                or any(role not in enabled for role in CORE_ROLES)):
            die("loop.json has invalid enabled role list")
    frozen_roles = state.get("frozen_roles")
    if frozen_roles is not None and (
            not isinstance(frozen_roles, list)
            or any(role not in ROLES for role in frozen_roles)
            or len(frozen_roles) != len(set(frozen_roles))
            or any(role not in frozen_roles for role in CORE_ROLES)):
        die("loop.json has invalid frozen role list")
    return state


def save_state(state):
    state["updated"] = now()
    if not loop_owned_path_is_safe(STATE_FILE):
        die("refusing to write state through an unsafe loop-project path")
    os.makedirs(LOOP_DIR, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".loop.json.", dir=LOOP_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(state, indent=2) + "\n")
            f.flush()
            os.fsync(f.fileno())
        mode = os.stat(STATE_FILE).st_mode & 0o777 if os.path.exists(STATE_FILE) else 0o644
        os.chmod(temp_path, mode)
        os.replace(temp_path, STATE_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def require_state():
    state = load_state()
    if state is None:
        die("no loop found. Run: loop.py init")
    return state


def ledger(entry):
    if not loop_owned_path_is_safe(LEDGER):
        die("refusing to write the ledger through an unsafe loop-project path")
    line = "\n## %s\n%s\n" % (now(), entry.strip())
    if os.path.exists(LEDGER):
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        write(LEDGER, "# Loop ledger\n\nAppend-only. Decisions, deviations, escalations.\n" + line)


def git(*args):
    try:
        out = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            text=True,
            errors="surrogateescape",
            timeout=30,
        )
        return out.returncode, out.stdout, out.stderr
    except (OSError, subprocess.SubprocessError):
        return 1, "", "git unavailable"


def has_git():
    return git("rev-parse", "--git-dir")[0] == 0


def git_commit_exists(commit):
    if not commit:
        return False
    return git("cat-file", "-e", commit + "^{commit}")[0] == 0


def sha256_of(path):
    if not os.path.exists(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def approval_fingerprint(gate, state):
    """Hash the artifacts and stable state a human approved at a gate."""
    roots = {
        "g0": ["0-plan"],
        "g1": ["1-spec"],
        "g2": ["2-build"],
        "g3": ["0-plan/dod.md", "3-verify"],
    }[gate]
    digest = hashlib.sha256()
    digest.update(hashlib.sha256(gate.encode("utf-8")).digest())
    stable_state = {
        "roles": state.get("roles"),
        "tasks": state.get("tasks"),
        "dod_hash": state.get("dod_hash"),
    }
    digest.update(hashlib.sha256(
        json.dumps(stable_state, sort_keys=True).encode("utf-8")
    ).digest())

    files = []
    for rel in roots:
        path = os.path.join(LOOP_DIR, rel)
        if os.path.isfile(path):
            files.append(path)
        elif os.path.isdir(path):
            for base, dirs, names in os.walk(path):
                dirs.sort()
                for name in sorted(names):
                    files.append(os.path.join(base, name))
    for path in sorted(files):
        rel = os.path.relpath(path, LOOP_DIR).replace("\\", "/")
        digest.update(hashlib.sha256(rel.encode("utf-8")).digest())
        with open(path, "rb") as f:
            file_digest = hashlib.sha256()
            for chunk in iter(lambda: f.read(65536), b""):
                file_digest.update(chunk)
            digest.update(file_digest.digest())
    return digest.hexdigest()


def is_test_path(path):
    low = path.lower()
    return any(h in low for h in TEST_PATH_HINTS)


def enabled_roles(state):
    """Roles active for this loop, in roster order.

    A loop created before role selection existed has no 'roles' key. It gets the core five,
    which is exactly how it already behaved — an old loop must never change shape because the
    tool was upgraded underneath it.
    """
    frozen = (
        state.get("frozen_roles")
        if state.get("gates", {}).get("g0", {}).get("passed")
        else None
    )
    names = frozen if frozen is not None else (
        (state.get("roles") or {}).get("enabled") or CORE_ROLES
    )
    return [k for k in ROLES if k in names]


def role_enabled(state, key):
    return key in enabled_roles(state)


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

def archive_existing_loop():
    if not os.path.lexists(LOOP_DIR):
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = "%s.archive-%s" % (LOOP_DIR, stamp)
    target = base
    suffix = 1
    while os.path.lexists(target):
        suffix += 1
        target = "%s-%d" % (base, suffix)
    os.replace(LOOP_DIR, target)
    return target


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

# Seeded only when the owning role is enabled. Scaffolding a contract nobody owns creates an empty
# file that reads as a standard and is enforced by no one.
OPTIONAL_SEED = {
    "domain-analyst": ("0-plan/domain.md", "# Domain brief\n\nVertical: <set via loop.py roles --vertical>\nSection read from references/verticals.md: \n\n## Table stakes\nWhat every serious product here has, that a newcomer forgets.\n\n| Feature | Why its absence disqualifies you |\n|---------|----------------------------------|\n\n## Regulatory and standards constraints\nState the trigger, not just the regime. Date every verification.\n\n| Regime | Trigger (what brings it into scope) | What it forces the build to contain | Verified |\n|--------|-------------------------------------|-------------------------------------|----------|\n\n## Vocabulary\n| Term | Means here | Does NOT mean |\n|------|-----------|---------------|\n\n## Integration and data reality\n\n## Open questions for the human\n- \n"),
    "ux-researcher": ("1-spec/ux-contract.md", "# UX contract\n\n## Segment, stated as consequences\n| Dimension | This segment | What it rules out |\n|-----------|-------------|-------------------|\n| Device and input | | |\n| Session shape | | |\n| Interruption tolerance | | |\n| Error cost | | |\n| Expertise and frequency | | |\n| Environment | | |\n\n## Jobs\n| Job | Trigger | Outcome wanted | 'Done' looks like | What they do today instead |\n|-----|---------|----------------|-------------------|----------------------------|\n\n## Journeys with a completion bar\n| Journey | Max steps | Max required fields | Must persist across | Must be recoverable |\n|---------|-----------|--------------------|--------------------|--------------------|\n\n## Failure states drawn from reality\n| Failure | What the system does | What the user sees | What they do next |\n|---------|---------------------|--------------------|-------------------|\n\n## Cognitive load rules\n\n## Accessibility completability\n\n## Non-goals, in experience terms\n- \n\n## Evidence\n| Claim | Source | Or: assumed, and what would test it |\n|-------|--------|-------------------------------------|\n"),
    "content-strategist": ("1-spec/content-contract.md", "# Content contract\n\n## Message hierarchy\nWhat this is and who it is for, in one sentence:\n\n| # | Claim | Evidence it rests on |\n|---|-------|----------------------|\n| 1 | | |\n\nThe objection this answers:\n\n## Voice, stated as bans\n| Never | Always |\n|-------|--------|\n\nBanned generated register (extend from references/content-contract.md):\n\n## Interface copy\n| Surface | String | Constraint |\n|---------|--------|------------|\n\n## Terminology\n| Approved term | Replaces |\n|---------------|----------|\n\nReading level target and the tool that measures it:\n\n## Retrieval structure\n\n## Claims discipline\n"),
    "seo-specialist": ("1-spec/seo-contract.md", "# SEO contract\n\nSelected from references/discoverability-contract.md Part A. Every rule needs a check.\n\n| ID | Rule | Applies to | Check | Blocking |\n|----|------|-----------|-------|----------|\n| SEO-01 | | | | Yes |\n\n## Notes\nWhat discoverability actually means for this product.\n\n## Accepted gaps\nWhat we knowingly are not doing this cycle, why, and who accepted it.\n"),
    "llm-specialist": ("1-spec/ai-readiness.md", "# AI readiness contract\n\nSelected from references/discoverability-contract.md Part B. Every rule needs a check.\nVerify anything you make blocking — this area moves faster than the reference does.\n\n## Crawler access decision\n| Bot | Training | Retrieval | Live answers | Decided by | Why |\n|-----|----------|-----------|--------------|-----------|-----|\n| GPTBot | | | | | |\n| ClaudeBot | | | | | |\n| PerplexityBot | | | | | |\n| Google-Extended | | | | | |\n| CCBot | | | | | |\n\n## Rules\n| ID | Rule | Applies to | Check | Blocking |\n|----|------|-----------|-------|----------|\n| AI-01 | | | | Yes |\n\n## Cross-references to security.md\nRules for an embedded model live there, not here.\n\n## Accepted gaps\n"),
}


def cmd_init(args):
    if not loop_root_is_confined() and not args.force:
        die("loop-project must be a real directory inside the project; "
            "use --force to archive the symlink and create a safe loop")
    if os.path.lexists(LOOP_DIR) and not args.force:
        die("loop-project already exists. Use --force to archive it and start a fresh loop.")

    archived = archive_existing_loop() if args.force else None

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
        "approvals": {},
        "roles": {"enabled": list(CORE_ROLES), "preset": "core", "vertical": None,
                  "selected": False, "selected_at": None},
        "gates": {g: {"passed": False, "at": None} for g in GATES},
        "dod_hash": None,
        "tasks": {},
        "blocked_reason": None,
    }
    save_state(state)
    ledger("Loop initialised (%s)." % ("brownfield" if args.brownfield else "greenfield"))

    print("Initialised /loop-project")
    if archived:
        print("Archived previous loop at /%s" % archived)
    print("Phase 0. First choose the role set, then research.md, brd.md, prd.md, plan.md, dod.md.")
    print("")
    print("Roles: 18 available, the core 5 enabled by default. Run 'loop.py roles --recommend',")
    print("put the result to the human, then apply it. G0 will not pass until the set is confirmed,")
    print("because a roster nobody chose is a roster nobody owns.")
    if args.brownfield:
        print("")
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

    rstate = state.get("roles") or {}
    active = enabled_roles(state)

    print("phase:   %d (%s)" % (state["phase"], PHASES[state["phase"]]))
    print("status:  %s" % state["status"])
    print("cursor:  %s" % state.get("cursor", "-"))
    print("gates:   %s" % " ".join(
        "%s=%s" % (g, "pass" if state["gates"][g]["passed"] else "-") for g in GATES))
    print("roles:   %d enabled (%s)%s" % (
        len(active), rstate.get("preset", "core"),
        "" if rstate.get("selected") else "  -- default, not yet confirmed"))
    print("tasks:   %d total, %d open" % (len(tasks), len(open_tasks)))

    if not rstate.get("selected") and state["status"] != "BLOCKED":
        print("\nRole set has not been chosen. Run: loop.py roles --recommend")

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


# --------------------------------------------------------------------------- roles

def split_keys(value):
    return [k.strip().lower() for k in re.split(r"[,\s]+", value or "") if k.strip()]


def preset_label(enabled):
    for name, keys in PRESETS.items():
        if set(keys) == set(enabled):
            return name
    return "custom"


def print_roster(state):
    active = set(enabled_roles(state))
    rstate = state.get("roles") or {}
    print("preset:  %s%s" % (rstate.get("preset", "core"),
                             "" if rstate.get("selected") else "   (default, not yet confirmed)"))
    if "domain-analyst" in active:
        print("vertical: %s" % (rstate.get("vertical") or "NOT SET — run: loop.py roles --vertical <name>"))
    print("")
    shown = None
    for key, (name, cls, owns, core, _why) in ROLES.items():
        if cls != shown:
            shown = cls
            print("%s — %s" % (cls, CLASSES[cls]))
        flag = "[core]" if core else ("[unabsorbed]" if key in UNABSORBED_ROLES else "")
        print("  %s  %-20s %-46s %s" % (
            "on " if key in active else "off", key, owns, flag))
    print("\n%d of %d roles enabled." % (len(active), len(ROLES)))

    missing = [k for k in UNABSORBED_ROLES if k not in active]
    if missing:
        print("\n[unabsorbed] means no other role picks the work up. Off right now: %s."
              % ", ".join(missing))
        print("Every other optional role hands its artifact to the core role in its class. These two")
        print("do not — disabled means those rules are absent, not delegated. Fine if the product has")
        print("no public surface; worth knowing if it does.")

    if "domain-analyst" in active and not rstate.get("vertical"):
        print("\nThe Domain Analyst has no vertical set. Without one it is a second Analyst at the")
        print("same cost. Set it with: loop.py roles --vertical <name>   (--vertical list to see them)")


def recommend_roles(state):
    """Propose a set from what the project actually looks like.

    Deliberately conservative. A recommendation that turns on everything is the same as no
    recommendation, and costs the human the one thing this is meant to save them: a decision.
    """
    def text_of(rel):
        path = os.path.join(LOOP_DIR, rel)
        return read(path).lower() if os.path.exists(path) else ""

    plan_text = text_of("0-plan/prd.md") + text_of("0-plan/brd.md") + text_of("0-plan/research.md")
    tree = source_files()
    exts = set(os.path.splitext(f)[1] for f in tree)

    suggest, signals = set(CORE_ROLES), []

    def note(role_keys, why):
        suggest.update(role_keys)
        signals.append("%-38s -> %s" % (why, ", ".join(role_keys)))

    has_ui = bool({".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"} & exts) or \
        bool(re.search(r"\b(ui|screen|page|component|button|form|design|layout)\b", plan_text))
    if has_ui:
        note(["designer", "ui-critic"], "UI present or specified")

    if has_ui and re.search(r"\b(user|customer|segment|audience|persona|journey|onboard|workflow|adoption)\b",
                            plan_text):
        note(["ux-researcher"], "a named audience with a job to do")

    if re.search(r"\b(auth|login|password|token|session|payment|card|pii|gdpr|hipaa|upload|personal data)\b",
                 plan_text) or any("auth" in f.lower() for f in tree):
        note(["security-architect", "adversary"], "auth / personal data / payments")

    # A public surface is the trigger for the two unabsorbed roles. Nothing else covers them, so a
    # missed signal here means the rules are simply absent.
    public = re.search(r"\b(public|marketing|landing|blog|docs|seo|search engine|content|website|"
                       r"discoverab|organic|sitemap)\b", plan_text)
    if public:
        note(["seo-specialist"], "public pages that have to be found")
    if public or re.search(r"\b(llm|ai agent|mcp|chatgpt|perplexity|citation|rag|assistant|api)\b",
                           plan_text):
        note(["llm-specialist"], "AI systems should be able to read or act on it")

    if re.search(r"\b(copy|content|messaging|tone of voice|brand|newsletter|campaign|persuad|"
                 r"convert|microcopy)\b", plan_text):
        note(["content-strategist"], "shipped words have to do work")

    verticals_re = r"\b(%s)\b" % "|".join(v for v in VERTICALS if v != "other")
    domain_hit = re.search(verticals_re, plan_text) or re.search(
        r"\b(regulat|compliance|licence|license|statutory|audit trail|kyc|aml|gdpr|hipaa|"
        r"mifid|solvency|csrd|ferpa|coppa|itar)\b", plan_text)
    if domain_hit:
        note(["domain-analyst"], "regulated or convention-heavy vertical")

    if os.path.exists("Dockerfile") or os.path.isdir(os.path.join(".github", "workflows")) or \
            re.search(r"\b(deploy|ci/cd|pipeline|docker|kubernetes|hosting|staging|production)\b", plan_text):
        note(["integrator"], "deployment target implied")

    if not (os.path.exists("README.md") or os.path.exists("readme.md")) or \
            re.search(r"\b(open source|public|handover|onboard|contributor)\b", plan_text):
        note(["scribe"], "docs are a deliverable")

    # text_of lowercases, so this match must be case-insensitive or it silently never fires.
    brs = len(set(re.findall(r"\bbr-\d{3}\b", text_of("0-plan/brd.md"), re.IGNORECASE)))
    if brs >= 3:
        note(["product-owner"], "%d business requirements to grade" % brs)

    if state.get("brownfield") or len(text_of("0-plan/research.md").strip()) < 200:
        note(["analyst"], "research not yet established")

    print("Signals in this project\n-----------------------")
    for s in signals:
        print("  " + s)
    if not signals:
        print("  none — nothing here argues for an optional role")

    ordered = [k for k in ROLES if k in suggest]
    optional = [k for k in ordered if not ROLES[k][3]]

    print("\nRecommended: %d roles (%s)" % (len(ordered), preset_label(ordered)))
    for k in ordered:
        print("  %-19s %-22s %s" % (k, ROLES[k][0], "[core]" if ROLES[k][3] else ROLES[k][4]))

    print("\nApply with:")
    if optional:
        cmd = "  loop.py roles --enable %s" % ",".join(optional)
        if "domain-analyst" in optional:
            cmd += " --vertical <name>"
        print(cmd)
    else:
        print("  loop.py roles --confirm      (the core five are the right set here)")

    if "domain-analyst" in optional:
        print("\n  Verticals: %s" % ", ".join(VERTICALS))

    print("\nThis is a recommendation, not a decision — put it to the human before applying it.")
    print("More roles means a slower, more expensive loop that catches more. Fewer means the core")
    print("roles absorb the work with less specialisation and a wider context.")
    unabs = [k for k in UNABSORBED_ROLES if k in suggest]
    if unabs:
        print("\nTwo exceptions worth stating: %s own rules nobody else picks up."
              % " and ".join(ROLES[k][0] for k in unabs))
        print("Leaving them off does not move the work — it removes it.")
    return 0


def cmd_roles(args):
    state = require_state()
    rstate = state.setdefault("roles", {"enabled": list(CORE_ROLES), "preset": "core",
                                        "selected": False, "selected_at": None, "vertical": None})

    if args.vertical and args.vertical.strip().lower() == "list":
        print("Verticals for the Domain Analyst\n-------------------------------")
        for v in VERTICALS:
            print("  " + v)
        print("\nA section per vertical lives in references/verticals.md. 'other' is a legitimate")
        print("choice and means there is no section — research it and write one.")
        return 0

    if args.recommend:
        return recommend_roles(state)

    current = set(enabled_roles(state))
    touched = bool(args.preset or args.enable or args.disable or args.confirm or args.vertical)
    if touched and state.get("gates", {}).get("g0", {}).get("passed"):
        die("the role roster was frozen at G0; use an audited new loop to change it")

    # Validate the vertical before touching anything, so a typo does not half-apply a role change.
    vertical = None
    if args.vertical:
        vertical = args.vertical.strip().lower()
        if vertical not in VERTICALS:
            die("unknown vertical '%s'. Run: loop.py roles --vertical list" % vertical)

    if args.preset:
        if args.preset not in PRESETS:
            die("preset must be one of: %s" % ", ".join(PRESETS))
        current = set(PRESETS[args.preset])

    for key in split_keys(args.enable):
        if key not in ROLES:
            die("unknown role '%s'. Run: loop.py roles --list" % key)
        current.add(key)

    # Applied after the preset so that `--preset growth --vertical proptech` does what it reads like.
    # Naming a vertical is a request for the role that uses it.
    if vertical:
        was_vertical = rstate.get("vertical")
        rstate["vertical"] = vertical
        current.add("domain-analyst")
        if was_vertical and was_vertical != vertical:
            ledger("Domain Analyst vertical changed: %s -> %s. Any conclusion in 0-plan/domain.md "
                   "drawn from the old vertical is now unsourced and must be re-derived."
                   % (was_vertical, vertical))
        else:
            ledger("Domain Analyst vertical set: %s." % vertical)

    for key in split_keys(args.disable):
        if key not in ROLES:
            die("unknown role '%s'. Run: loop.py roles --list" % key)
        if ROLES[key][3]:
            die("%s is a core role. Disabling it would leave the %s class with no member, and a "
                "class with no member is a class whose prohibitions nobody holds."
                % (ROLES[key][0], ROLES[key][1]))
        current.discard(key)

    if touched:
        enabled = [k for k in ROLES if k in current]
        was = rstate.get("enabled") or list(CORE_ROLES)
        rstate["enabled"] = enabled
        rstate["preset"] = preset_label(enabled)
        rstate["selected"] = True
        rstate["selected_at"] = now()
        save_state(state)
        if set(was) != set(enabled) or not args.confirm:
            ledger("Role set confirmed: %s (%d roles).\n%s"
                   % (rstate["preset"], len(enabled), ", ".join(enabled)))

        # Seed the artifact an added role owns. Only on enable, and never over an existing file —
        # overwriting a written contract with a template is the worst possible outcome here.
        seeded = []
        for key, (rel, body) in OPTIONAL_SEED.items():
            if key in enabled:
                path = os.path.join(LOOP_DIR, rel)
                if not os.path.exists(path):
                    write(path, body)
                    seeded.append(rel)
        print("Role set saved.")
        if seeded:
            print("Seeded: %s" % ", ".join(seeded))
        print("")

    print_roster(state)

    if not touched:
        print("\nNothing changed. Use --recommend, --preset, --enable/--disable, or --confirm.")
    elif state.get("phase", 0) > 0:
        print("\nRoster changed after Phase 0. Any artifact an added role owns must still be")
        print("written before its gate, and a removed role's artifact reverts to its core role.")
    return 0


# --------------------------------------------------------------------------- tasks

TASK_TEMPLATE = """# {tid} — {title}

## Scope
<what is being built, one paragraph>

Out of scope:
- 

## Read-set
- /loop-project/2-build/tasks/{tid}.md
- /loop-project/1-spec/interfaces.md
- /loop-project/1-spec/security.md (relevant rules only)

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
        if (state.get("gates", {}).get("g0", {}).get("passed")
                and not state.get("frozen_roles")):
            die("the approved role roster is missing; run the audited migrate command first")
        if not state.get("gates", {}).get("g1", {}).get("passed"):
            die("tasks can only be created after G1 has passed")
        if state.get("phase") != 2 or state.get("gates", {}).get("g2", {}).get("passed"):
            die("tasks can only be created during Phase 2 before G2 passes")
        if state.get("status") != "ACTIVE":
            die("tasks can only be created while the loop is ACTIVE")
        tid = next_id(tdir, "TASK")
        write(os.path.join(tdir, tid + ".md"), TASK_TEMPLATE.format(tid=tid, title=args.title))
        code, head, _ = git("rev-parse", "HEAD")
        base_sha = head.strip() if code == 0 else None
        state.setdefault("tasks", {})[tid] = {
            "title": args.title, "cycles": 0, "verdict": None, "findings": {},
            "base_sha": base_sha,
        }
        save_state(state)
        print("created /loop-project/2-build/tasks/%s.md" % tid)
        if base_sha:
            print("baseline: %s" % base_sha)
        else:
            print("warning: no Git HEAD found; immutable task diff verification is unavailable")
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


def check_changed_path_confinement(files):
    """Reject task-delivered paths whose symlink resolution leaves the project."""
    project_root = os.path.realpath(".")
    findings = []
    for path in files:
        if not os.path.lexists(path):
            continue
        resolved = os.path.realpath(path)
        try:
            inside = os.path.commonpath([project_root, resolved]) == project_root
        except ValueError:
            inside = False
        if not inside:
            findings.append("%s: resolves outside the project" % path)
    return findings


# --------------------------------------------------------------------------- verify

def changed_files(base_sha=None):
    if not has_git():
        return None
    files = []
    if base_sha:
        code, out, _ = git("diff", "--name-only", "-z", base_sha, "--")
        if code != 0:
            return None
        files.extend(path for path in out.split("\0") if path)

    # Untracked files are absent from `git diff <base>`, so merge status into the
    # baseline diff. `--untracked-files=all` avoids collapsing a new directory to
    # one entry and hiding every file inside it.
    code, status_out, _ = git(
        "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
    if code != 0:
        return None
    records = status_out.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        status = record[:2]
        files.append(record[3:])
        if "R" in status or "C" in status:
            # In porcelain -z mode a rename/copy's original path is the next
            # NUL-delimited field. The first field above is the destination.
            index += 1
    return list(dict.fromkeys(f for f in files if f))


def project_files():
    """Files owned by the project, excluding loop evidence and generated/vendor trees."""
    skipped = {".git", "node_modules", "dist", "build", ".next", ".venv", "__pycache__",
               "vendor", "target", "coverage"}
    files = []
    for base, dirs, names in os.walk("."):
        dirs[:] = [
            name for name in dirs
            if name not in skipped
            and name != LOOP_DIR
            and not name.startswith(LOOP_DIR + ".archive-")
        ]
        for name in names:
            files.append(os.path.relpath(os.path.join(base, name), "."))
    return files


def snapshot_paths(files):
    """Hash an exact immutable set of task-delivered paths."""
    files = sorted(set(
        path.replace("\\", "/") for path in files
        if path != LOOP_DIR
        and not path.startswith(LOOP_DIR + "/")
        and not path.startswith(LOOP_DIR + ".archive-")
    ))
    digest = hashlib.sha256()
    for path in files:
        encoded = path.encode("utf-8", errors="surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        if os.path.lexists(path):
            mode = os.lstat(path).st_mode & 0o7777
            digest.update(b"M")
            digest.update(mode.to_bytes(4, "big"))
        if os.path.islink(path):
            target = os.readlink(path).encode("utf-8", errors="surrogateescape")
            digest.update(b"L")
            digest.update(len(target).to_bytes(8, "big"))
            digest.update(target)
        elif os.path.isfile(path):
            digest.update(b"F")
            digest.update(os.path.getsize(path).to_bytes(8, "big"))
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    digest.update(chunk)
        else:
            digest.update(b"D")
    return digest.hexdigest(), files


def result_snapshot(base_sha=None):
    """Capture the task result delta at the moment its verdict is recorded."""
    if has_git():
        files = changed_files(base_sha)
        if files is None:
            return None, []
    else:
        files = project_files()
    return snapshot_paths(files)


def diff_for(path, base_sha=None):
    if base_sha:
        code, out, _ = git("diff", "--unified=0", base_sha, "--", path)
        if code == 0 and out:
            return out
    code, out, _ = git("diff", "--unified=0", "--", path)
    if code != 0 or not out:
        code, out, _ = git("diff", "--cached", "--unified=0", "--", path)
    if not out and os.path.isfile(path):
        tracked, _, _ = git("ls-files", "--error-unmatch", "--", path)
        if tracked != 0:
            # Git has no diff for an untracked file. Model it as an all-added
            # diff so integrity checks cannot hide skips in a newly created test.
            return "\n".join("+" + line for line in read(path).splitlines())
    return out


def check_test_tampering(files, base_sha=None):
    findings = []
    test_files = [f for f in files if is_test_path(f)]
    for f in test_files:
        if not os.path.exists(f):
            findings.append("%s: test file deleted" % f)
            continue
        d = diff_for(f, base_sha)
        if not d:
            continue
        if base_sha:
            code, baseline_paths, _ = git(
                "ls-tree", "-r", "--name-only", "-z", base_sha, "--", f
            )
            existed_at_baseline = (
                code == 0 and f in {path for path in baseline_paths.split("\0") if path}
            )
            if existed_at_baseline:
                findings.append(
                    "%s: pre-existing test modified; resolve the test contract outside "
                    "this task and create a fresh human-approved baseline" % f
                )
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


def check_git_history_secrets():
    """Find strong secret signatures even when a later commit deleted the file."""
    if not has_git():
        return None
    findings = []
    for pattern, label in HISTORY_SECRET_PATTERNS:
        code, commits, error = git(
            "log", "--all", "--format=%H", "--no-patch", "--max-count=1",
            "--regexp-ignore-case", "-G", pattern, "--",
        )
        if code != 0:
            return None
        commit = next((line.strip() for line in commits.splitlines() if line.strip()), None)
        if commit:
            findings.append("%s in commit %s" % (label, commit[:12]))
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
    text = re.sub(r"//[^\n]*|#[^\n]*|/\*.*?\*/", " ", text, flags=re.DOTALL)
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
        print("registry (/loop-project/1-spec/conventions.md)")
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


def validate_report(text, expected_task=None):
    problems = []
    if not re.search(r"^#\s+REPORT\s+TASK-\d{3}", text, re.MULTILINE):
        problems.append("missing '# REPORT TASK-###' heading")
    elif expected_task and not re.search(
            r"^#\s+REPORT\s+%s\b" % re.escape(expected_task), text, re.MULTILINE):
        problems.append("REPORT heading does not name %s" % expected_task)

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
        elif m and m.group(1) == "Done" and cells[2].lower() != "pass":
            problems.append("Acceptance result must be pass for Status: Done: %s"
                            % row.strip()[:80])

    for section in ("Assumptions", "Risks", "Blocked"):
        if not parse_section(text, section).strip():
            problems.append("%s is empty — write 'none' if it genuinely is" % section)

    return problems


def acceptance_ids(text, heading):
    """Return concrete acceptance IDs from one named evidence section, in order."""
    return re.findall(r"\bAC-\d{3}\b", parse_section(text, heading))


def validate_acceptance_trace(task_card, report_text=None, qa_text=None):
    """Require the task, Worker, and Tester to prove exactly the same acceptance set."""
    problems = []
    task_list = acceptance_ids(task_card, "Acceptance")
    task_ids = set(task_list)
    if not task_ids:
        problems.append("task card has no concrete AC-### acceptance rows")
    if len(task_list) != len(task_ids):
        problems.append("task card repeats an acceptance ID")

    for label, text, heading in (
            ("REPORT", report_text, "Acceptance"),
            ("QA", qa_text, "Acceptance verified independently")):
        if text is None:
            continue
        artifact_list = acceptance_ids(text, heading)
        artifact_ids = set(artifact_list)
        if len(artifact_list) != len(artifact_ids):
            problems.append("%s repeats an acceptance ID" % label)
        missing = sorted(task_ids - artifact_ids)
        extra = sorted(artifact_ids - task_ids)
        if missing or extra:
            detail = []
            if missing:
                detail.append("missing %s" % ", ".join(missing))
            if extra:
                detail.append("extra %s" % ", ".join(extra))
            problems.append("%s acceptance does not exactly match the task (%s)"
                            % (label, "; ".join(detail)))
    return problems


def validate_qa_report(text, expected_task, artifact_prefix="QA"):
    problems = []
    if not re.search(r"^#\s+%s-\d{3}\s+.+\s+%s\b"
                     % (re.escape(artifact_prefix), re.escape(expected_task)),
                     text, re.MULTILINE):
        problems.append("%s heading does not name %s" % (artifact_prefix, expected_task))
    for section in ("Commands run", "Acceptance verified independently",
                    "Findings", "Observations", "Regression"):
        if not parse_section(text, section).strip():
            problems.append("missing or empty section '## %s'" % section)

    acceptance = parse_section(text, "Acceptance verified independently")
    rows = [line for line in acceptance.splitlines()
            if re.search(r"\bAC-\d{3}\b", line) and "|" in line]
    if not rows:
        problems.append("QA has no independently verified AC rows")
    for row in rows:
        cells = [cell.strip().lower() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[-1] != "pass":
            problems.append("QA acceptance row is not pass: %s" % row.strip()[:80])

    findings = parse_section(text, "Findings")
    if re.search(r"\bSev-[12]\b", findings, re.IGNORECASE):
        problems.append("QA contains an open Sev-1 or Sev-2 finding")

    regression = parse_section(text, "Regression")
    if not re.search(r"(?i)\bfull suite:\s*pass\b", regression):
        problems.append("QA regression does not record a passing full suite")
    if not re.search(r"(?i)\b0\s+failed\b", regression):
        problems.append("QA regression does not record zero failures")
    return problems


def validate_ui_report(text, expected_task):
    problems = []
    if not re.search(r"^#\s+UI-\d{3}\s+.+\s+%s\b" % re.escape(expected_task),
                     text, re.MULTILINE):
        problems.append("UI heading does not name %s" % expected_task)
    for field in ("Surfaces examined", "How"):
        match = re.search(r"^%s:\s*(.+)$" % re.escape(field), text,
                          re.MULTILINE | re.IGNORECASE)
        if not match or not match.group(1).strip():
            problems.append("missing or empty '%s:' field" % field)
        elif re.search(r"<[^>]+>", match.group(1)):
            problems.append("%s still contains a template placeholder" % field)
    for section in ("Anti-generic bans", "Token discipline", "Data stress",
                    "Required states", "The one deliberate decision", "Copy",
                    "Findings", "Coverage"):
        body = parse_section(text, section)
        if not body.strip():
            problems.append("missing or empty section '## %s'" % section)
        elif re.search(r"<[^>]+>", body):
            problems.append("section '## %s' contains template placeholders" % section)
    findings = parse_section(text, "Findings")
    if re.search(r"\bSev-[12]\b", findings, re.IGNORECASE):
        problems.append("UI report contains an open Sev-1 or Sev-2 finding")
    return problems


def validate_product_owner_report(text):
    problems = []
    if not re.search(r"^#\s+.*\bPO-\d{3}\b", text, re.MULTILINE):
        problems.append("heading does not name a PO-### artifact")
    if not re.search(r"^Verdict:\s*PASS\s*$", text, re.MULTILINE):
        problems.append("business verdict is not PASS")
    if not re.search(r"\bBR-\d{3}\b", text):
        problems.append("no business requirement is named")
    if not re.search(r"(?i)\b(evidence|observed|measured|demonstrated)\b", text):
        problems.append("no outcome evidence is recorded")
    if re.search(r"<[^>]+>", text):
        problems.append("business acceptance contains template placeholders")
    if re.search(r"\bSev-[12]\b", text, re.IGNORECASE):
        problems.append("business acceptance contains an open Sev-1 or Sev-2")
    return problems


def validate_verdict_report(text, expected_task, expected_outcome):
    problems = []
    if not re.search(r"^#\s+VERDICT\s+V-\d{3}\s+.+\s+%s\b" % re.escape(expected_task),
                     text, re.MULTILINE):
        problems.append("verdict heading does not name %s" % expected_task)
    match = re.search(r"^Verdict:\s*(PASS|REWORK|BLOCKED)\s*$", text, re.MULTILINE)
    if not match:
        problems.append("missing typed 'Verdict:' line")
    elif match.group(1) != expected_outcome:
        problems.append("verdict artifact says %s, command requested %s"
                        % (match.group(1), expected_outcome))

    for section in ("Checks", "Orders", "Observations", "Loop state"):
        if not parse_section(text, section).strip():
            problems.append("missing or empty section '## %s'" % section)

    checks = parse_section(text, "Checks")
    rows = []
    for line in checks.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0].isdigit():
            rows.append(cells)
    if len(rows) < 9:
        problems.append("%s verdict must record at least 9 checks" % expected_outcome)
    numbers = [cells[0] for cells in rows]
    missing_numbers = [str(number) for number in range(1, 10) if str(number) not in numbers]
    duplicate_numbers = sorted(set(number for number in numbers if numbers.count(number) > 1))
    if missing_numbers:
        problems.append("verdict checks missing number(s): %s" % ", ".join(missing_numbers))
    if duplicate_numbers:
        problems.append("verdict checks repeat number(s): %s" % ", ".join(duplicate_numbers))
    allowed_results = {"pass", "fail", "n/a"}
    for cells in rows:
        if cells[2].lower() not in allowed_results:
            problems.append("verdict check %s has an unknown result" % cells[0])

    failed = [cells for cells in rows if cells[2].lower() == "fail"]
    if expected_outcome == "PASS":
        for cells in failed:
            problems.append("verdict check %s is not pass or n/a" % cells[0])
        if re.search(r"\bR-\d{3}-\d{2}\b", parse_section(text, "Orders")):
            problems.append("PASS verdict cannot contain rework orders")
    elif expected_outcome == "REWORK":
        if not failed:
            problems.append("REWORK verdict must record at least one failed check")
        if not re.search(r"\bR-\d{3}-\d{2}\b", parse_section(text, "Orders")):
            problems.append("REWORK verdict must cite at least one numbered order")
    elif expected_outcome == "BLOCKED":
        if not failed:
            problems.append("BLOCKED verdict must record at least one failed check")
        if not re.search(r"(?i)\bblocked\b", parse_section(text, "Loop state")):
            problems.append("BLOCKED verdict must state the block in Loop state")
    return problems


def validate_rework_order(text):
    problems = []
    heading = re.search(r"^##\s+(R-\d{3}-\d{2})\s+.+\s+Sev-([1-4])\s+.+\s+\S+",
                        text, re.MULTILINE | re.IGNORECASE)
    if not heading:
        problems.append("missing '## R-###-## — Sev-# — title' heading")
    fields = {}
    for field in ("Finding-ID", "Domain", "DoD-impact", "Finding", "Evidence",
                  "Required", "Re-check", "Cause"):
        match = re.search(r"^%s:\s*(.+)$" % re.escape(field), text,
                          re.MULTILINE | re.IGNORECASE)
        if not match or not match.group(1).strip():
            problems.append("missing or empty '%s:' field" % field)
        else:
            fields[field.lower()] = match.group(1).strip()
    cause = re.search(r"^Cause:\s*(\w+)\s*$", text, re.MULTILINE | re.IGNORECASE)
    if cause and cause.group(1).lower() not in ("code", "craft", "spec", "scope", "plan"):
        problems.append("Cause must be code, craft, spec, scope or plan")
    finding_id = fields.get("finding-id", "").lower()
    if finding_id and not re.match(r"^[a-z0-9][a-z0-9.-]{2,63}$", finding_id):
        problems.append("Finding-ID must be a stable 3-64 character lowercase slug")
    domain = fields.get("domain", "").lower()
    if domain and not re.match(r"^[a-z][a-z0-9-]{1,31}$", domain):
        problems.append("Domain must be a lowercase slug")
    dod_value = fields.get("dod-impact", "").lower()
    if dod_value and dod_value not in ("yes", "no"):
        problems.append("DoD-impact must be yes or no")

    finding_text = fields.get("finding", "")
    required_text = fields.get("required", "")
    security_signal = bool(re.search(
        r"(?i)\b(auth(?:entication|ori[sz]ation|z)?|access control|credential|secret|"
        r"injection|xss|csrf|ssrf|tenant isolation|permission|encryption|security)\b",
        finding_text + "\n" + required_text,
    ))
    effective_domain = "security" if security_signal else domain

    dod_target = r"(?:dod\.md|definition of done|AC-\d{3}|acceptance criteri(?:on|a))"
    change_verb = r"(?:change|edit|add|remove|soften|rewrite|re-?cut|update|modify)"
    inferred_dod_change = bool(
        re.search(r"(?i)\b%s\b[^\n]{0,100}\b%s\b" % (change_verb, dod_target),
                  required_text)
        or re.search(r"(?i)\b%s\b[^\n]{0,100}\b%s\b" % (dod_target, change_verb),
                     required_text)
    )
    normalised_finding = re.sub(
        r"[^a-z0-9]+", " ", finding_text.lower()
    ).strip()
    signature = hashlib.sha256(
        ("%s\0%s" % (effective_domain, normalised_finding)).encode("utf-8")
    ).hexdigest()
    metadata = {
        "order_id": heading.group(1).upper() if heading else None,
        "severity": int(heading.group(2)) if heading else None,
        "finding_id": finding_id or None,
        "domain": effective_domain or None,
        "dod_change": dod_value == "yes" or inferred_dod_change,
        "signature": signature,
        "finding": finding_text,
    }
    return metadata, problems


def owned_directory_is_confined(subdir):
    if not loop_root_is_confined():
        return False
    project_root = os.path.realpath(".")
    loop_root = os.path.realpath(LOOP_DIR)
    expected = os.path.realpath(os.path.join(LOOP_DIR, subdir))
    try:
        return (loop_root != project_root
                and os.path.commonpath([project_root, loop_root]) == project_root
                and os.path.commonpath([loop_root, expected]) == loop_root)
    except ValueError:
        return False


def confined_artifact_path(raw, subdir):
    """Resolve an evidence path and keep it inside its owned loop directory."""
    if not raw:
        return None, None
    if not owned_directory_is_confined(subdir):
        die("evidence directory escapes loop-project: %s" % os.path.join(LOOP_DIR, subdir))
    expected = os.path.realpath(os.path.join(LOOP_DIR, subdir))
    actual = os.path.realpath(raw)
    try:
        inside = os.path.commonpath([expected, actual]) == expected
    except ValueError:
        inside = False
    if not inside:
        die("artifact must be inside %s" % os.path.join(LOOP_DIR, subdir))
    rel = os.path.relpath(actual, ".").replace("\\", "/")
    return actual, rel


def validate_recorded_pass_evidence(tid, task):
    """Rebuild trust in a stored PASS without trusting mutable state or paths."""
    validation_problems = []
    hash_problems = []
    evidence_hashes = task.get("evidence_hashes") or {}
    paths = {
        "task": os.path.join(LOOP_DIR, "2-build/tasks", tid + ".md"),
        "report": os.path.join(LOOP_DIR, "2-build/reports", tid + ".report.md"),
        "qa": task.get("qa_file"),
        "verdict": task.get("verdict_file"),
    }
    owned_dirs = {
        "task": os.path.join(LOOP_DIR, "2-build/tasks"),
        "report": os.path.join(LOOP_DIR, "2-build/reports"),
        "qa": os.path.join(LOOP_DIR, "3-verify/qa"),
        "verdict": os.path.join(LOOP_DIR, "3-verify/verdicts"),
    }

    resolved = {}
    for label, raw in paths.items():
        if not raw:
            validation_problems.append("%s: no recorded artifact path" % label)
            hash_problems.append("%s: no recorded artifact hash" % label)
            continue
        expected = os.path.realpath(owned_dirs[label])
        loop_root = os.path.realpath(LOOP_DIR)
        try:
            owned_dir_safe = os.path.commonpath([loop_root, expected]) == loop_root
        except ValueError:
            owned_dir_safe = False
        if not owned_dir_safe:
            validation_problems.append("%s: evidence directory escapes loop-project" % label)
            hash_problems.append("%s: untrusted evidence directory" % label)
            continue
        actual = os.path.realpath(raw)
        try:
            inside = os.path.commonpath([expected, actual]) == expected
        except ValueError:
            inside = False
        if not inside:
            validation_problems.append("%s: artifact path escapes %s" % (label, owned_dirs[label]))
            hash_problems.append("%s: untrusted artifact path" % label)
            continue
        if not os.path.isfile(actual):
            validation_problems.append("%s: artifact is missing" % label)
            hash_problems.append("%s: artifact is missing" % label)
            continue
        resolved[label] = actual
        recorded_hash = evidence_hashes.get(label)
        current_hash = sha256_of(actual)
        if not recorded_hash:
            hash_problems.append("%s: no recorded hash" % label)
        elif recorded_hash != current_hash:
            hash_problems.append("%s: content changed after verdict" % label)

    report_path = resolved.get("report")
    if report_path:
        report = read(report_path)
        report_problems = validate_report(report, tid)
        status = re.search(r"^Status:\s*(\w+)", report, re.MULTILINE)
        if not status or status.group(1) != "Done":
            report_problems.append("Status must be Done")
        validation_problems.extend("report: " + problem for problem in report_problems)

    qa_path = resolved.get("qa")
    if qa_path:
        validation_problems.extend(
            "qa: " + problem for problem in validate_qa_report(read(qa_path), tid)
        )

    card_path = resolved.get("task")
    if card_path and report_path and qa_path:
        validation_problems.extend(
            "acceptance: " + problem
            for problem in validate_acceptance_trace(
                read(card_path), read(report_path), read(qa_path)
            )
        )

    verdict_path = resolved.get("verdict")
    if verdict_path:
        validation_problems.extend(
            "verdict: " + problem
            for problem in validate_verdict_report(read(verdict_path), tid, "PASS")
        )

    return validation_problems, hash_problems


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
    report_path, _ = confined_artifact_path(report_path, "2-build/reports")
    card = read(card_path)

    # 1 evidence
    if not os.path.isfile(report_path):
        r.add("evidence complete", False, "no REPORT at %s" % report_path, "2")
        code = r.render("verify %s" % tid)
        print("\nVerdict input: REWORK. Do not open the diff — the missing report is the finding.")
        return code
    report = read(report_path)
    problems = validate_report(report, tid)
    r.add("report schema", not problems,
          "ok" if not problems else "%d problem(s)" % len(problems), "2")
    for p in problems:
        print("    - " + p)
    trace_problems = validate_acceptance_trace(card, report)
    r.add("acceptance trace exact", not trace_problems,
          "task and REPORT match" if not trace_problems
          else "%d problem(s)" % len(trace_problems), "1")
    for problem in trace_problems:
        print("    - " + problem)

    # 2 scope
    task_state = state.get("tasks", {}).get(tid, {})
    base_sha = task_state.get("base_sha")
    git_repo = has_git()
    baseline_valid = not git_repo or git_commit_exists(base_sha)
    if git_repo:
        r.add("Git baseline valid", baseline_valid,
              base_sha if baseline_valid else "missing or not a commit", "1")
    files = changed_files(base_sha) if baseline_valid else None
    write_globs = parse_globs(parse_section(card, "Write-set"))
    if files is None:
        r.add("scope intact", False, "unverifiable without a valid Git baseline", "1")
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
        escaped_paths = check_changed_path_confinement(code_files)
        r.add("changed paths confined", not escaped_paths,
              "inside project" if not escaped_paths
              else "%d escaping path(s)" % len(escaped_paths), "1")
        for path in escaped_paths:
            print("    - " + path)

    # 3 test integrity
    if files is None:
        r.add("test integrity", False, "unverifiable without a valid Git baseline", "1")
    else:
        tamper = check_test_tampering(files, base_sha)
        r.add("test integrity", not tamper,
              "clean" if not tamper else "%d finding(s)" % len(tamper), "1")
        for t in tamper:
            print("    - " + t)

    # 4 secrets
    scan_targets = files if files is not None else project_files()
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
        if base_sha:
            code_g, out_g, _ = git(
                "diff", "--name-only", "-z", "--diff-filter=A", base_sha, "--"
            )
            added = set(out_g.split("\0")) if code_g == 0 else set()
            new_files = [f for f in code_files if f in added]
        else:
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
    die("cycle is retired because it can bypass verdict evidence; "
        "use: loop.py verdict TASK-### rework --file ... --order ...")


# --------------------------------------------------------------------------- verdict

def cmd_verdict(args):
    state = require_state()
    if state.get("status") != "ACTIVE":
        die("verdicts can only be recorded while the loop is ACTIVE")
    if (state.get("gates", {}).get("g0", {}).get("passed")
            and not state.get("frozen_roles")):
        die("the approved role roster is missing; run the audited migrate command first")
    tid = args.task.upper()
    if not re.match(r"^TASK-\d{3}$", tid):
        die("task id must look like TASK-007")
    tasks = state.get("tasks", {})
    if tid not in tasks:
        die("unknown task %s" % tid)

    outcome = args.outcome.upper()
    if outcome == "PASS":
        if not state.get("gates", {}).get("g1", {}).get("passed"):
            die("PASS verdicts require G1 to have passed")
        if state.get("phase") not in (2, 3):
            die("PASS verdicts can only be recorded during Build or Verify")
        r = Result()
        report_path, _ = confined_artifact_path(
            os.path.join(LOOP_DIR, "2-build/reports", tid + ".report.md"),
            "2-build/reports",
        )
        r.add("Worker REPORT", os.path.isfile(report_path),
              report_path if os.path.isfile(report_path) else "Worker REPORT missing", "1")
        qa_path, qa_rel = confined_artifact_path(args.qa, "3-verify/qa")
        r.add("Tester QA", bool(qa_path) and os.path.isfile(qa_path),
              qa_path if qa_path and os.path.isfile(qa_path) else "Tester QA missing", "1")
        verdict_path, verdict_rel = confined_artifact_path(args.file, "3-verify/verdicts")
        r.add("Judge verdict", bool(verdict_path) and os.path.isfile(verdict_path),
              verdict_path if verdict_path and os.path.isfile(verdict_path)
              else "Judge verdict missing", "1")
        if r.failed:
            return r.render("verdict %s PASS" % tid)

        report_problems = validate_report(read(report_path), tid)
        status = re.search(r"^Status:\s*(\w+)", read(report_path), re.MULTILINE)
        if not status or status.group(1) != "Done":
            report_problems.append("Worker REPORT Status must be Done")
        qa_problems = validate_qa_report(read(qa_path), tid)
        verdict_problems = validate_verdict_report(read(verdict_path), tid, outcome)
        card_path = os.path.join(LOOP_DIR, "2-build/tasks", tid + ".md")
        trace_problems = validate_acceptance_trace(
            read(card_path), read(report_path), read(qa_path)
        )
        r.add("Worker REPORT valid", not report_problems,
              "valid" if not report_problems else "%d problem(s)" % len(report_problems), "1")
        r.add("Tester QA valid", not qa_problems,
              "valid" if not qa_problems else "%d problem(s)" % len(qa_problems), "1")
        r.add("Judge verdict valid", not verdict_problems,
              "valid" if not verdict_problems else "%d problem(s)" % len(verdict_problems), "1")
        r.add("acceptance trace exact", not trace_problems,
              "task, REPORT, and QA match" if not trace_problems
              else "%d problem(s)" % len(trace_problems), "1")
        for label, problems in (("REPORT", report_problems), ("QA", qa_problems),
                                ("verdict", verdict_problems),
                                ("acceptance", trace_problems)):
            for problem in problems:
                print("    - %s: %s" % (label, problem))
        mechanical_code = cmd_verify(argparse.Namespace(task=tid))
        r.add("mechanical task verification", mechanical_code == 0,
              "passed" if mechanical_code == 0 else "failed", "1")
        if r.failed:
            return r.render("verdict %s PASS" % tid)

        code, head, _ = git("rev-parse", "HEAD")
        task = tasks[tid]
        result_fingerprint, result_files = result_snapshot(task.get("base_sha"))
        task["verdict"] = "PASS"
        task["verdict_at"] = now()
        task["qa_file"] = qa_rel
        task["verdict_file"] = verdict_rel
        task["result_sha"] = head.strip() if code == 0 else None
        task["result_fingerprint"] = result_fingerprint
        task["result_files"] = result_files
        task["mechanical_verification"] = {
            "passed": True,
            "at": now(),
            "base_sha": task.get("base_sha"),
            "result_fingerprint": result_fingerprint,
        }
        task["evidence_hashes"] = {
            "task": sha256_of(card_path),
            "report": sha256_of(report_path),
            "qa": sha256_of(qa_path),
            "verdict": sha256_of(verdict_path),
        }
        save_state(state)
        ledger("%s recorded PASS from %s and %s."
               % (tid, qa_rel, verdict_rel))
        r.render("verdict %s PASS" % tid)
        print("\n%s recorded PASS. G3 will independently revalidate these artifacts." % tid)
        return 0

    if not state.get("gates", {}).get("g1", {}).get("passed"):
        die("%s verdicts require G1 to have passed" % outcome)
    if state.get("phase") not in (2, 3):
        die("%s verdicts can only be recorded during Build or Verify" % outcome)

    verdict_path, verdict_rel = confined_artifact_path(args.file, "3-verify/verdicts")
    r = Result()
    r.add("Judge verdict artifact", bool(verdict_path) and os.path.isfile(verdict_path),
          verdict_path if verdict_path and os.path.isfile(verdict_path)
          else "Judge verdict artifact missing", "1")
    if r.failed:
        return r.render("verdict %s %s" % (tid, outcome))

    verdict_text = read(verdict_path)
    verdict_problems = validate_verdict_report(verdict_text, tid, outcome)
    r.add("Judge verdict valid", not verdict_problems,
          "valid" if not verdict_problems else "%d problem(s)" % len(verdict_problems), "1")
    for problem in verdict_problems:
        print("    - verdict: " + problem)

    if outcome == "REWORK":
        order_paths = []
        order_ids = []
        order_metadata = []
        order_problems = []
        for raw in args.order or []:
            path, rel = confined_artifact_path(raw, "3-verify/rework")
            if not path or not os.path.isfile(path):
                order_problems.append("%s: artifact is missing" % (raw or "<unspecified>"))
                continue
            metadata, problems = validate_rework_order(read(path))
            order_id = metadata.get("order_id")
            if order_id and not re.search(r"\b%s\b" % re.escape(order_id),
                                          parse_section(verdict_text, "Orders")):
                problems.append("%s is not cited by the Judge verdict" % order_id)
            order_paths.append((path, rel))
            if order_id:
                order_ids.append(order_id)
            order_metadata.append(metadata)
            order_problems.extend("%s: %s" % (rel, problem) for problem in problems)
        if not order_paths:
            order_problems.append("at least one rework order artifact is required")
        cited_ids = set(re.findall(r"\bR-\d{3}-\d{2}\b",
                                   parse_section(verdict_text, "Orders")))
        provided_ids = set(order_ids)
        for missing_id in sorted(cited_ids - provided_ids):
            order_problems.append("missing artifact for cited order %s" % missing_id)
        for extra_id in sorted(provided_ids - cited_ids):
            order_problems.append("artifact %s is not cited by the Judge verdict" % extra_id)
        if len(order_ids) != len(provided_ids):
            order_problems.append("duplicate rework order artifacts were supplied")
        task = tasks[tid]
        known_orders = task.get("order_findings") or {}
        known_signatures = task.get("finding_signatures") or {}
        for metadata in order_metadata:
            order_id = metadata.get("order_id")
            finding_id = metadata.get("finding_id")
            signature = metadata.get("signature")
            order_canonical = known_orders.get(order_id)
            signature_canonical = known_signatures.get(signature)
            if (order_canonical and signature_canonical
                    and order_canonical != signature_canonical):
                order_problems.append(
                    "%s conflicts with the previously recorded finding signature" % order_id
                )
            canonical = order_canonical or signature_canonical
            if canonical and finding_id != canonical:
                metadata["declared_finding_id"] = finding_id
                metadata["finding_id"] = canonical
        r.add("rework order artifact", not order_problems,
              "%d valid order(s)" % len(order_paths) if not order_problems
              else "%d problem(s)" % len(order_problems), "1")
        for problem in order_problems:
            print("    - order: " + problem)
        if r.failed:
            return r.render("verdict %s REWORK" % tid)

        task["cycles"] = task.get("cycles", 0) + 1
        task["verdict"] = "REWORK"
        task["verdict_at"] = now()
        task["verdict_file"] = verdict_rel
        task["rework_files"] = [rel for _, rel in order_paths]
        task["rework_metadata"] = [
            {
                "order_id": metadata["order_id"],
                "finding_id": metadata["finding_id"],
                "severity": metadata["severity"],
                "domain": metadata["domain"],
                "dod_change": metadata["dod_change"],
            }
            for metadata in order_metadata
        ]
        task.pop("qa_file", None)
        findings = task.setdefault("findings", {})
        cycle_findings = set(metadata["finding_id"] for metadata in order_metadata)
        for finding in cycle_findings:
            findings[finding] = findings.get(finding, 0) + 1
        order_findings = task.setdefault("order_findings", {})
        finding_signatures = task.setdefault("finding_signatures", {})
        for metadata in order_metadata:
            order_findings[metadata["order_id"]] = metadata["finding_id"]
            finding_signatures[metadata["signature"]] = metadata["finding_id"]
        security_findings = task.setdefault("security_sev1_findings", {})
        security_sev1_labels = set(
            metadata["finding_id"] for metadata in order_metadata
            if metadata["severity"] == 1 and metadata["domain"] == "security"
        )
        for finding in security_sev1_labels:
            security_findings[finding] = security_findings.get(finding, 0) + 1
        task["evidence_hashes"] = {
            "verdict": sha256_of(verdict_path),
            "orders": {rel: sha256_of(path) for path, rel in order_paths},
        }

        reasons = []
        if any(metadata["dod_change"] for metadata in order_metadata):
            reasons.append("%s rework would change the frozen Definition of Done" % tid)
        if task["cycles"] > MAX_CYCLES_PER_TASK:
            reasons.append("%s exceeded %d cycles — the task was cut wrong"
                           % (tid, MAX_CYCLES_PER_TASK))
        for finding, count in findings.items():
            if count >= MAX_REPEAT_FINDING:
                reasons.append("finding '%s' has failed %d cycles on %s"
                               % (finding, count, tid))
        for finding, count in security_findings.items():
            if count >= 2:
                reasons.append("Sev-1 security finding '%s' recurred on %s"
                               % (finding, tid))
        if reasons:
            task["verdict"] = "BLOCKED"
            state["status"] = "BLOCKED"
            state["blocked_reason"] = "; ".join(reasons)
        save_state(state)
        ledger("%s recorded %s at cycle %d from %s; orders: %s."
               % (tid, task["verdict"], task["cycles"], verdict_rel,
                  ", ".join(order_ids)))
        if reasons:
            r.add("loop stop conditions", False, "; ".join(reasons), "1")
            r.render("verdict %s REWORK" % tid)
            print("\nThe requested REWORK crossed a hard stop. Status is BLOCKED.")
            return 1
        r.render("verdict %s REWORK" % tid)
        print("\n%s recorded REWORK cycle %d." % (tid, task["cycles"]))
        return 0

    if outcome == "BLOCKED":
        if not (args.reason or "").strip():
            die("BLOCKED verdicts require --reason with the decision the human must make")
        if r.failed:
            return r.render("verdict %s BLOCKED" % tid)
        task = tasks[tid]
        task["verdict"] = "BLOCKED"
        task["verdict_at"] = now()
        task["verdict_file"] = verdict_rel
        task["evidence_hashes"] = {"verdict": sha256_of(verdict_path)}
        state["status"] = "BLOCKED"
        state["blocked_reason"] = args.reason.strip()
        save_state(state)
        ledger("%s recorded BLOCKED from %s.\nDecision needed: %s"
               % (tid, verdict_rel, args.reason.strip()))
        r.render("verdict %s BLOCKED" % tid)
        print("\nLoop BLOCKED. Present the recorded decision to a human and stop.")
        return 0

    die("unknown verdict outcome: %s" % outcome)


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

    if gate in ("g1", "g2"):
        r.add("approved role roster frozen", bool(state.get("frozen_roles")),
              "%d frozen roles" % len(state.get("frozen_roles") or [])
              if state.get("frozen_roles") else "run the audited migrate command", "1")
    p = lambda *a: os.path.join(LOOP_DIR, *a)

    def nonempty(path, min_chars=120):
        return os.path.exists(path) and len(read(path).strip()) >= min_chars

    def filled(label, rel):
        hits = placeholders_in(p(rel))
        r.add("%s filled in" % label, not hits,
              "clean" if not hits else "%d placeholder pattern(s) remain" % len(hits))
        for h in hits[:4]:
            print("    - unfilled: %s" % h)

    def artifacts_in(subdir, prefix):
        d = p(subdir)
        if not os.path.isdir(d):
            return []
        return [f for f in os.listdir(d) if f.startswith(prefix)]

    if gate == "g0":
        rstate = state.get("roles") or {}
        r.add("role set confirmed", bool(rstate.get("selected")),
              "%d roles (%s)" % (len(enabled_roles(state)), rstate.get("preset", "core"))
              if rstate.get("selected") else "run: loop.py roles --recommend, then apply it")
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
        if role_enabled(state, "domain-analyst"):
            vertical = (state.get("roles") or {}).get("vertical")
            r.add("vertical chosen", bool(vertical),
                  vertical or "run: loop.py roles --vertical <name>")
            r.add("domain brief written", nonempty(p("0-plan/domain.md")),
                  "0-plan/domain.md (Domain Analyst is enabled)")
            if os.path.exists(p("0-plan/domain.md")):
                dom = read(p("0-plan/domain.md"))
                # A domain brief with no dated verification is a brief nobody can re-check, and
                # regulatory claims are the ones where that matters most. Require a real date, not
                # just the word "verified" — an undated "verified" is the same claim with a costume on.
                dated = bool(re.search(r"(?i)\b(verified|checked|as of|retrieved|accessed)\b"
                                       r"[^\n]{0,30}(\d{4}-\d{2}-\d{2}|\b\d{4}\b)", dom))
                r.add("regulatory claims dated", dated,
                      "dated verification present" if dated
                      else "no dated verification — write 'verified <YYYY-MM-DD>' against each regime")

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
        if role_enabled(state, "designer"):
            r.add("design contract written", nonempty(p("1-spec/design-contract.md")),
                  "1-spec/design-contract.md (Designer is enabled)")
        # Each optional PLAN role's artifact is required only when that role is on.
        for key, path, label in [
                ("ux-researcher", "1-spec/ux-contract.md", "ux contract"),
                ("content-strategist", "1-spec/content-contract.md", "content contract"),
                ("seo-specialist", "1-spec/seo-contract.md", "seo contract"),
                ("llm-specialist", "1-spec/ai-readiness.md", "ai readiness contract")]:
            if role_enabled(state, key):
                r.add("%s written" % label, nonempty(p(path)),
                      "%s (%s is enabled)" % (path, ROLES[key][0]))

        # The two rule-table contracts are checked the same way security.md is: ids selected, and a
        # stated check against each. A rule without a check cannot be judged and will not be enforced.
        for key, path, label, pattern in [
                ("seo-specialist", "1-spec/seo-contract.md", "seo", r"\bSEO-\d+\b"),
                ("llm-specialist", "1-spec/ai-readiness.md", "ai readiness", r"\bAI-\d+\b")]:
            if role_enabled(state, key) and os.path.exists(p(path)):
                body = read(p(path))
                ids = set(re.findall(pattern, body))
                r.add("%s rules selected" % label, bool(ids), "%d rules" % len(ids))
                rows = [ln for ln in body.splitlines() if re.search(pattern, ln) and "|" in ln]
                uncheckable = [ln for ln in rows if len(
                    [c for c in ln.strip().strip("|").split("|")[3:5] if c.strip()]) < 2]
                r.add("%s rules carry a check" % label, bool(rows) and not uncheckable,
                      "all %d rows have a check and a blocking flag" % len(rows) if rows and not uncheckable
                      else "%d row(s) missing a check or blocking flag" % (len(uncheckable) or 1))

        if role_enabled(state, "llm-specialist") and os.path.exists(p("1-spec/ai-readiness.md")):
            ai = read(p("1-spec/ai-readiness.md"))
            # The crawler grant has licensing and revenue consequences and no correct default. The
            # seed template already names the bots, so naming them proves nothing — the grant cells
            # have to be filled. A row of empty pipes is the decision nobody made.
            bot_re = (r"(?i)\b(gptbot|oai-searchbot|claudebot|perplexitybot|google-extended|"
                      r"ccbot|bytespider)\b")
            decided_rows = [ln for ln in ai.splitlines()
                            if re.search(bot_re, ln) and "|" in ln
                            and len([c for c in ln.strip().strip("|").split("|")[1:]
                                     if c.strip()]) >= 2]
            prose = bool(re.search(r"(?i)(all (ai )?crawlers?|every crawler)[^.\n]{0,40}"
                                   r"\b(allow|permit|block|disallow)", ai))
            r.add("crawler access decided", bool(decided_rows) or prose,
                  "%d crawler grant(s) filled" % len(decided_rows) if decided_rows
                  else ("blanket decision stated in prose" if prose
                        else "the crawler table is still empty — fill the grant per bot, or state "
                             "one blanket decision explicitly"))

        if role_enabled(state, "ux-researcher") and os.path.exists(p("1-spec/ux-contract.md")):
            ux = read(p("1-spec/ux-contract.md"))
            # "Intuitive" is not checkable; a number is. The template ships with none on purpose.
            bars = re.findall(r"(?<![\w-])\d+(?![\w-])", ux)
            r.add("completion bars are numeric", bool(bars),
                  "%d numeric bar(s)" % len(bars) if bars
                  else "no number anywhere — state max steps and max required fields as figures")

        if role_enabled(state, "content-strategist") and os.path.exists(p("1-spec/content-contract.md")):
            cc = read(p("1-spec/content-contract.md"))
            # The string table is the deliverable. Principles with no strings get ignored by every
            # Worker who needs a button label.
            rows = [ln for ln in cc.splitlines()
                    if ln.strip().startswith("|") and len(ln.split("|")) >= 4
                    and not re.match(r"^\s*\|[\s:|-]+\|\s*$", ln)]
            body_rows = [ln for ln in rows if len([c for c in ln.strip().strip("|").split("|")
                                                   if c.strip()]) >= 3]
            r.add("copy strings written", len(body_rows) >= 3,
                  "%d table row(s) filled" % len(body_rows) if len(body_rows) >= 3
                  else "the string table is the deliverable — %d filled row(s)" % len(body_rows))

    elif gate == "g2":
        tasks = state.get("tasks", {})
        r.add("tasks exist", bool(tasks), "%d tasks" % len(tasks))
        missing_reports = [t for t in tasks
                           if not os.path.isfile(p("2-build/reports", t + ".report.md"))]
        r.add("every task has a REPORT", not missing_reports,
              "missing: %s" % (", ".join(sorted(missing_reports)) or "none"))
        invalid_reports = {}
        for tid in tasks:
            report_path = p("2-build/reports", tid + ".report.md")
            if not os.path.isfile(report_path):
                continue
            report_path, _ = confined_artifact_path(report_path, "2-build/reports")
            report = read(report_path)
            problems = validate_report(report, tid)
            status = re.search(r"^Status:\s*(\w+)", report, re.MULTILINE)
            if status and status.group(1) != "Done":
                problems.append("Status must be Done before G2")
            task_path = p("2-build/tasks", tid + ".md")
            if not os.path.isfile(task_path):
                problems.append("task card is missing")
            else:
                problems.extend(validate_acceptance_trace(read(task_path), report))
            if problems:
                invalid_reports[tid] = problems
        r.add("every REPORT schema-valid", not invalid_reports,
              "invalid: %s" % (", ".join(sorted(invalid_reports)) or "none"))
        for tid, problems in sorted(invalid_reports.items()):
            for problem in problems[:4]:
                print("    - %s: %s" % (tid, problem))

    elif gate == "g3":
        tasks = state.get("tasks", {})
        r.add("approved role roster frozen", bool(state.get("frozen_roles")),
              "%d frozen roles" % len(state.get("frozen_roles") or [])
              if state.get("frozen_roles") else "run the audited migration command", "1")
        r.add("tasks exist", bool(tasks), "%d tasks" % len(tasks))
        open_tasks = [t for t, v in tasks.items() if v.get("verdict") != "PASS"]
        r.add("all tasks PASS", not open_tasks,
              "open: %s" % (", ".join(sorted(open_tasks)) or "none"))
        evidence_problems = {}
        evidence_hash_problems = {}
        for tid, task in sorted(tasks.items()):
            if task.get("verdict") != "PASS":
                continue
            validation, hashes = validate_recorded_pass_evidence(tid, task)
            if validation:
                evidence_problems[tid] = validation
            if hashes:
                evidence_hash_problems[tid] = hashes
        r.add("PASS evidence independently valid", not evidence_problems,
              "invalid: %s" % (", ".join(evidence_problems) or "none"), "1")
        r.add("PASS evidence hashes intact", not evidence_hash_problems,
              "changed: %s" % (", ".join(evidence_hash_problems) or "none"), "1")
        for tid, problems in evidence_problems.items():
            for problem in problems[:6]:
                print("    - %s: %s" % (tid, problem))
        for tid, problems in evidence_hash_problems.items():
            for problem in problems[:6]:
                print("    - %s: %s" % (tid, problem))
        changed_results = []
        missing_receipts = []
        for tid, task in sorted(tasks.items()):
            if task.get("verdict") != "PASS":
                continue
            recorded_files = task.get("result_files")
            if not isinstance(recorded_files, list):
                changed_results.append(tid)
                continue
            current_result, _ = snapshot_paths(recorded_files)
            if not task.get("result_fingerprint") or current_result != task.get("result_fingerprint"):
                changed_results.append(tid)
            receipt = task.get("mechanical_verification") or {}
            if (not receipt.get("passed")
                    or receipt.get("base_sha") != task.get("base_sha")
                    or receipt.get("result_fingerprint") != task.get("result_fingerprint")):
                missing_receipts.append(tid)
        r.add("PASS result snapshots intact", not changed_results,
              "changed: %s" % (", ".join(changed_results) or "none"), "1")
        r.add("PASS mechanical receipts intact", not missing_receipts,
              "missing or inconsistent: %s" % (", ".join(missing_receipts) or "none"), "1")
        attributed_paths = set()
        post_verdict_paths = set()
        invalid_result_boundaries = []
        for tid, task in sorted(tasks.items()):
            if task.get("verdict") != "PASS":
                continue
            attributed_paths.update(task.get("result_files") or [])
            result_sha = task.get("result_sha")
            if not git_commit_exists(result_sha):
                invalid_result_boundaries.append(tid)
                continue
            boundary_delta = changed_files(result_sha)
            if boundary_delta is None:
                invalid_result_boundaries.append(tid)
                continue
            post_verdict_paths.update(
                path for path in boundary_delta
                if path != LOOP_DIR
                and not path.startswith(LOOP_DIR + "/")
                and not path.startswith(LOOP_DIR + ".archive-")
            )
        unattributed_paths = sorted(post_verdict_paths - attributed_paths)
        r.add("PASS Git result boundaries valid", not invalid_result_boundaries,
              "invalid: %s" % (", ".join(invalid_result_boundaries) or "none"), "1")
        r.add("every final changed path attributed", not unattributed_paths,
              "unowned: %s" % (", ".join(unattributed_paths) or "none"), "1")
        for path in unattributed_paths[:12]:
            print("    - unowned final path: " + path)
        if len(unattributed_paths) > 12:
            print("    - ... and %d more" % (len(unattributed_paths) - 12))
        required_acs = set()
        if os.path.exists(p("0-plan/dod.md")):
            required_acs.update(re.findall(r"\bAC-\d{3}\b", read(p("0-plan/dod.md"))))
        covered_acs = set()
        for task in tasks.values():
            qa_file = task.get("qa_file")
            if task.get("verdict") != "PASS" or not qa_file or not os.path.isfile(qa_file):
                continue
            acceptance = parse_section(read(qa_file), "Acceptance verified independently")
            for line in acceptance.splitlines():
                if re.search(r"(?i)\|\s*pass\s*\|?\s*$", line):
                    covered_acs.update(re.findall(r"\bAC-\d{3}\b", line))
        missing_acs = sorted(required_acs - covered_acs)
        r.add("frozen DoD acceptance covered", not missing_acs,
              "missing: %s" % (", ".join(missing_acs) or "none"), "1")
        current = sha256_of(p("0-plan/dod.md"))
        frozen = state.get("dod_hash")
        r.add("DoD unchanged since G0", bool(frozen) and current == frozen,
              "hash match" if frozen and current == frozen else "drift or never frozen", "1")
        secrets = check_secrets(project_files())
        r.add("no secrets in project tree", not secrets,
              "%d finding(s)" % len(secrets), "1")
        history_secrets = check_git_history_secrets()
        r.add("no strong secrets in Git history",
              history_secrets == [],
              ("clean" if history_secrets == [] else
               "scan unavailable" if history_secrets is None else
               "%d finding(s)" % len(history_secrets)), "1")
        for secret in (history_secrets or []):
            print("    - " + secret)
        r.add("README present", os.path.exists("README.md") or os.path.exists("readme.md"),
              "install, run, test, deploy")
        if role_enabled(state, "adversary"):
            evidence_dir_safe = owned_directory_is_confined("3-verify/qa")
            secs = artifacts_in("3-verify/qa", "SEC-") if evidence_dir_safe else []
            valid_tasks = set()
            invalid = ({} if evidence_dir_safe else
                       {"3-verify/qa": ["evidence directory escapes loop-project"]})
            for filename in secs:
                path = p("3-verify/qa", filename)
                text = read(path) if os.path.isfile(path) and not os.path.islink(path) else ""
                task_match = re.search(r"^#\s+SEC-\d{3}\s+.+\s+(TASK-\d{3})\b",
                                       text, re.MULTILINE)
                tid = task_match.group(1) if task_match else None
                problems = (validate_qa_report(text, tid, "SEC") if tid else
                            ["SEC heading does not name a task"])
                if tid not in tasks:
                    problems.append("SEC report names an unknown task")
                if problems:
                    invalid[filename] = problems
                else:
                    valid_tasks.add(tid)
            missing = sorted(set(tasks) - valid_tasks)
            r.add("adversary evidence valid", bool(secs) and not invalid and not missing,
                  "invalid: %s; missing tasks: %s"
                  % (", ".join(sorted(invalid)) or "none", ", ".join(missing) or "none"), "1")
            for filename, problems in sorted(invalid.items()):
                for problem in problems[:4]:
                    print("    - %s: %s" % (filename, problem))
        if role_enabled(state, "ui-critic"):
            evidence_dir_safe = owned_directory_is_confined("3-verify/qa")
            uis = artifacts_in("3-verify/qa", "UI-") if evidence_dir_safe else []
            valid_tasks = set()
            invalid = ({} if evidence_dir_safe else
                       {"3-verify/qa": ["evidence directory escapes loop-project"]})
            for filename in uis:
                path = p("3-verify/qa", filename)
                text = read(path) if os.path.isfile(path) and not os.path.islink(path) else ""
                task_match = re.search(r"^#\s+UI-\d{3}\s+.+\s+(TASK-\d{3})\b",
                                       text, re.MULTILINE)
                tid = task_match.group(1) if task_match else None
                problems = (validate_ui_report(text, tid) if tid else
                            ["UI heading does not name a task"])
                if tid not in tasks:
                    problems.append("UI report names an unknown task")
                if problems:
                    invalid[filename] = problems
                else:
                    valid_tasks.add(tid)
            missing = sorted(set(tasks) - valid_tasks)
            r.add("UI critique evidence valid", bool(uis) and not invalid and not missing,
                  "invalid: %s; missing tasks: %s"
                  % (", ".join(sorted(invalid)) or "none", ", ".join(missing) or "none"), "1")
            for filename, problems in sorted(invalid.items()):
                for problem in problems[:4]:
                    print("    - %s: %s" % (filename, problem))
        if role_enabled(state, "product-owner"):
            evidence_dir_safe = owned_directory_is_confined("3-verify/verdicts")
            pos = artifacts_in("3-verify/verdicts", "PO-") if evidence_dir_safe else []
            invalid = ({} if evidence_dir_safe else
                       {"3-verify/verdicts": ["evidence directory escapes loop-project"]})
            for filename in pos:
                path = p("3-verify/verdicts", filename)
                text = read(path) if os.path.isfile(path) and not os.path.islink(path) else ""
                problems = validate_product_owner_report(text)
                if problems:
                    invalid[filename] = problems
            r.add("business acceptance valid", bool(pos) and not invalid,
                  "invalid: %s" % (", ".join(sorted(invalid)) or "none"), "1")
            for filename, problems in sorted(invalid.items()):
                for problem in problems[:4]:
                    print("    - %s: %s" % (filename, problem))

    return r


def cmd_approve(args):
    state = require_state()
    gate = args.gate.lower()
    if gate not in GATES:
        die("gate must be one of: %s" % ", ".join(GATES))
    if gate not in state.get("human_gates", []):
        die("%s is not configured as a human gate" % gate.upper())
    if state["gates"][gate]["passed"]:
        die("%s has already passed" % gate.upper())
    if not args.by.strip():
        die("approver identity must not be blank")

    r = gate_checks(gate, state)
    code = r.render("approve %s" % gate.upper())
    if code:
        print("\nRefusing approval while gate checks are failing.")
        return code

    state.setdefault("approvals", {})[gate] = {
        "approved": True,
        "by": args.by.strip(),
        "at": now(),
        "note": (args.note or "").strip(),
        "fingerprint": approval_fingerprint(gate, state),
    }
    save_state(state)
    ledger("%s approved by %s.%s" % (
        gate.upper(), args.by.strip(),
        ("\nNote: " + args.note.strip()) if args.note else ""))
    print("\n%s human approval recorded for %s." % (gate.upper(), args.by.strip()))
    print("Run: loop.py gate %s --pass" % gate)
    return 0


def cmd_gate(args):
    state = require_state()
    gate = args.gate.lower()
    if gate not in GATES:
        die("gate must be one of: %s" % ", ".join(GATES))

    previous = {"g0": None, "g1": "g0", "g2": "g1", "g3": "g2"}[gate]
    if args.pass_gate and state["gates"][gate]["passed"]:
        die("%s has already passed" % gate.upper())
    if args.pass_gate and state.get("status") != "ACTIVE":
        die("gates can only pass while the loop is ACTIVE")
    if args.pass_gate and previous and not state["gates"][previous]["passed"]:
        die("%s requires %s to have passed" % (gate.upper(), previous.upper()))
    approval = state.get("approvals", {}).get(gate, {})
    if args.pass_gate and gate in state.get("human_gates", []) and not approval.get("approved"):
        die("%s requires human approval. Run: loop.py approve %s --by <name>"
            % (gate.upper(), gate))
    if args.pass_gate and gate in state.get("human_gates", []):
        current_fingerprint = approval_fingerprint(gate, state)
        if approval.get("fingerprint") != current_fingerprint:
            die("%s approval is stale because approved artifacts changed; approve it again"
                % gate.upper())

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
        state["frozen_roles"] = list(enabled_roles(state))
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
    if state.get("status") != "ACTIVE":
        die("only an ACTIVE loop can be blocked")
    if not args.reason.strip():
        die("blocking reason must not be blank")
    state["status"] = "BLOCKED"
    state["blocked_reason"] = args.reason.strip()
    save_state(state)
    ledger("BLOCKED: %s\n\nOptions and recommendation belong here." % args.reason)
    print("Status set to BLOCKED.")
    print("Write the options and your recommendation into /loop-project/ledger.md, then stop.")
    return 0


def cmd_unblock(args):
    state = require_state()
    if state.get("status") != "BLOCKED":
        die("the loop is not BLOCKED")
    decision = args.decision.strip()
    approver = args.by.strip()
    if not decision or not approver:
        die("--by and --decision must not be blank")
    record = {
        "by": approver,
        "at": now(),
        "decision": decision,
        "previous_reason": state.get("blocked_reason"),
    }
    state.setdefault("unblocks", []).append(record)
    state["status"] = "ACTIVE"
    state["blocked_reason"] = None
    save_state(state)
    ledger("Loop unblocked by %s.\nDecision: %s\nPrevious block: %s"
           % (approver, decision, record["previous_reason"] or "not recorded"))
    print("Loop resumed by %s. The decision is recorded in loop.json and ledger.md." % approver)
    print("Blocked tasks remain open until the Judge records REWORK or PASS.")
    return 0


def cmd_migrate(args):
    """Explicitly attest legacy state that predates frozen rosters and Git baselines."""
    state = require_state()
    if state.get("status") != "ACTIVE":
        die("legacy migration requires an ACTIVE loop")
    approver = args.by.strip()
    reason = args.reason.strip()
    if not approver or not reason:
        die("--by and --reason must not be blank")

    migrated = []
    if state.get("gates", {}).get("g0", {}).get("passed") and not state.get("frozen_roles"):
        state["frozen_roles"] = list((state.get("roles") or {}).get("enabled") or CORE_ROLES)
        migrated.append("approved role roster")

    missing_baselines = [
        tid for tid, task in state.get("tasks", {}).items()
        if not git_commit_exists(task.get("base_sha"))
    ]
    if missing_baselines:
        code, head, _ = git("rev-parse", "HEAD")
        if code != 0 or not git_commit_exists(head.strip()):
            die("legacy task migration requires a valid Git HEAD")
        for tid in missing_baselines:
            task = state["tasks"][tid]
            task["base_sha"] = head.strip()
            task["baseline_migrated_at"] = now()
            task["baseline_migrated_by"] = approver
            task["verdict"] = None
            for field in ("result_sha", "result_fingerprint", "result_files",
                          "mechanical_verification", "evidence_hashes",
                          "verdict_at", "qa_file", "verdict_file", "rework_files"):
                task.pop(field, None)
        migrated.append("task baselines: %s" % ", ".join(sorted(missing_baselines)))

    if not migrated:
        die("this loop has no legacy roster or task baseline state to migrate")
    record = {
        "by": approver,
        "at": now(),
        "reason": reason,
        "changes": migrated,
    }
    state.setdefault("migrations", []).append(record)
    save_state(state)
    ledger("Legacy state migration approved by %s.\nReason: %s\nChanges: %s"
           % (approver, reason, "; ".join(migrated)))
    print("Legacy loop state migrated by %s." % approver)
    for change in migrated:
        print("  - " + change)
    print("Migrated task baselines accept the current Git HEAD as the new boundary; "
          "those tasks must be re-verified.")
    return 0


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="loop.py", description="Project Loop state machine")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="scaffold a new evidence workspace")
    p.add_argument("--brownfield", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("status", help="show phase, gates, roles, and open tasks")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("roles", help="select the authority roster before G0")
    p.add_argument("--list", action="store_true", help="show the roster and what is enabled")
    p.add_argument("--recommend", action="store_true",
                   help="propose a set from the shape of this project")
    p.add_argument("--preset", help="core (5), standard (8), product (12), growth (15), full (18)")
    p.add_argument("--enable", help="comma-separated role keys to turn on")
    p.add_argument("--disable", help="comma-separated role keys to turn off")
    p.add_argument("--vertical",
                   help="the Domain Analyst's vertical, or 'list' to see the options")
    p.add_argument("--confirm", action="store_true",
                   help="accept the current set as a deliberate choice")
    p.set_defaults(fn=cmd_roles)

    p = sub.add_parser("task", help="create or list baseline-anchored tasks")
    p.add_argument("action", choices=["new", "list"])
    p.add_argument("title", nargs="?")
    p.set_defaults(fn=cmd_task)

    p = sub.add_parser("reuse", help="search the registry and tree before building")
    p.add_argument("query", help='what you are about to build, e.g. "currency format"')
    p.set_defaults(fn=cmd_reuse)

    p = sub.add_parser("verify", help="run deterministic task evidence checks")
    p.add_argument("task")
    p.set_defaults(fn=cmd_verify)

    p = sub.add_parser("cycle", help="retired; use the evidence-bearing verdict command")
    p.add_argument("task")
    p.set_defaults(fn=cmd_cycle)

    p = sub.add_parser("verdict", help="record PASS, REWORK, or BLOCKED with evidence")
    p.add_argument("task")
    p.add_argument("outcome", choices=["pass", "rework", "blocked"])
    p.add_argument("--file", required=True, help="Judge verdict artifact")
    p.add_argument("--qa", help="Tester QA artifact (required for PASS)")
    p.add_argument("--order", action="append",
                   help="rework order artifact; repeat once per order (required for REWORK)")
    p.add_argument("--reason", help="decision the human must make (required for BLOCKED)")
    p.set_defaults(fn=cmd_verdict)

    p = sub.add_parser("gate", help="check or pass an ordered lifecycle gate")
    p.add_argument("gate", choices=GATES)
    p.add_argument("--check", action="store_true")
    p.add_argument("--pass", dest="pass_gate", action="store_true")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("approve", help="bind a human identity to checked gate artifacts")
    p.add_argument("gate", choices=GATES)
    p.add_argument("--by", required=True, help="human approver name or stable identifier")
    p.add_argument("--note", help="optional approval context")
    p.set_defaults(fn=cmd_approve)

    p = sub.add_parser("block", help="stop the loop with a specific decision need")
    p.add_argument("reason")
    p.set_defaults(fn=cmd_block)

    p = sub.add_parser("unblock", help="resume after an attributed human decision")
    p.add_argument("--by", required=True, help="human decision-maker name or stable identifier")
    p.add_argument("--decision", required=True, help="decision that resolves the recorded block")
    p.set_defaults(fn=cmd_unblock)

    p = sub.add_parser("migrate", help="attest legacy role and task baselines")
    p.add_argument("--by", required=True, help="human approver name or stable identifier")
    p.add_argument("--reason", required=True, help="why the current legacy state is accepted")
    p.set_defaults(fn=cmd_migrate)

    args = ap.parse_args()
    if not getattr(args, "fn", None):
        ap.print_help()
        return 2
    with project_lock():
        return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
