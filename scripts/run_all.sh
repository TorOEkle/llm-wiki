#!/usr/bin/env bash
# run_all.sh — fetch macro data and regenerate wiki articles
# Place this in scripts/ and run from the repo root:
#   bash scripts/run_all.sh
#
# Options:
#   --no-llm      Skip Gemini, leave placeholders (good for testing data only)
#   --fetch-only  Only fetch data, skip article generation
#   --article X   Regenerate one article only (e.g. --article norway)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Parse flags ──────────────────────────────────────────────────────────────
NO_LLM=""
FETCH_ONLY=0
ARTICLE=""

for arg in "$@"; do
  case $arg in
    --no-llm)     NO_LLM="--no-llm" ;;
    --fetch-only) FETCH_ONLY=1 ;;
    --article)    shift; ARTICLE="--article $1" ;;
    --article=*)  ARTICLE="--article ${arg#*=}" ;;
  esac
done

# ── Check uv is available ────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
  echo "ERROR: uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# ── Sync venv via uv ─────────────────────────────────────────────────────────
echo "Syncing dependencies with uv..."
uv sync --project "$REPO_ROOT" --quiet
PYTHON="$REPO_ROOT/.venv/bin/python"

# ── Step 1: Fetch macro data ─────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "  Step 1: Fetching macro data"
echo "════════════════════════════════════════"
$PYTHON "$SCRIPT_DIR/fetch_macro.py"

if [ $FETCH_ONLY -eq 1 ]; then
  echo ""
  echo "Done (--fetch-only, skipping article generation)."
  exit 0
fi

# ── Step 2: Generate articles ────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "  Step 2: Generating articles"
echo "════════════════════════════════════════"
$PYTHON "$SCRIPT_DIR/generate_articles.py" $NO_LLM $ARTICLE

# ── Step 3: Git commit (optional, uncomment to enable) ───────────────────────
# echo ""
# echo "════════════════════════════════════════"
# echo "  Step 3: Committing to git"
# echo "════════════════════════════════════════"
# cd "$REPO_ROOT"
# git add docs/ _data/
# git commit -m "chore: auto-update macro data $(date +%Y-%m-%d)"
# git push

echo ""
echo "All done."
