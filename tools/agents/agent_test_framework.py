#!/usr/bin/env python3
"""
Agent Testing Framework
Comprehensive testing system for Claude Code agents in Builder system
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import yaml
import tempfile
import shutil

# Import Builder modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("paths_config", parent_dir / "global" / "config" / "paths.py")
    paths_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paths_module)
    paths = paths_module.paths
    
    # Import other modules
    spec = importlib.util.spec_from_file_location("agent_registry", parent_dir / "tools" / "agent_registry.py")
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    AgentRegistry = registry_module.AgentRegistry
    
    spec = importlib.util.spec_from_file_location("agent_usage_tracker", parent_dir / "tools" / "agent_usage_tracker.py")
    tracker_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracker_module)
    AgentUsageTracker = tracker_module.AgentUsageTracker
    
except Exception as e:
    print(f"Error importing Builder modules: {e}")
    sys.exit(1)


class AgentTestFramework:
    """Comprehensive testing framework for Claude Code agents"""
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.usage_tracker = AgentUsageTracker()
        self.test_results_dir = paths.registry / "agent_test_results"
        self.test_scenarios_dir = paths.base / "testing" / "agent_scenarios"
        self.test_results_dir.mkdir(parents=True, exist_ok=True)
        
        # Standard test scenarios
        self.test_scenarios = {
            "basic_functionality": {
                "description": "Test basic agent functionality and response",
                "test_prompt": "Please analyze this simple task and provide a response.",
                "expected_elements": ["analysis", "response", "reasoning"],
                "timeout": 30
            },
            "tool_usage": {
                "description": "Test agent's ability to use specified tools",
                "test_prompt": "Please demonstrate the use of your available tools.",
                "expected_elements": ["tool_usage", "practical_application"],
                "timeout": 60
            },
            "error_handling": {
                "description": "Test agent's error handling capabilities",
                "test_prompt": "Handle this intentionally problematic scenario: [INVALID_INPUT]",
                "expected_elements": ["error_recognition", "graceful_handling"],
                "timeout": 30
            },
            "context_awareness": {
                "description": "Test agent's understanding of Builder context",
                "test_prompt": "Explain how you would approach this task within the Builder system.",
                "expected_elements": ["builder_awareness", "capsule_understanding"],
                "timeout": 45
            },
            "dod_integration": {
                "description": "Test agent's DoD contribution capabilities",
                "test_prompt": "What would you contribute to the Definition of Done for this task?",
                "expected_elements": ["dod_items", "quality_checks"],
                "timeout": 30
            }
        }
    
    def run_agent_test_suite(self, agent_id: str, test_scenarios: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive test suite for an agent"""
        agent_info = self.registry.agents.get(agent_id)
        if not agent_info:
            return {"error": f"Agent {agent_id} not found in registry"}
        
        test_scenarios = test_scenarios or list(self.test_scenarios.keys())
        
        test_session = {
            "agent_id": agent_id,
            "agent_name": agent_info["name"],
            "test_timestamp": datetime.now().isoformat(),
            "test_scenarios": test_scenarios,
            "results": {},
            "summary": {
                "total_tests": len(test_scenarios),
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "overall_score": 0
            }
        }
        
        print(f"🧪 Testing agent: {agent_info['display_name']}")
        
        for scenario_name in test_scenarios:
            if scenario_name not in self.test_scenarios:
                print(f"   ⚠️  Unknown scenario: {scenario_name}")
                continue
                
            print(f"   Running {scenario_name}...")
            result = self._run_single_test(agent_info, scenario_name)
            test_session["results"][scenario_name] = result
            
            if result["passed"]:
                test_session["summary"]["passed"] += 1
                print(f"     ✅ Passed")
            elif result.get("error"):
                test_session["summary"]["errors"] += 1
                print(f"     💥 Error: {result['error']}")
            else:
                test_session["summary"]["failed"] += 1
                print(f"     ❌ Failed")
        
        # Calculate overall score
        if test_session["summary"]["total_tests"] > 0:
            score = (test_session["summary"]["passed"] / test_session["summary"]["total_tests"]) * 100
            test_session["summary"]["overall_score"] = score
        
        # Save results
        results_file = self.test_results_dir / f"{agent_info['name']}_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(test_session, f, indent=2, default=str)
        
        return test_session
    
    def _run_single_test(self, agent_info: Dict[str, Any], scenario_name: str) -> Dict[str, Any]:
        """Run a single test scenario"""
        scenario = self.test_scenarios[scenario_name]
        test_result = {
            "scenario": scenario_name,
            "description": scenario["description"],
            "start_time": datetime.now().isoformat(),
            "passed": False,
            "score": 0,
            "details": {},
            "metrics": {}
        }
        
        start_time = time.time()
        
        try:
            # Simulate agent test (in real implementation, this would invoke Claude Code)
            test_result["details"] = self._simulate_agent_interaction(agent_info, scenario)
            
            # Evaluate results
            evaluation = self._evaluate_test_results(test_result["details"], scenario)
            test_result.update(evaluation)
            
            # Track usage
            self.usage_tracker.log_agent_usage(
                agent_name=agent_info["name"],
                task_type=f"test_{scenario_name}",
                success=test_result["passed"],
                duration_seconds=time.time() - start_time,
                context={"test_framework": True, "scenario": scenario_name}
            )
            
        except Exception as e:
            test_result["error"] = str(e)
            test_result["passed"] = False
        
        test_result["duration"] = time.time() - start_time
        test_result["end_time"] = datetime.now().isoformat()
        
        return test_result
    
    def _simulate_agent_interaction(self, agent_info: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate agent interaction (placeholder for actual Claude Code integration)"""
        # In a real implementation, this would:
        # 1. Create a test environment
        # 2. Invoke Claude Code with the agent
        # 3. Capture the response and tool usage
        # 4. Return detailed interaction data
        
        # For now, simulate based on agent configuration
        agent_spec = self._load_agent_specification(agent_info)
        
        simulation_result = {
            "agent_spec_loaded": bool(agent_spec),
            "tools_available": agent_info.get("metadata", {}).get("tools", []),
            "response_generated": True,
            "tool_usage_attempted": len(agent_info.get("metadata", {}).get("tools", [])) > 0,
            "error_handling_present": "error" in str(agent_spec).lower() if agent_spec else False,
            "builder_context_aware": any(term in str(agent_spec).lower() for term in ["builder", "capsule", "dod"]) if agent_spec else False,
            "dod_contributions_defined": "definition of done" in str(agent_spec).lower() if agent_spec else False
        }
        
        return simulation_result
    
    def _load_agent_specification(self, agent_info: Dict[str, Any]) -> Optional[str]:
        """Load agent specification content"""
        try:
            agent_path = Path(agent_info["path"])
            if agent_path.is_file():
                with open(agent_path, 'r', encoding='utf-8') as f:
                    return f.read()
            elif agent_path.is_dir():
                prompt_file = agent_path / "prompt.md"
                if prompt_file.exists():
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        return f.read()
        except:
            pass
        return None
    
    def _evaluate_test_results(self, details: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test results against expected criteria"""
        evaluation = {
            "passed": False,
            "score": 0,
            "checks": {}
        }
        
        scenario_name = None
        for name, config in self.test_scenarios.items():
            if config == scenario:
                scenario_name = name
                break
        
        if scenario_name == "basic_functionality":
            checks = {
                "spec_loaded": details.get("agent_spec_loaded", False),
                "response_generated": details.get("response_generated", False)
            }
            
        elif scenario_name == "tool_usage":
            checks = {
                "tools_available": len(details.get("tools_available", [])) > 0,
                "tool_usage_attempted": details.get("tool_usage_attempted", False)
            }
            
        elif scenario_name == "error_handling":
            checks = {
                "error_handling_present": details.get("error_handling_present", False)
            }
            
        elif scenario_name == "context_awareness":
            checks = {
                "builder_context_aware": details.get("builder_context_aware", False)
            }
            
        elif scenario_name == "dod_integration":
            checks = {
                "dod_contributions_defined": details.get("dod_contributions_defined", False)
            }
        else:
            checks = {}
        
        evaluation["checks"] = checks
        
        # Calculate score
        if checks:
            passed_checks = sum(1 for check in checks.values() if check)
            evaluation["score"] = (passed_checks / len(checks)) * 100
            evaluation["passed"] = evaluation["score"] >= 70  # 70% threshold
        
        return evaluation
    
    def run_batch_tests(self, agent_filter: Dict[str, Any] = None, 
                       test_scenarios: List[str] = None) -> Dict[str, Any]:
        """Run tests on multiple agents"""
        # Get agents to test
        if agent_filter:
            agents_to_test = self.registry.get_agents_by_criteria(**agent_filter)
        else:
            agents_to_test = list(self.registry.agents.values())
        
        batch_results = {
            "batch_timestamp": datetime.now().isoformat(),
            "total_agents": len(agents_to_test),
            "agent_results": {},
            "summary": {
                "agents_passed": 0,
                "agents_failed": 0,
                "average_score": 0,
                "test_scenarios": test_scenarios or list(self.test_scenarios.keys())
            }
        }
        
        print(f"🧪 Running batch tests on {len(agents_to_test)} agents")
        
        scores = []
        for agent in agents_to_test:
            agent_id = agent["id"]
            print(f"\n Testing {agent['display_name']}...")
            
            result = self.run_agent_test_suite(agent_id, test_scenarios)
            batch_results["agent_results"][agent_id] = result
            
            if "error" not in result:
                score = result["summary"]["overall_score"]
                scores.append(score)
                
                if score >= 70:
                    batch_results["summary"]["agents_passed"] += 1
                else:
                    batch_results["summary"]["agents_failed"] += 1
                    
                print(f"   Score: {score:.1f}/100")
        
        if scores:
            batch_results["summary"]["average_score"] = sum(scores) / len(scores)
        
        # Save batch results
        batch_file = self.test_results_dir / f"batch_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(batch_file, 'w') as f:
            json.dump(batch_results, f, indent=2, default=str)
        
        return batch_results
    
    def generate_test_report(self, results_file: Path = None) -> str:
        """Generate human-readable test report"""
        if results_file:
            with open(results_file) as f:
                results = json.load(f)
        else:
            # Get latest batch results
            batch_files = list(self.test_results_dir.glob("batch_test_results_*.json"))
            if not batch_files:
                return "❌ No test results available"
            
            latest_file = max(batch_files, key=lambda x: x.stat().st_mtime)
            with open(latest_file) as f:
                results = json.load(f)
        
        if "agent_results" in results:
            # Batch results
            report = self._generate_batch_report(results)
        else:
            # Single agent results
            report = self._generate_single_agent_report(results)
        
        return report
    
    def _generate_batch_report(self, results: Dict[str, Any]) -> str:
        """Generate batch test report"""
        report = f"""
🧪 Agent Test Report - Batch Results

## Summary
- **Total Agents Tested**: {results['total_agents']}
- **Agents Passed**: {results['summary']['agents_passed']}
- **Agents Failed**: {results['summary']['agents_failed']}
- **Average Score**: {results['summary']['average_score']:.1f}/100
- **Test Date**: {results['batch_timestamp'][:10]}

## Test Scenarios
{', '.join(results['summary']['test_scenarios'])}

## Agent Performance
"""
        
        # Sort agents by score
        agent_scores = []
        for agent_id, agent_result in results["agent_results"].items():
            if "error" not in agent_result:
                agent_scores.append((
                    agent_result["agent_name"],
                    agent_result["summary"]["overall_score"],
                    agent_result["summary"]["passed"],
                    agent_result["summary"]["failed"]
                ))
        
        agent_scores.sort(key=lambda x: x[1], reverse=True)
        
        for name, score, passed, failed in agent_scores:
            status = "✅" if score >= 70 else "❌"
            report += f"- {status} **{name}**: {score:.1f}/100 ({passed}P/{failed}F)\n"
        
        # Add recommendations
        if results['summary']['average_score'] < 70:
            report += "\n## Recommendations\n"
            report += "- 🔧 Review failed agents and improve specifications\n"
            report += "- 📚 Update agent documentation to meet standards\n"
            report += "- 🧪 Run individual tests for detailed diagnostics\n"
        
        return report
    
    def _generate_single_agent_report(self, results: Dict[str, Any]) -> str:
        """Generate single agent test report"""
        report = f"""
🧪 Agent Test Report - {results['agent_name']}

## Summary
- **Overall Score**: {results['summary']['overall_score']:.1f}/100
- **Tests Passed**: {results['summary']['passed']}/{results['summary']['total_tests']}
- **Test Date**: {results['test_timestamp'][:10]}

## Test Results
"""
        
        for scenario, result in results["results"].items():
            status = "✅" if result["passed"] else "❌"
            score = result.get("score", 0)
            report += f"- {status} **{scenario}**: {score:.1f}/100\n"
            
            if result.get("checks"):
                for check, passed in result["checks"].items():
                    check_status = "✅" if passed else "❌"
                    report += f"  - {check_status} {check.replace('_', ' ').title()}\n"
        
        return report
    
    def create_test_scenario(self, name: str, description: str, test_prompt: str,
                           expected_elements: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Create custom test scenario"""
        scenario = {
            "description": description,
            "test_prompt": test_prompt,
            "expected_elements": expected_elements,
            "timeout": timeout
        }
        
        # Save scenario
        scenario_file = self.test_scenarios_dir / f"{name}.json"
        scenario_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(scenario_file, 'w') as f:
            json.dump(scenario, f, indent=2)
        
        return scenario


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Testing Framework")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Test single agent
    test_parser = subparsers.add_parser("test", help="Test single agent")
    test_parser.add_argument("agent", help="Agent name or ID")
    test_parser.add_argument("--scenarios", nargs="+", help="Test scenarios to run")
    
    # Batch test
    batch_parser = subparsers.add_parser("batch", help="Run batch tests")
    batch_parser.add_argument("--scope", help="Filter by scope")
    batch_parser.add_argument("--lane", help="Filter by lane")
    batch_parser.add_argument("--scenarios", nargs="+", help="Test scenarios to run")
    
    # Report
    report_parser = subparsers.add_parser("report", help="Generate test report")
    report_parser.add_argument("--file", help="Specific results file")
    
    # List scenarios
    subparsers.add_parser("scenarios", help="List available test scenarios")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    framework = AgentTestFramework()
    
    if args.command == "test":
        # Find agent
        agent_id = None
        for aid, agent in framework.registry.agents.items():
            if args.agent in agent["name"] or args.agent == aid:
                agent_id = aid
                break
        
        if not agent_id:
            print(f"❌ Agent '{args.agent}' not found")
            return
        
        results = framework.run_agent_test_suite(agent_id, args.scenarios)
        
        if "error" in results:
            print(f"❌ Error: {results['error']}")
        else:
            print(f"\n📊 Test Results:")
            print(f"   Overall Score: {results['summary']['overall_score']:.1f}/100")
            print(f"   Passed: {results['summary']['passed']}/{results['summary']['total_tests']}")
    
    elif args.command == "batch":
        filters = {}
        if args.scope:
            filters["scope"] = args.scope
        if args.lane:
        
        results = framework.run_batch_tests(filters, args.scenarios)
        
        print(f"\n📊 Batch Test Results:")
        print(f"   Average Score: {results['summary']['average_score']:.1f}/100")
        print(f"   Agents Passed: {results['summary']['agents_passed']}")
        print(f"   Agents Failed: {results['summary']['agents_failed']}")
    
    elif args.command == "report":
        report_file = Path(args.file) if args.file else None
        report = framework.generate_test_report(report_file)
        print(report)
    
    elif args.command == "scenarios":
        print("📋 Available Test Scenarios:")
        for name, scenario in framework.test_scenarios.items():
            print(f"   • **{name}**: {scenario['description']}")


if __name__ == "__main__":
    main()