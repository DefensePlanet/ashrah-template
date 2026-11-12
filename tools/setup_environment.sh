#!/bin/bash
# Catalyst Environment Setup
# Run this script to set up environment variables for portability

export BUILDER_ROOT="{{CATALYST_ROOT}}"
export BUILDER_RAG_HOST="127.0.0.1"
export BUILDER_RAG_PORT="8000"
export BUILDER_LOG_LEVEL="INFO"
export BUILDER_DEFAULT_LANE="standard"

# Optional: Add to your shell profile
# echo 'export BUILDER_ROOT="{{CATALYST_ROOT}}"' >> ~/.bashrc
# echo 'export BUILDER_ROOT="{{CATALYST_ROOT}}"' >> ~/.zshrc

echo "Catalyst environment configured:"
echo "  BUILDER_ROOT: $BUILDER_ROOT"
echo "  RAG Service: $BUILDER_RAG_HOST:$BUILDER_RAG_PORT"
echo "  Log Level: $BUILDER_LOG_LEVEL"


