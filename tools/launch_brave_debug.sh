#!/bin/bash
# Launch Brave Browser with remote debugging enabled

echo "🚀 Launching Brave with remote debugging..."
echo ""
echo "⚠️  Note: This will close any existing Brave windows first"
echo ""

# Close existing Brave instances
pkill -x "Brave Browser" 2>/dev/null
sleep 2

# Launch Brave with debugging port
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser \
  --remote-debugging-port=9222 \
  --disable-web-security \
  --disable-features=IsolateOrigins,site-per-process \
  > /dev/null 2>&1 &

echo "✅ Brave launched with remote debugging on port 9222"
echo ""
echo "📌 Next steps:"
echo "   1. Navigate to your Supabase project dashboard"
echo "   2. Go to Settings → API"
echo "   3. Run: python3 {{CATALYST_ROOT}}/tools/extract_supabase_credentials.py"
