#!/bin/bash
echo "=== LANE SYSTEM VERIFICATION REPORT ==="
echo ""
echo "Checking active operational files..."
echo ""

echo "1. Agent Configs (excluding CHANGELOG):"
AGENT_COUNT=$(find {{CATALYST_ROOT}}/.claude/agents {{CATALYST_ROOT}}/global/claude-config/agents -name "*.md" -type f 2>/dev/null | grep -v "CHANGELOG" | xargs grep -l -i "lane" 2>/dev/null | wc -l)
echo "   Files with lane references: $AGENT_COUNT"

echo ""
echo "2. Tools (excluding archived/backups):"
TOOL_COUNT=$(find {{CATALYST_ROOT}}/tools -type f \( -name "*.py" -o -name "*.sh" \) 2>/dev/null | grep -v "versions/" | grep -v ".backup" | grep -v ".lane_backup" | xargs grep -l -i "fast_lane\|deep_lane" 2>/dev/null | wc -l)
echo "   Files with lane references: $TOOL_COUNT"

echo ""
echo "3. Source Code:"
SRC_COUNT=$(find {{CATALYST_ROOT}}/src -name "*.py" -type f 2>/dev/null | grep -v ".backup" | grep -v ".lane_backup" | xargs grep -l -i "fast_lane\|deep_lane" 2>/dev/null | wc -l)
echo "   Files with lane references: $SRC_COUNT"

echo ""
echo "4. MCP Config:"
MCP_COUNT=$(grep -i "fast_lane\|deep_lane" {{CATALYST_ROOT}}/global/mcp/profile-configs.json 2>/dev/null | wc -l)
echo "   Lines with lane references: $MCP_COUNT"

echo ""
echo "5. Schemas:"
SCHEMA_COUNT=$(grep -i "lane" {{CATALYST_ROOT}}/global/schemas/run_manifest.json 2>/dev/null | wc -l)
echo "   Lines with lane references: $SCHEMA_COUNT"

echo ""
echo "6. Documentation:"
DOC_COUNT=$(find {{CATALYST_ROOT}}/global/docs -name "*.md" -type f 2>/dev/null | xargs grep -l -i "fast lane\|deep lane" 2>/dev/null | wc -l)
echo "   Files with lane references: $DOC_COUNT"

echo ""
TOTAL=$((AGENT_COUNT + TOOL_COUNT + SRC_COUNT + MCP_COUNT + SCHEMA_COUNT + DOC_COUNT))
if [ $TOTAL -eq 0 ]; then
  echo "✅ SUCCESS: All active operational files are clean!"
else
  echo "⚠️  REMAINING: $TOTAL lane references found in active files"
fi
