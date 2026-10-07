#!/bin/bash
# Test GitHub signup with the fixed registration automation script

set -e

echo "🧪 Testing GitHub signup automation with anti-detection fixes"
echo "============================================================"
echo ""

# Generate test credentials
TEST_EMAIL="test.builder.$(date +%s)@example.com"
TEST_USERNAME="testuser$(date +%s)"
TEST_PASSWORD="TestPass123!Secure"

echo "Test credentials:"
echo "  Email: $TEST_EMAIL"
echo "  Username: $TEST_USERNAME"
echo "  Password: [REDACTED]"
echo ""

echo "Starting GitHub signup test..."
echo "This will open a browser window - watch for:"
echo "  ✅ Email field filled character-by-character (80-250ms delays)"
echo "  ✅ Username field filled with delays"
echo "  ✅ Password field filled with delays"
echo "  ✅ Clicks 'Continue' button (NOT OAuth buttons)"
echo "  ✅ No redirect to Google/GitHub OAuth"
echo ""

# Run the registration automation
python3 {{CATALYST_ROOT}}/tools/registration_automation.py \
  https://github.com/signup \
  --email "$TEST_EMAIL" \
  --username "$TEST_USERNAME" \
  --password "$TEST_PASSWORD"

EXIT_CODE=$?

echo ""
echo "============================================================"
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Test completed successfully"
  echo ""
  echo "Manual verification checklist:"
  echo "  [ ] Form fields were filled slowly (human-like)"
  echo "  [ ] No OAuth redirect occurred"
  echo "  [ ] Landed on GitHub verification page"
else
  echo "❌ Test failed with exit code: $EXIT_CODE"
  echo ""
  echo "Check screenshots in /tmp/registration_*.png"
fi

exit $EXIT_CODE
