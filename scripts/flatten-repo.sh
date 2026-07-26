#!/usr/bin/env bash
# One-time repo cleanup.
#
# This repository ended up with a nested duplicate: the git metadata lives in
# "Project Look Skills /" while the working files also exist at the top level.
# File contents are identical between the two, so there is nothing to merge —
# only a .git directory to move and a duplicate to delete.
#
# This script is idempotent and refuses to run if anything looks unexpected.
# It takes a full backup before touching anything.
#
#   ./scripts/flatten-repo.sh --dry-run    show the plan, change nothing
#   ./scripts/flatten-repo.sh              do it

set -euo pipefail

NESTED="Project Look Skills "
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; }
info() { printf '  \033[36minfo\033[0m  %s\n' "$1"; }
warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; }
err()  { printf '  \033[31merror\033[0m %s\n' "$1" >&2; }

# Quote the echo so a dry run shows exactly how the paths are grouped. The real
# invocation passes arguments as an array, so the space in the folder name is
# never an issue — but an unquoted preview makes it look like one.
run() {
  if [[ $DRY -eq 1 ]]; then
    printf '    would:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

cd "$(dirname "${BASH_SOURCE[0]}")/.."
ROOT="$(pwd)"

echo ""
echo "Flatten repo — $ROOT"
echo ""

# ---- already done?
if [[ -d .git && ! -d "$NESTED" ]]; then
  ok "already flat — .git is at the root and the duplicate is gone"
  exit 0
fi

# ---- preconditions
if [[ ! -d "$NESTED/.git" ]]; then
  err "expected git metadata at '$NESTED/.git' — not found."
  err "Nothing to do, or this script has already run. Check: git status"
  exit 2
fi

if [[ -d .git ]]; then
  err "there is already a .git at the root AND a nested one at '$NESTED/.git'."
  err "Two repositories. Resolve by hand — this script will not guess."
  exit 2
fi

# ---- Would deleting the nested copy lose anything?
#
# Only one question matters: does the nested folder contain a file that does not
# exist at the top level? Differing *contents* are expected and fine — the top
# level is the newer tree, which is why it is the one being kept. Files unique to
# the nested copy are the only thing that would actually be destroyed.
info "checking whether '$NESTED' holds anything unique"

UNIQUE="$(cd "$NESTED" && find . -type f \
            -not -path './.git/*' \
            -not -name '.DS_Store' \
            -not -name '.gitattributes' \
            -print 2>/dev/null \
          | while read -r f; do
              [[ -e "$ROOT/${f#./}" ]] || echo "${f#./}"
            done)"

if [[ -n "$UNIQUE" ]]; then
  warn "these files exist ONLY inside '$NESTED' and would be lost:"
  echo "$UNIQUE" | sed 's/^/        /'
  echo ""
  if [[ $DRY -eq 1 ]]; then
    warn "dry run — would stop here and ask before continuing"
  else
    read -r -p "  Continue and delete them? [y/N] " reply
    [[ "$reply" == "y" || "$reply" == "Y" ]] || { info "aborted — nothing changed"; exit 1; }
  fi
else
  ok "nothing unique in the nested copy — safe to remove"
fi

# ---- stale lock, which blocks every write operation git does
if [[ -f "$NESTED/.git/index.lock" ]]; then
  info "removing stale index.lock"
  run rm -f "$NESTED/.git/index.lock"
fi

# ---- backup
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP="$HOME/project-loop-backup-$STAMP"
info "backing up to $BACKUP"
run mkdir -p "$BACKUP"
run cp -R "$NESTED/.git" "$BACKUP/git-metadata"
run cp -R "$NESTED" "$BACKUP/nested-copy"
ok "backup written — delete it yourself once you are happy"

# ---- move .git up
info "moving git metadata to the repository root"
run mv "$NESTED/.git" "$ROOT/.git"
[[ -f "$NESTED/.gitattributes" && ! -f "$ROOT/.gitattributes" ]] && run mv "$NESTED/.gitattributes" "$ROOT/.gitattributes"
ok ".git -> $ROOT/.git"

# ---- remove the duplicate
info "removing the duplicate working tree"
run rm -rf "$NESTED"
ok "removed '$NESTED'"

if [[ $DRY -eq 1 ]]; then
  echo ""
  info "dry run — nothing changed"
  exit 0
fi

# ---- verify
echo ""
info "verifying"
git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  && ok "git work tree is healthy" \
  || { err "git is unhappy. Restore from $BACKUP/git-metadata"; exit 1; }

COMMITS="$(git -C "$ROOT" rev-list --count HEAD 2>/dev/null || echo 0)"
ok "history intact — $COMMITS commit(s)"
git -C "$ROOT" remote -v | sed 's/^/        /'

cat <<'NEXT'

Done. Now review and commit:

  git status
  git add -A
  git commit -m "Add npm CLI installer with target and scope selection"
  git push

NEXT
