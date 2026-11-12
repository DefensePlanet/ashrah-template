#!/bin/bash
# RAG Service Security Environment Setup

# Authentication token (keep this secret!)
export BUILDER_RAG_AUTH_TOKEN="${BUILDER_RAG_AUTH_TOKEN:-$(openssl rand -base64 32)}"

# CORS origins (adjust as needed)
export BUILDER_RAG_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

# Service configuration
export BUILDER_RAG_HOST="127.0.0.1"
export BUILDER_RAG_PORT="8000"

echo "RAG Service security environment configured"
echo "Token: 3FlNN7RO..."
echo "CORS origins: $BUILDER_RAG_ALLOWED_ORIGINS"
echo ""
echo "To start secure RAG service:"
echo "  cd {{CATALYST_ROOT}}/global/rag/service"
echo "  python3 rag_service.py"
echo ""
echo "WARNING: Keep the auth token secure and do not commit it to git!"


