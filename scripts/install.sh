#!/usr/bin/env bash
# Project Loop installer.
#
# Installs the skill into whichever agents you name. The Agent Skills format is shared; the
# discovery paths are not, which is the only reason this script exists.
#
#   ./scripts/install.sh --target claude              user scope (default)
#   ./scripts/install.sh --target codex --scope project
#   ./scripts/install.sh --target all --scope project
#   ./scripts/install.sh --target claude --uninstall
#
# Targets: claude, codex, cursor, all
# Scopes:  user (default), project

set -euo pipefail

TARGET="claude"
SCOPE="user"
UNINSTALL=0
DRY=0

SKILL_NAME="project-loop"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SRC="$REPO_ROOT/plugins/project-loop/skills/$SKILL_NAME"
AGENTS_SRC="$REPO_ROOT/plugins/project-loop/agents"
ADAPTERS="$REPO_ROOT/adapters"

c_ok()   { printf '  \033[32mok\033[0m    %s\n' "$1"; }
c_info() { printf '  \033[36minfo\033[0m  %s\n' "$1"; }
c_warn() { printf '  \033[33mwarn\033[0m  %s\n' "$1"; }
c_err()  { printf '  \033[31merror\033[0m %s\n' "$1" >&2; }

usage() {
  sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)    TARGET="${2:-}"; shift 2 ;;
    --scope)     SCOPE="${2:-}";  shift 2 ;;
    --uninstall) UNINSTALL=1;     shift ;;
    --dry-run)   DRY=1;           shift ;;
    -h|--help)   usage ;;
    *) c_err "unknown argument: $1"; exit 2 ;;
  esac
done

case "$TARGET" in claude|codex|cursor|all) ;; *) c_err "--target must be claude, codex, cursor or all"; exit 2 ;; esac
case "$SCOPE"  in user|project) ;;          *) c_err "--scope must be user or project"; exit 2 ;; esac

[[ -f "$SKILL_SRC/SKILL.md" ]] || { c_err "skill not found at $SKILL_SRC — run this from the repository"; exit 2; }

if ! command -v python3 >/dev/null 2>&1; then
  c_warn "python3 not found. loop.py drives the state machine and the deterministic checks;"
  c_warn "without it the loop runs on model judgement alone, which is slower and less reliable."
fi

run() { if [[ $DRY -eq 1 ]]; then echo "    would: $*"; else "$@"; fi; }

install_skill() {
  local dest="$1" label="$2"
  if [[ $UNINSTALL -eq 1 ]]; then
    if [[ -d "$dest/$SKILL_NAME" ]]; then
      run rm -rf "$dest/$SKILL_NAME"
      c_ok "removed $label -> $dest/$SKILL_NAME"
    else
      c_info "$label: nothing installed at $dest/$SKILL_NAME"
    fi
    return
  fi
  run mkdir -p "$dest"
  run rm -rf "$dest/$SKILL_NAME"
  run cp -R "$SKILL_SRC" "$dest/$SKILL_NAME"
  [[ $DRY -eq 1 ]] || chmod +x "$dest/$SKILL_NAME/scripts/loop.py" 2>/dev/null || true
  c_ok "$label -> $dest/$SKILL_NAME"
}

install_agents() {
  local dest="$1"
  [[ $UNINSTALL -eq 1 ]] && return 0
  run mkdir -p "$dest"
  for f in "$AGENTS_SRC"/*.md; do
    run cp "$f" "$dest/"
  done
  c_ok "subagents -> $dest (5 roles)"
}

place_adapter() {
  local src="$1" dest="$2" label="$3"
  [[ $UNINSTALL -eq 1 ]] && return 0
  if [[ -f "$dest" ]]; then
    c_warn "$label already exists at $dest — not overwriting. Merge by hand:"
    c_warn "  $src"
    return 0
  fi
  run mkdir -p "$(dirname "$dest")"
  run cp "$src" "$dest"
  c_ok "$label -> $dest"
}

echo ""
echo "Project Loop — $([[ $UNINSTALL -eq 1 ]] && echo uninstall || echo install) ($TARGET, $SCOPE scope)"
echo ""

do_claude() {
  echo "Claude Code"
  if [[ "$SCOPE" == "user" ]]; then
    install_skill "$HOME/.claude/skills" "skill (user)"
    install_agents "$HOME/.claude/agents"
  else
    install_skill ".claude/skills" "skill (project)"
    install_agents ".claude/agents"
    c_info "project scope loads only after you accept the workspace trust prompt"
  fi
  c_info "alternative: /plugin marketplace add <owner>/project-loop && /plugin install project-loop@project-loop"
  echo ""
}

do_codex() {
  echo "OpenAI Codex"
  if [[ "$SCOPE" == "user" ]]; then
    install_skill "$HOME/.agents/skills" "skill (user)"
  else
    install_skill ".agents/skills" "skill (project)"
    place_adapter "$ADAPTERS/codex/AGENTS.md" "AGENTS.md" "AGENTS.md"
  fi
  c_info "Codex has no subagents — roles run sequentially. See references/portability.md"
  echo ""
}

do_cursor() {
  echo "Cursor"
  if [[ "$SCOPE" == "user" ]]; then
    install_skill "$HOME/.cursor/skills" "skill (user)"
    c_warn "Cursor rules are project-scoped; run with --scope project to add the rule file"
  else
    install_skill ".cursor/skills" "skill (project)"
    place_adapter "$ADAPTERS/cursor/project-loop.mdc" ".cursor/rules/project-loop.mdc" "rule"
  fi
  echo ""
}

case "$TARGET" in
  claude) do_claude ;;
  codex)  do_codex ;;
  cursor) do_cursor ;;
  all)    do_claude; do_codex; do_cursor ;;
esac

if [[ $UNINSTALL -eq 1 ]]; then
  echo "Done. Your /loop-project directories were left alone — they are project state, not installed files."
  exit 0
fi

cat <<'NEXT'
Done.

Verify it loaded:
  Claude Code   /plugin  or  claude plugin list
  Codex/Cursor  ask the agent to list its available skills

Start a loop in a project directory:
  Say "run the project loop" and describe what you want built.

Or scaffold the state directory yourself:
  python3 <skill-path>/scripts/loop.py init            new project
  python3 <skill-path>/scripts/loop.py init --brownfield   existing codebase
NEXT
