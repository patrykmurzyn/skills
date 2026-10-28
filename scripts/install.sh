#!/usr/bin/env bash
# Link every skill in this repo into the agent skill folders.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/install.sh [--dry-run] [--uninstall] [--target agents|claude|all]

Symlink each skill folder (skills/**/SKILL.md, fixtures in evals/ excluded) into:
  agents  ~/.agents/skills   Codex, Cursor and other Agent Skills clients
  claude  ~/.claude/skills   Claude Code

Re-running is safe. Links into this repo whose skill no longer exists are removed.
A name already taken by anything else is skipped, never overwritten.

Options:
  --dry-run     Print what would change; change nothing.
  --uninstall   Remove only the links that point into this repo.
  --target T    agents, claude or all (default: all).
  -h, --help    Show this help.

Exit codes: 0 done, 1 bad arguments, 2 one or more names were taken (skipped).
EOF
}

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
dry=0
mode=install
target=all

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry=1 ;;
    --uninstall) mode=uninstall ;;
    --target) target="${2:-}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Error: unknown option '$1'." >&2; usage >&2; exit 1 ;;
  esac
  shift
done

case "$target" in
  agents) dests=("$HOME/.agents/skills") ;;
  claude) dests=("$HOME/.claude/skills") ;;
  all) dests=("$HOME/.agents/skills" "$HOME/.claude/skills") ;;
  *) echo "Error: --target must be agents, claude or all. Received: '$target'." >&2; exit 1 ;;
esac

prefix=""
(( dry )) && prefix="[dry-run] "
do_run() { (( dry )) || "$@"; }

conflicts=0
for dest in "${dests[@]}"; do
  if [[ ! -d "$dest" ]]; then
    echo "${prefix}create   $dest"
    do_run mkdir -p "$dest"
  fi

  # Remove this repo's links: all of them on uninstall, dangling ones on install.
  for link in "$dest"/*; do
    [[ -L "$link" ]] || continue
    [[ "$(readlink "$link")" == "$repo/skills/"* ]] || continue
    if [[ $mode == uninstall || ! -e "$link" ]]; then
      echo "${prefix}removed  $link"
      do_run rm "$link"
    fi
  done
  [[ $mode == uninstall ]] && continue

  while IFS= read -r skill_md; do
    src="$(dirname "$skill_md")"
    link="$dest/$(basename "$src")"
    if [[ -L "$link" && "$(readlink "$link")" == "$src" ]]; then
      echo "${prefix}ok       $link"
    elif [[ -e "$link" || -L "$link" ]]; then
      echo "${prefix}conflict $link already exists and is not this repo's link; skipped" >&2
      conflicts=$((conflicts + 1))
    else
      echo "${prefix}linked   $link -> $src"
      do_run ln -s "$src" "$link"
    fi
  done < <(find "$repo/skills" -name SKILL.md -type f -not -path '*/evals/*' | sort)
done

if (( conflicts > 0 )); then
  echo "Skipped $conflicts taken name(s). Rename the skill or remove the existing entry, then re-run." >&2
  exit 2
fi
