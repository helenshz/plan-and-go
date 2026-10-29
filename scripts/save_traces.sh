#!/usr/bin/env bash
# Copy Claude Code session transcripts for this project into traces/claude-code/
# and scan them for secrets. Exits non-zero if anything looks like a key, so the
# copy is never committed blindly.
#
# Usage: scripts/save_traces.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dest="$repo_root/traces/claude-code"
projects_dir="$HOME/.claude/projects"

# Claude Code names project dirs after the working directory path with '/' and
# ' ' replaced by '-'. Sessions may start in the repo or in its parent folder.
parent_slug="$(dirname "$repo_root" | sed 's#[/ ]#-#g')"

mkdir -p "$dest"
copied=0
for dir in "$projects_dir/$parent_slug" "$projects_dir/$parent_slug"-*; do
    [ -d "$dir" ] || continue
    name="$(basename "$dir")"
    mkdir -p "$dest/$name"
    # -u: only overwrite when the source is newer (sessions keep growing)
    for f in "$dir"/*.jsonl; do
        [ -e "$f" ] || continue
        cp -u "$f" "$dest/$name/"
        copied=$((copied + 1))
    done
done
echo "Copied $copied transcript(s) to ${dest#"$repo_root"/}"

# Common API key / token formats: Anthropic, OpenAI, OpenRouter, Google, GitHub,
# GitLab, AWS, Hugging Face, plus generic bearer tokens and key assignments.
pattern='sk-ant-[A-Za-z0-9_-]{20,}|sk-or-v1-[A-Za-z0-9]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}|gh[pousr]_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20}|AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{30,}|Bearer [A-Za-z0-9._-]{20,}|(API_KEY|api_key|apiKey|SECRET|TOKEN)["'"'"']?\s*[:=]\s*["'"'"']?[A-Za-z0-9_-]{16,}'

if hits="$(grep -rEoHn "$pattern" "$dest" 2>/dev/null)"; then
    echo "Redacting possible secrets (file:line, masked):" >&2
    # Print file:line and a masked match only, never the full secret
    echo "$hits" | sed -E "s#^${repo_root}/##; s/^([^:]+:[0-9]+):(.{8}).*/\1: \2********/" >&2
    # Redact in the copies only; re-running is safe because sources are re-copied
    # only when newer and are then redacted again.
    echo "$hits" | cut -d: -f1 | sort -u | while read -r f; do
        PATTERN="$pattern" perl -pi -e 's/$ENV{PATTERN}/[REDACTED]/g' "$f"
    done
fi
if grep -rEq "$pattern" "$dest" 2>/dev/null; then
    echo "Secrets still present after redaction — do not commit." >&2
    exit 1
fi
echo "No secrets left in traces/."
