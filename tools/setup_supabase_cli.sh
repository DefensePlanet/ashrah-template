#!/bin/bash
# Setup Supabase CLI for Catalyst
# Authenticates CLI using credentials from Strongbox

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDER_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up Supabase CLI for Catalyst..."

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo "❌ Supabase CLI not found"
    echo "Install with: brew install supabase/tap/supabase"
    exit 1
fi

echo "✅ Supabase CLI found: $(supabase --version | head -1)"

# Get access token from Strongbox
echo "🔑 Retrieving access token from Strongbox..."
ACCESS_TOKEN=$(python3 "$SCRIPT_DIR/strongbox_cli.py" get-api-key --service supabase --purpose "access-token" 2>&1)

if [[ $ACCESS_TOKEN == *"Error"* ]] || [[ -z "$ACCESS_TOKEN" ]]; then
    echo "❌ Access token not found in Strongbox"
    echo ""
    echo "Store your Supabase access token:"
    echo "  tools/strongbox_cli.py set-api-key \\"
    echo "    --service supabase \\"
    echo "    --purpose 'access-token' \\"
    echo "    --api-key 'your-token-here'"
    exit 1
fi

echo "✅ Access token retrieved from Strongbox"

# Authenticate CLI using environment variable method
# This is more secure than storing in ~/.supabase
export SUPABASE_ACCESS_TOKEN="$ACCESS_TOKEN"

# Test authentication
echo "🔍 Testing CLI authentication..."
if supabase projects list --output json > /dev/null 2>&1; then
    echo "✅ CLI authentication successful"
    echo ""
    echo "Available projects:"
    supabase projects list
else
    echo "❌ CLI authentication failed"
    echo "Verify your access token has correct permissions"
    exit 1
fi

echo ""
echo "✅ Supabase CLI setup complete!"
echo ""
echo "💡 Usage Notes:"
echo "  - CLI commands work with SUPABASE_ACCESS_TOKEN env var"
echo "  - Capsules should set this in their .env file"
echo "  - Use 'supabase link' in capsules to connect to projects"
echo "  - Backend Dev agent now uses CLI as primary method"
echo ""
echo "📚 Next steps:"
echo "  1. cd capsules/your-project"
echo "  2. supabase init"
echo "  3. supabase link --project-ref your-project-ref"
echo "  4. supabase db pull  # Pull remote schema"
echo "  5. supabase gen types typescript --local > types/database.ts"
