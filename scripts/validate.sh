#!/usr/bin/env bash
# Validate every skill in this repo with the repo's required fields.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/validate.sh [--with-skills-ref] [--format text|json]

Runs skill-testing's validate_skill.py on every skill (fixtures in evals/ excluded),
requiring license, metadata.author, metadata.version and metadata.status, and
rejecting frontmatter fields outside the spec (--strict-spec).

Options:
  --with-skills-ref  Also run the reference validator from agentskills/agentskills
                     (needs network; fetched with uvx).
  --format FORMAT    text (default) or json.
  -h, --help         Show this help.

Exit codes: 0 valid, 1 errors found, 2 bad arguments.
EOF
}

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
validator="$repo/skills/authoring/skill-testing/scripts/validate_skill.py"
with_ref=0
format=text

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-skills-ref) with_ref=1 ;;
    --format) format="${2:-}"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Error: unknown option '$1'." >&2; usage >&2; exit 2 ;;
  esac
  shift
done

skills=()
while IFS= read -r skill_md; do
  skills+=("$(dirname "$skill_md")")
done < <(find "$repo/skills" -name SKILL.md -type f -not -path '*/evals/*' | sort)

if (( ${#skills[@]} == 0 )); then
  echo "No skills found under $repo/skills." >&2
  exit 0
fi

status=0

# A SKILL.md nested inside a skill folder (e.g. an eval fixture) is loaded as a real
# skill by agents that scan recursively, such as Codex. Fixtures use SKILL.fixture.md.
for skill in "${skills[@]}"; do
  while IFS= read -r nested; do
    echo "error: nested SKILL.md would load as a separate skill: ${nested#"$repo"/}" >&2
    echo "       rename it to SKILL.fixture.md (see evals/files/README.md)" >&2
    status=1
  done < <(find "$skill" -mindepth 2 -name SKILL.md)
done

uv run --quiet "$validator" --strict-spec \
  --require license,metadata.author,metadata.version,metadata.status \
  --format "$format" "${skills[@]}" || status=$?

if (( with_ref )); then
  for skill in "${skills[@]}"; do
    uvx --quiet --from 'git+https://github.com/agentskills/agentskills#subdirectory=skills-ref' \
      skills-ref validate "$skill" >&2 || status=1
  done
fi

exit "$status"
