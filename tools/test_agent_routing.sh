#!/bin/bash
set -e

# test_agent_routing.sh - Test agent routing by branch/lane/targets
# Validates that the find_prompt function correctly discovers agents

BUILDER_ROOT="${CATALYST_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$BUILDER_ROOT"

# Source the find_prompt function from trigger_planner.sh
source_find_prompt() {
    sed -n '/^find_prompt() {/,/^}/p' tools/trigger_planner.sh > /tmp/find_prompt_func.sh
    source /tmp/find_prompt_func.sh
    rm /tmp/find_prompt_func.sh
}

source_find_prompt

echo "=== Agent Routing Smoke Test ==="
echo

# Test cases: role, branch, lane, expected_agent_pattern
test_cases=(
    # Backend branch
    "backend-architect|backend||backend-architect.md"
    "python-pro|backend||python-pro.md"
    
    # Frontend branch  
    "frontend-specialist|web||frontend-specialist.web.md"
    "javascript-pro|frontend||javascript-pro.md"
    
    # Operations branch
    "devops-troubleshooter|ops||devops-troubleshooter.md"
    "deployment-engineer|ops||deployment-engineer.md"
    
    # Security branch with standard
    "security-auditor|security|standard|security-auditor.md"
    "security-analyst||standard|security-analyst.standard.md"
    
    # Quality branch
    "test-automator|quality||test-automator.md"
    
    # Mobile branch
    "ios-specialist|mobile||ios-specialist.md"
    
    # Desktop branch
    "macos-specialist|desktop||macos-specialist.md"
    
    # Analytics branch
    "data-analyst|analytics||data-analyst.md"
    
    # Automation branch  
    "automation-specialist|automation||automation-specialist.md"
    
    # Web with shopify
    "shopify-specialist|web||shopify-specialist.md"
    
    # Fallback to user-level agents
    "nonexistent-agent|||NOT_FOUND"
)

test_capsule="$BUILDER_ROOT"
pass_count=0
total_count=${#test_cases[@]}

for test_case in "${test_cases[@]}"; do
    IFS='|' read -r role branch lane expected <<< "$test_case"
    
    printf "Testing: %-25s branch=%-10s lane=%-10s " "$role" "$branch" "$lane"
    
    if result=$(find_prompt "$role" "$branch" "$lane" "$test_capsule" 2>/dev/null); then
        found_agent=$(basename "$result")
        if [ "$expected" = "NOT_FOUND" ]; then
            echo "❌ FAIL (expected not found, but got $found_agent)"
        elif [[ "$found_agent" == *"$expected"* ]]; then
            echo "✅ PASS ($found_agent)"
            ((pass_count++))
        else
            echo "❌ FAIL (expected *$expected*, got $found_agent)"
        fi
    else
        if [ "$expected" = "NOT_FOUND" ]; then
            echo "✅ PASS (correctly not found)"
            ((pass_count++))
        else
            echo "❌ FAIL (expected $expected, but not found)"
        fi
    fi
done

echo
echo "=== Branch Routing Results ==="
echo "Passed: $pass_count/$total_count tests"

if [ "$pass_count" -eq "$total_count" ]; then
    echo "🎉 All agent routing tests passed!"
    exit 0
else
    echo "❌ Some routing tests failed"
    exit 1
fi

