#!/bin/bash
# Switch Catalyst to Subscription Mode (Anthropic credits)
# Controlled by {{ORCHESTRATOR_NAME}} via natural language or /use-subscription command

set -e

GATEWAY_STATE_FILE="$HOME/.claude/gateway-mode"

echo "🔄 Switching to Subscription Mode..."
echo

# Write state file
echo "subscription" > "$GATEWAY_STATE_FILE"
echo "✅ Subscription mode state saved to $GATEWAY_STATE_FILE"

echo
echo "🎯 Subscription Mode Configuration Complete"
echo
echo "   Current session: No change (restart required)"
echo "   Next session: Anthropic Subscription Credits"
echo
echo "📊 Billing info:"
echo "   • ~3 weeks remaining in current cycle"
echo "   • Prepaid credits will be used"
echo "   • No additional API charges"
echo
echo "🔄 To activate: Start new terminal → run 'claude' command"
echo "💡 To switch back: Tell {{ORCHESTRATOR_NAME}} 'use gateway' or run /use-gateway"
echo
