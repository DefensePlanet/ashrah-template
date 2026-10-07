#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: new-capsule.sh <slug> [template_type]"
  echo "  slug: Project identifier (e.g., 'my-project')"
  echo "  template_type: 'full' (default) or 'automation'"
  exit 1
fi

SLUG="$1"
TEMPLATE_TYPE="${2:-full}"
ROOT="${CATALYST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"

case "$TEMPLATE_TYPE" in
  "full")
    TEMPLATE="$ROOT/recipes/capsule-template"
    ;;
  "automation")
    TEMPLATE="$ROOT/recipes/automation-capsule-template"
    ;;
  *)
    echo "Error: Unknown template type '$TEMPLATE_TYPE'. Use 'full' or 'automation'."
    exit 1
    ;;
esac

DEST="$ROOT/capsules/$SLUG"

if [ -d "$DEST" ]; then
  echo "Capsule already exists: $DEST"
  exit 0
fi

mkdir -p "$DEST"
rsync -a "$TEMPLATE/" "$DEST/"

# Rename *.template files to their real names (except .mcp.json.template)
find "$DEST" -type f -name "*.template" ! -name ".mcp.json.template" | while read -r f; do
  new="${f%.template}"
  mv "$f" "$new"
done

# Generate capsule.map.json with actual values
if [[ -f "$DEST/capsule.map.json" ]]; then
  if [[ "$TEMPLATE_TYPE" == "full" ]]; then
    sed -i '' "s/{{ project_name }}/TODO: $SLUG/g; s/{{ project_slug }}/$SLUG/g" "$DEST/capsule.map.json"
  else
    sed -i '' "s/{{ workflow_name }}/TODO: $SLUG/g; s/{{ workflow_slug }}/$SLUG/g" "$DEST/capsule.map.json"
  fi
fi

# Generate framework structure automatically
echo "Generating framework structure..."
python3 "$ROOT/tools/generate-framework.py" "$SLUG" --builderOS-root "$ROOT"

# Refresh shared MCP configs so Claude & Codex see new state
if ! python3 "$ROOT/tools/sync_mcp_configs.py" >/dev/null 2>&1; then
  echo "WARNING: sync_mcp_configs.py failed; run manually to refresh MCP settings." >&2
fi

echo "Created $TEMPLATE_TYPE capsule at: $DEST"
echo "✅ Framework structure generated automatically"
echo ""
echo "Next steps:"
if [[ "$TEMPLATE_TYPE" == "automation" ]]; then
  echo "  1) Edit $DEST/spec/workflow.yaml"
  echo "  2) Configure triggers in $DEST/spec/triggers.md"  
  echo "  3) Define outputs in $DEST/spec/outputs.md"
else
  echo "  1) Edit $DEST/spec/requirements.yaml"
  echo "  2) (Optional) copy $DEST/.mcp.json.template to $DEST/.mcp.json and configure MCPs"
fi
echo "  3) Customize framework files:"
echo "     - standards.yaml (quality standards)"
echo "     - product.yaml (roadmap & vision)"
echo "     - specs/current.yaml & specs/next.yaml"
echo "     - context/*.md (decisions, patterns, evolution)"
echo "  4) Configure secrets in $DEST/.secrets (copy from .secrets.template)"
echo "  5) Open the capsule in Cursor and run Claude Code from there"




