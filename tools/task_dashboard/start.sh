#!/bin/bash

# Catalyst Task Dashboard Launcher
cd "$(dirname "$0")"

echo "🚀 Starting Catalyst Task Dashboard..."
echo ""
echo "Opening browser: http://localhost:3000"
echo "Press Ctrl+C to stop the server"
echo ""

# Open browser after a delay
(sleep 2 && open http://localhost:3000) &

# Start Next.js dev server
npm run dev
