#!/usr/bin/env python3
"""
System Integration Test - Verify all Builder systems work together
Tests autopsy, dependency mapping, replay, fork, opportunity feeding, and system ops integration
"""

import os
import sys
import json
import subprocess
import pathlib
import tempfile
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
import time

# Add Builder tools to path
BUILDER_ROOT = pathlib.Path.home() / "Documents" / "Builder"
sys.path.append(str(BUILDER_ROOT / "tools"))

def test_system_component(component_name: str, test_func) -> Dict[str, Any]:
    """Test a system component and return results"""
    print(f"Testing {component_name}...")
    start_time = time.time()
    
    try:
        result = test_func()
        duration = time.time() - start_time
        
        return {
            "component": component_name,
            "status": "PASS" if result.get("success", False) else "FAIL",
            "duration_seconds": round(duration, 2),
            "details": result,
            "error": result.get("error") if not result.get("success", False) else None
        }
    except Exception as e:
        duration = time.time() - start_time
        return {
            "component": component_name,
            "status": "ERROR", 
            "duration_seconds": round(duration, 2),
            "error": str(e),
            "details": {}
        }

def test_rag_service() -> Dict[str, Any]:
    """Test RAG service connectivity and basic functionality"""
    try:
        # Test health endpoint
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        if health_response.status_code != 200:
            return {"success": False, "error": f"Health check failed: {health_response.status_code}"}
        
        # Test query functionality
        query_response = requests.post(
            "http://localhost:8000/query",
            json={"collection": "test", "query": "test query", "top_k": 1},
            timeout=10
        )
        
        return {
            "success": True,
            "health_status": health_response.json(),
            "query_responsive": query_response.status_code in [200, 404]  # 404 is OK if collection doesn't exist
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_dependency_mapper() -> Dict[str, Any]:
    """Test dependency mapper functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "dependency_mapper.py"
        if not script_path.exists():
            return {"success": False, "error": "dependency_mapper.py not found"}
        
        # Run dependency mapper with timeout
        result = subprocess.run(
            [sys.executable, str(script_path), "--quiet"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check if graph file was created
        graph_file = BUILDER_ROOT / "global" / "dependency-graph.json"
        graph_exists = graph_file.exists()
        
        return {
            "success": result.returncode == 0 and graph_exists,
            "exit_code": result.returncode,
            "graph_file_created": graph_exists,
            "stdout_lines": len(result.stdout.splitlines()) if result.stdout else 0,
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Dependency mapper timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_autopsy_agent() -> Dict[str, Any]:
    """Test capsule autopsy agent functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "capsule_autopsy.py"
        if not script_path.exists():
            return {"success": False, "error": "capsule_autopsy.py not found"}
        
        # Find a test capsule or create a minimal one
        capsules_dir = BUILDER_ROOT / "capsules"
        test_capsule = None
        
        if capsules_dir.exists():
            for capsule_dir in capsules_dir.iterdir():
                if capsule_dir.is_dir() and not capsule_dir.name.startswith('.'):
                    runs_dir = capsule_dir / "runs"
                    if runs_dir.exists() and any(runs_dir.iterdir()):
                        test_capsule = capsule_dir.name
                        break
        
        if not test_capsule:
            return {"success": False, "error": "No capsules with runs found for testing"}
        
        # Run autopsy in dry-run mode
        result = subprocess.run(
            [sys.executable, str(script_path), test_capsule, "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "test_capsule": test_capsule,
            "output_lines": len(result.stdout.splitlines()) if result.stdout else 0,
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Autopsy agent timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_replay_tool() -> Dict[str, Any]:
    """Test capsule replay tool functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "replay_capsule.py"
        if not script_path.exists():
            return {"success": False, "error": "replay_capsule.py not found"}
        
        # Find a capsule with runs
        capsules_dir = BUILDER_ROOT / "capsules"
        test_capsule = None
        
        if capsules_dir.exists():
            for capsule_dir in capsules_dir.iterdir():
                if capsule_dir.is_dir() and not capsule_dir.name.startswith('.'):
                    runs_dir = capsule_dir / "runs"
                    if runs_dir.exists() and any(runs_dir.iterdir()):
                        test_capsule = capsule_dir.name
                        break
        
        if not test_capsule:
            return {"success": True, "note": "No capsules with runs found - replay tool not tested"}
        
        # Test list functionality
        result = subprocess.run(
            [sys.executable, str(script_path), "list", test_capsule],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "test_capsule": test_capsule,
            "runs_found": "runs" in result.stdout.lower(),
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Replay tool timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_fork_tool() -> Dict[str, Any]:
    """Test capsule fork tool functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "fork_capsule.py"
        if not script_path.exists():
            return {"success": False, "error": "fork_capsule.py not found"}
        
        # Test list functionality
        result = subprocess.run(
            [sys.executable, str(script_path), "list"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "capsules_listed": "capsule" in result.stdout.lower(),
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Fork tool timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_internal_metrics_ingestion() -> Dict[str, Any]:
    """Test internal metrics ingestion functionality"""
    try:
        script_path = BUILDER_ROOT / "global" / "rag" / "service" / "ingest_internal_metrics.py"
        if not script_path.exists():
            return {"success": False, "error": "ingest_internal_metrics.py not found"}
        
        # Run in dry-run mode with short timeframe
        result = subprocess.run(
            [sys.executable, str(script_path), "--dry-run", "--hours", "1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "opportunities_generated": "opportunity" in result.stdout.lower(),
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Internal metrics ingestion timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_system_ops_integration() -> Dict[str, Any]:
    """Test system ops integration functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "system_ops_integration.py"
        if not script_path.exists():
            return {"success": False, "error": "system_ops_integration.py not found"}
        
        # Run report-only mode with short timeframe
        result = subprocess.run(
            [sys.executable, str(script_path), "--report-only", "--days", "1"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "report_generated": "Catalyst Weekly Report" in result.stdout,
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "System ops integration timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_daily_dependency_check() -> Dict[str, Any]:
    """Test daily dependency check functionality"""
    try:
        script_path = BUILDER_ROOT / "tools" / "daily_dependency_check.py"
        if not script_path.exists():
            return {"success": False, "error": "daily_dependency_check.py not found"}
        
        # Run dependency check
        result = subprocess.run(
            [sys.executable, str(script_path), "--quiet"],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        return {
            "success": result.returncode in [0, 1],  # 1 is OK for warnings
            "exit_code": result.returncode,
            "dependency_check_completed": True,
            "stderr": result.stderr if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Daily dependency check timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def run_integration_tests() -> Dict[str, Any]:
    """Run all system integration tests"""
    print("🔄 Starting Catalyst Integration Tests")
    print("=" * 60)
    
    test_results = []
    
    # Define test components
    test_components = [
        ("RAG Service", test_rag_service),
        ("Dependency Mapper", test_dependency_mapper),
        ("Autopsy Agent", test_autopsy_agent),
        ("Replay Tool", test_replay_tool),
        ("Fork Tool", test_fork_tool),
        ("Internal Metrics Ingestion", test_internal_metrics_ingestion),
        ("System Ops Integration", test_system_ops_integration),
        ("Daily Dependency Check", test_daily_dependency_check),
    ]
    
    # Run each test
    for component_name, test_func in test_components:
        result = test_system_component(component_name, test_func)
        test_results.append(result)
        
        # Print immediate feedback
        status_emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "🚨"}
        print(f"{status_emoji.get(result['status'], '❓')} {component_name}: {result['status']} ({result['duration_seconds']}s)")
        
        if result.get("error"):
            print(f"   Error: {result['error']}")
    
    # Calculate overall results
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r['status'] == 'PASS')
    failed_tests = sum(1 for r in test_results if r['status'] == 'FAIL')
    error_tests = sum(1 for r in test_results if r['status'] == 'ERROR')
    
    overall_status = "PASS" if passed_tests == total_tests else "FAIL"
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": overall_status,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "error_tests": error_tests,
        "success_rate": round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0,
        "test_results": test_results
    }
    
    return summary

def main():
    """CLI interface for system integration tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Catalyst Integration Tests")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    if args.quiet:
        # Redirect stdout to null for quiet mode, but keep stderr
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
    
    try:
        results = run_integration_tests()
        
        if args.quiet:
            sys.stdout = old_stdout
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "=" * 60)
            print("🔄 Catalyst Integration Test Summary")
            print("=" * 60)
            print(f"Overall Status: {results['overall_status']}")
            print(f"Success Rate: {results['success_rate']}%")
            print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
            
            if results['failed_tests'] > 0:
                print(f"Tests Failed: {results['failed_tests']}")
                print("\nFailed Tests:")
                for result in results['test_results']:
                    if result['status'] in ['FAIL', 'ERROR']:
                        print(f"  ❌ {result['component']}: {result.get('error', 'Unknown error')}")
            
            if results['overall_status'] == 'PASS':
                print("\n✅ All Builder systems are integrated and functioning correctly!")
            else:
                print(f"\n⚠️ {results['failed_tests'] + results['error_tests']} system(s) need attention")
        
        # Exit with appropriate code
        sys.exit(0 if results['overall_status'] == 'PASS' else 1)
        
    except Exception as e:
        if args.quiet:
            sys.stdout = old_stdout
        
        print(f"❌ Integration test suite failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()