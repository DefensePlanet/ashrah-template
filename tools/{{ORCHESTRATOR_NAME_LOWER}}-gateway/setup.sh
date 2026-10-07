#!/bin/bash
# {{ORCHESTRATOR_NAME}} Gateway Setup Script
# Creates optimized Mistral model and verifies dependencies

set -e

echo "🏗️  {{ORCHESTRATOR_NAME}} Gateway Setup"
echo "======================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Ollama
echo "Checking Ollama..."
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama not found${NC}"
    echo "Install with: brew install ollama"
    exit 1
fi
echo -e "${GREEN}✅ Ollama installed${NC}"

# Check if Ollama is running
if ! ollama list &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama service not running${NC}"
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Check for base Mistral model
echo ""
echo "Checking Mistral model..."
if ! ollama list | grep -q "mistral:latest"; then
    echo -e "${YELLOW}⚠️  Mistral not found. Downloading...${NC}"
    ollama pull mistral
    echo -e "${GREEN}✅ Mistral downloaded${NC}"
else
    echo -e "${GREEN}✅ Mistral available${NC}"
fi

# Create optimized model
echo ""
echo "Creating mistral-fast (optimized model)..."
if ollama list | grep -q "mistral-fast"; then
    echo -e "${YELLOW}⚠️  mistral-fast already exists${NC}"
    read -p "Recreate? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping model creation"
    else
        ollama rm mistral-fast
        ollama create mistral-fast -f Modelfile.mistral-fast
        echo -e "${GREEN}✅ mistral-fast recreated${NC}"
    fi
else
    ollama create mistral-fast -f Modelfile.mistral-fast
    echo -e "${GREEN}✅ mistral-fast created${NC}"
fi

# Check Kokoro TTS
echo ""
echo "Checking Kokoro TTS..."
kokoro_url=${KOKORO_URL:-"http://localhost:8880"}
kokoro_health="${kokoro_url%/v1*}/health"

if curl -s "$kokoro_health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kokoro TTS running${NC}"
else
    echo -e "${YELLOW}⚠️  Kokoro TTS not running at $kokoro_url${NC}"
    echo "Please start Kokoro TTS server"
fi

# Check Python dependencies
echo ""
echo "Checking Python dependencies..."
if [ -f requirements.txt ]; then
    if pip3 list | grep -q "pipecat"; then
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  Installing Python dependencies...${NC}"
        pip3 install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found${NC}"
fi

# Preload model
echo ""
echo "Preloading mistral-fast..."
if ./preload-mistral.sh; then
    echo -e "${GREEN}✅ Model preloaded${NC}"
else
    echo -e "${YELLOW}⚠️  Preload failed (non-critical)${NC}"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Available models:"
ollama list | grep -E "NAME|mistral"
echo ""
echo "Next steps:"
echo "  1. Start gateway: python3 pipecat_gateway.py"
echo "  2. Or use run script: ./run.sh"
echo "  3. Test performance: ./test-latency.sh"
echo ""
echo "Environment variables (optional):"
echo "  export OLLAMA_MODEL=mistral-fast  # Use optimized (default)"
echo "  export OLLAMA_MODEL=mistral       # Use standard"
echo ""
