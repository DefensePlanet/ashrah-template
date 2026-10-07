#!/usr/bin/env python3
"""
Catalyst Health Monitor
Real-time status dashboard
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

def check_system_health():
    """Run all health checks and aggregate status"""
    checks = {
        'daily_audit': run_audit_check(),
        'test_suite': run_test_check(),
        'dependencies': run_dependency_check(),
        'memory': run_memory_check()
    }
    
    overall_status = 'healthy'
    for check, status in checks.items():
        if status['status'] == 'failed':
            overall_status = 'degraded'
        elif status['status'] == 'warning' and overall_status == 'healthy':
            overall_status = 'warning'
    
    return {
        'timestamp': datetime.now().isoformat(),
        'overall_status': overall_status,
        'checks': checks
    }

def run_audit_check():
    """Check daily audit status"""
    try:
        result = subprocess.run(['tools/daily_audit.sh'], 
                              capture_output=True, text=True, timeout=30)
        return {
            'status': 'passed' if result.returncode == 0 else 'failed',
            'details': result.stdout[-200:] if result.stdout else 'No output'
        }
    except Exception as e:
        return {'status': 'failed', 'details': str(e)}

def run_test_check():
    """Check test suite status"""
    try:
        result = subprocess.run(['tools/test_builder.sh'], 
                              capture_output=True, text=True, timeout=60)
        passed_tests = result.stdout.count('✅') if result.stdout else 0
        return {
            'status': 'passed' if passed_tests >= 7 else 'warning',
            'details': f'{passed_tests} tests passed'
        }
    except Exception as e:
        return {'status': 'failed', 'details': str(e)}

def run_dependency_check():
    """Check dependency health"""
    try:
        result = subprocess.run(['python3', 'tools/quick_dependency_check.py'], 
                              capture_output=True, text=True, timeout=30)
        # Parse health score from output
        health_score = 100  # Default
        if 'Health Score:' in result.stdout:
            score_line = [line for line in result.stdout.split('\n') if 'Health Score:' in line][0]
            health_score = int(score_line.split(':')[1].strip().replace('%', ''))
        
        return {
            'status': 'passed' if health_score >= 80 else 'warning',
            'details': f'Health score: {health_score}%'
        }
    except Exception as e:
        return {'status': 'failed', 'details': str(e)}

def run_memory_check():
    """Check memory system health"""
    try:
        result = subprocess.run(['tools/memory/memory_status.sh'], 
                              capture_output=True, text=True, timeout=15)
        return {
            'status': 'passed' if result.returncode == 0 else 'warning',
            'details': 'Memory system accessible' if result.returncode == 0 else 'Memory issues detected'
        }
    except Exception as e:
        return {'status': 'failed', 'details': str(e)}

if __name__ == "__main__":
    health = check_system_health()
    print(json.dumps(health, indent=2))
    
    # Save status
    status_file = Path('{{CATALYST_ROOT}}/registry/health_status.json')
    with open(status_file, 'w') as f:
        json.dump(health, f, indent=2)
