#!/bin/bash
# Verification script for Mistral optimizations
# Confirms all components are in place and working

set -e

echo "🔍 Mistral Optimization Verification"
echo "====================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0

check() {
    local name=$1
    local command=$2

    echo -n "Checking $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        ((passed++))
        return 0
    else
        echo -e "${RED}❌ FAIL${NC}"
        ((failed++))
        return 1
    fi
}

echo "📦 Files"
echo "--------"
check "Modelfile.mistral-fast exists" "[ -f Modelfile.mistral-fast ]"
check "voice_agent_v2.py exists" "[ -f voice_agent_v2.py ]"
check "preload-mistral.sh exists" "[ -f preload-mistral.sh ]"
check "setup.sh exists" "[ -f setup.sh ]"
check "test-latency.sh exists" "[ -f test-latency.sh ]"
check "README.md exists" "[ -f README.md ]"
check "MISTRAL-OPTIMIZATION.md exists" "[ -f MISTRAL-OPTIMIZATION.md ]"

echo ""
echo "🔧 Models"
echo "---------"
check "ollama command available" "command -v ollama"
check "mistral-fast model exists" "ollama list | grep -q mistral-fast"
check "mistral base model exists" "ollama list | grep -q 'mistral:latest'"

echo ""
echo "💻 Code Integration"
echo "-------------------"
check "voice_agent.py uses mistral-fast" "grep -q 'mistral-fast' voice_agent.py"
check "pipecat_gateway.py uses mistral-fast" "grep -q 'mistral-fast' pipecat_gateway.py"
check "voice_agent.py has streaming" "grep -q 'stream.*True' voice_agent.py"

echo ""
echo "🧪 Functionality"
echo "----------------"
if check "mistral-fast responds to queries" "timeout 15 ollama run mistral-fast 'hi' --verbose 2>&1 | grep -q 'total duration'"; then
    # Get performance metrics
    metrics=$(timeout 15 ollama run mistral-fast "What time is it?" --verbose 2>&1)
    total=$(echo "$metrics" | grep "total duration" | awk '{print $3}')
    load=$(echo "$metrics" | grep "load duration" | awk '{print $3}')
    rate=$(echo "$metrics" | grep "^eval rate" | awk '{print $3}')

    echo ""
    echo "  Performance:"
    echo "    Total: $total"
    echo "    Load:  $load"
    echo "    Rate:  $rate tokens/s"
fi

echo ""
echo "📊 Summary"
echo "----------"
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"

if [ $failed -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "Mistral optimization is ready for production."
    echo ""
    echo "Next steps:"
    echo "  • Run: ./preload-mistral.sh (keeps model in memory)"
    echo "  • Start: python3 pipecat_gateway.py"
    echo "  • Test: ./test-latency.sh"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Some checks failed${NC}"
    echo ""
    echo "Run ./setup.sh to fix missing components"
    exit 1
fi
