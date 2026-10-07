#!/usr/bin/env node

const fs = require('fs');
const jwt = require('jsonwebtoken');

// Get environment variables
const teamId = process.env.APPLE_TEAM_ID;
const keyId = process.env.APPLE_KEY_ID;
const keyPath = process.env.APPLE_PRIVATE_KEY_PATH;

if (!teamId || !keyId || !keyPath) {
  console.error("Missing APPLE_TEAM_ID/APPLE_KEY_ID/APPLE_PRIVATE_KEY_PATH");
  process.exit(1);
}

// Read private key
let privateKey;
try {
  privateKey = fs.readFileSync(keyPath, 'utf8');
} catch (err) {
  console.error(`Failed to read private key from ${keyPath}: ${err.message}`);
  process.exit(1);
}

// Generate token
const now = Math.floor(Date.now() / 1000);
const token = jwt.sign(
  {
    iss: teamId,
    iat: now,
    exp: now + (20 * 60), // 20 minutes
  },
  privateKey,
  {
    algorithm: 'ES256',
    header: {
      alg: 'ES256',
      kid: keyId,
      typ: 'JWT'
    }
  }
);

// Output token
process.stdout.write(token);