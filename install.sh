#!/usr/bin/env bash
set -euo pipefail

skill_name="minimax-music3"
force=0
dest_root="${CODEX_HOME:-$HOME/.codex}/skills"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage: ./install.sh [--dest SKILLS_DIR] [--force]

Install the minimax-music3 skill into SKILLS_DIR/minimax-music3.
By default, SKILLS_DIR is $CODEX_HOME/skills or ~/.codex/skills.
An existing installation is preserved unless --force is provided.
EOF
}

while (($#)); do
  case "$1" in
    --dest)
      (($# >= 2)) || { usage >&2; exit 2; }
      dest_root="$2"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

dest_root="${dest_root/#\~/$HOME}"
dest_root="$(mkdir -p -- "$dest_root" && cd -- "$dest_root" && pwd)"
destination="$dest_root/$skill_name"

if [[ -e "$destination" || -L "$destination" ]] && ((force == 0)); then
  printf 'Existing skill preserved: %s\n' "$destination"
  printf 'Use --force to back it up and replace it.\n'
  exit 0
fi

staging="$(mktemp -d "$dest_root/.${skill_name}.tmp.XXXXXX")"
backup=""
cleanup() {
  if [[ -n "$staging" && -d "$staging" ]]; then
    rm -rf -- "$staging"
  fi
}
trap cleanup EXIT

cp -- \
  "$script_dir/SKILL.md" \
  "$script_dir/SKILL.zh-TW.md" \
  "$script_dir/LICENSE" \
  "$script_dir/LICENSE-MINIMAX-MUSIC3.md" \
  "$script_dir/THIRD_PARTY_NOTICES.md" \
  "$staging/"
cp -R -- "$script_dir/scripts" "$script_dir/assets" "$script_dir/references" "$staging/"

if [[ -e "$destination" || -L "$destination" ]]; then
  backup="$destination.backup.$(date +%Y%m%d-%H%M%S).$$"
  mv -- "$destination" "$backup"
fi

if ! mv -- "$staging" "$destination"; then
  if [[ -n "$backup" && ( -e "$backup" || -L "$backup" ) ]]; then
    mv -- "$backup" "$destination"
  fi
  printf 'Could not install skill to %s\n' "$destination" >&2
  exit 1
fi
staging=""

printf 'Installed %s to %s\n' "$skill_name" "$destination"
if [[ -n "$backup" ]]; then
  printf 'Previous installation backed up to %s\n' "$backup"
fi
