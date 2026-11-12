#!/usr/bin/env python3
"""
Test script to validate agent routing based on branch, lane, and file context
"""

import os
import json
import yaml
import pathlib
from collections import defaultdict

BUILDER_ROOT = pathlib.Path.home() / "Documents" / "Builder"
AGENTS_DIR = BUILDER_ROOT / ".claude" / "agents"
RECIPES_DIR = BUILDER_ROOT / "recipes"

def load_agent_metadata():
    """Load all agent frontmatter metadata"""
    agents = {}
    
    if not AGENTS_DIR.exists():
        return agents
        
    for agent_file in AGENTS_DIR.glob("*.md"):
        try:
            with open(agent_file, 'r') as f:
                content = f.read()
                
            # Extract YAML frontmatter
            if content.startswith('---'):
                end = content.find('---', 3)
                if end != -1:
                    frontmatter = content[3:end]
                    metadata = yaml.safe_load(frontmatter)
                    # Use base name for agents like frontend-specialist.web.md
                    base_name = agent_file.stem.split('.')[0]
                    agents[base_name] = metadata
        except Exception as e:
            print(f"Error loading {agent_file}: {e}")
            
    return agents

def test_branch_routing():
    """Test that agents match their declared branches"""
    agents = load_agent_metadata()
    
    print("🔍 Testing Branch Routing...")
    
    # Test cases: branch -> expected agents
    test_cases = {
        'web': ['frontend-specialist', 'shopify-specialist'],
        'backend': ['backend-architect', 'python-pro', 'javascript-pro'],
        'ops': ['devops-troubleshooter', 'deployment-engineer'],
        'automation': ['automation-specialist'],
        'apple': ['ios-specialist', 'macos-specialist'],
        'all': ['code-reviewer']  # code-reviewer should work with any branch
    }
    
    results = {}
    for branch, expected_agents in test_cases.items():
        matching_agents = []
        for agent_name, metadata in agents.items():
            agent_branch = metadata.get('branch', 'default')
            if agent_branch == branch or agent_branch == 'all':
                matching_agents.append(agent_name)
        
        results[branch] = {
            'expected': expected_agents,
            'found': matching_agents,
            'missing': set(expected_agents) - set(matching_agents),
            'extra': set(matching_agents) - set(expected_agents)
        }
    
    # Print results
    all_passed = True
    for branch, result in results.items():
        if result['missing']:
            print(f"  ❌ {branch}: Missing agents {list(result['missing'])}")
            all_passed = False
        else:
            print(f"  ✅ {branch}: All expected agents present ({len(result['found'])} agents)")
    
    return all_passed

def test_lane_routing():
    """Test lane-specific routing"""
    agents = load_agent_metadata()
    
    print("\n🛣️ Testing Lane Routing...")
    
    standard_agents = []
    standard_agents = []
    
    for agent_name, metadata in agents.items():
        if lane == 'standard':
            standard_agents.append(agent_name)
        elif lane == 'standard':
            standard_agents.append(agent_name)
        # 'both' or unspecified means available in both lanes
    
    print(f"  standard Specialists: {standard_agents}")
    print(f"  standard Specialists: {standard_agents}")
    
    # Validate that standard has quality/security focus
    quality_agents = ['code-reviewer', 'security-auditor', 'test-automator']
    standard_quality = [a for a in quality_agents if a in [agent for agent, meta in agents.items() 
    
    if len(standard_quality) >= 2:
        print(f"  ✅ standard has quality agents: {standard_quality}")
        return True
    else:
        print(f"  ❌ standard missing quality agents")
        return False

def test_mcp_mappings():
    """Test that agents have correct MCP tool declarations"""
    agents = load_agent_metadata()
    
    print("\n🔧 Testing MCP Tool Mappings...")
    
    # Check that agents have tools declared
    agents_with_tools = {}
    for agent_name, metadata in agents.items():
        tools = metadata.get('tools', [])
        mcp_tools = [t for t in tools if t.startswith('mcp:')]
        agents_with_tools[agent_name] = {
            'all_tools': tools,
            'mcp_tools': mcp_tools
        }
    
    # Validate key agents have expected MCPs
    expected_mcps = {
        'automation-specialist': ['mcp:n8n', 'mcp:applescript'],
        'frontend-specialist': ['mcp:shadcn-ui'],  # Should be in web variant
        'shopify-specialist': ['mcp:shopify'],
        'ios-specialist': ['mcp:xcodebuild'],
        'backend-architect': ['mcp:git'],
        'devops-troubleshooter': ['mcp:git']
    }
    
    all_passed = True
    for agent_name, expected in expected_mcps.items():
        if agent_name in agents_with_tools:
            agent_mcps = agents_with_tools[agent_name]['mcp_tools']
            missing = [mcp for mcp in expected if mcp not in agent_mcps]
            if missing:
                print(f"  ❌ {agent_name}: Missing MCP tools {missing}")
                all_passed = False
            else:
                print(f"  ✅ {agent_name}: Has expected MCP tools {expected}")
        else:
            print(f"  ⚠️  {agent_name}: Agent not found")
            all_passed = False
    
    return all_passed

def test_recipe_integration():
    """Test that recipes properly integrate with agent system"""
    print("\n📝 Testing Recipe Integration...")
    
    if not RECIPES_DIR.exists():
        print("  ❌ Recipes directory not found")
        return False
    
    # Check that recipes have proper MCP configurations
    recipes_tested = 0
    recipes_passed = 0
    
    for recipe_dir in RECIPES_DIR.rglob("*/"):
        if recipe_dir.name in ['fast', 'deep']:
            continue
            
        mcp_config = recipe_dir / "ops" / "mcp.json"
        if mcp_config.exists():
            try:
                with open(mcp_config) as f:
                    config = json.load(f)
                    
                if 'profile' in config:
                    print(f"  ✅ {recipe_dir.name}: Has MCP profile '{config['profile']}'")
                    recipes_passed += 1
                else:
                    print(f"  ❌ {recipe_dir.name}: Missing MCP profile")
                    
                recipes_tested += 1
            except Exception as e:
                print(f"  ❌ {recipe_dir.name}: Invalid MCP config - {e}")
                recipes_tested += 1
    
    if recipes_tested == 0:
        print("  ⚠️  No recipes found to test")
        return True
    
    success_rate = recipes_passed / recipes_tested
    print(f"  Recipe Integration: {recipes_passed}/{recipes_tested} passed ({success_rate:.0%})")
    return success_rate >= 0.8

def main():
    print("🧪 Builder Agent Routing Validation")
    print("=" * 50)
    
    tests = [
        test_branch_routing,
        test_lane_routing, 
        test_mcp_mappings,
        test_recipe_integration
    ]
    
    passed = 0
    for test_func in tests:
        if test_func():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All agent routing tests passed!")
        return True
    else:
        print("⚠️  Some tests failed - review agent configurations")
        return False

if __name__ == "__main__":
    main()