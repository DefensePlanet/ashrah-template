#!/bin/bash
# Setup Strongbox Master Password in macOS Keychain
# This enables Catalyst account-creator skill to save credentials automatically

KEYCHAIN_SERVICE="Catalyst-Strongbox"
KEYCHAIN_ACCOUNT="master-password"

echo "🔐 Catalyst Strongbox Keychain Setup"
echo "======================================"
echo ""
echo "This will store your Strongbox master password in macOS Keychain."
echo "This enables the account-creator skill to save credentials automatically."
echo ""
echo "Your password will be encrypted and stored in the default keychain."
echo "Only Catalyst tools running as your user account can access it."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled"
    exit 1
fi

# Check if password already exists
if security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" &>/dev/null; then
    echo ""
    echo "⚠️  Strongbox password already exists in Keychain"
    read -p "Update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Delete existing entry
        security delete-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" 2>/dev/null
        echo "✅ Deleted old password"
    else
        echo "❌ Setup cancelled"
        exit 1
    fi
fi

echo ""
echo "Enter your Strongbox master password:"
read -s MASTER_PASSWORD
echo ""

# Validate password by attempting to open database
DB_PATH="{{HOME_DIR}}/Library/Mobile Documents/iCloud~com~strongbox/Documents/Roth Pass.kdbx"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Strongbox database not found at: $DB_PATH"
    exit 1
fi

echo "Validating password..."
echo "$MASTER_PASSWORD" | keepassxc-cli ls "$DB_PATH" &>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Invalid master password. Please try again."
    exit 1
fi

echo "✅ Password validated"

# Store in Keychain
security add-generic-password \
    -s "$KEYCHAIN_SERVICE" \
    -a "$KEYCHAIN_ACCOUNT" \
    -w "$MASTER_PASSWORD" \
    -U 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Strongbox password saved to Keychain"
    echo ""
    echo "📍 Service: $KEYCHAIN_SERVICE"
    echo "📍 Account: $KEYCHAIN_ACCOUNT"
    echo ""
    echo "The account-creator skill can now save credentials automatically!"
    echo ""
    echo "To remove later: security delete-generic-password -s '$KEYCHAIN_SERVICE' -a '$KEYCHAIN_ACCOUNT'"
else
    echo ""
    echo "❌ Failed to save to Keychain"
    exit 1
fi
