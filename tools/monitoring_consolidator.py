#!/usr/bin/env python3
"""
Monitoring and Alerting Consolidator
Improves consistency across Catalyst monitoring
"""

import json
import os
from datetime import datetime
from pathlib import Path

class MonitoringConsolidator:
    def __init__(self):
        self.builder_root = Path('{{CATALYST_ROOT}}')
        self.registry_dir = self.builder_root / 'registry'
        self.global_dir = self.builder_root / 'global'
        
    def consolidate_health_signals(self):
        """Consolidate health monitoring across system"""
        health_config = {
            'version': '1.0',
            'updated': datetime.now().isoformat(),
            'health_checks': {
                'daily_audit': {
                    'command': 'tools/daily_audit.sh',
                    'frequency': 'daily',
                    'success_criteria': 'exit_code_0',
                    'alert_on_failure': True
                },
                'test_suite': {
                    'command': 'tools/test_builder.sh',
                    'frequency': 'on_change',
                    'success_criteria': 'passed_tests >= 7',
                    'alert_on_failure': False
                },
                'dependency_check': {
                    'command': 'python3 tools/quick_dependency_check.py',
                    'frequency': 'weekly',
                    'success_criteria': 'health_score >= 80',
                    'alert_on_failure': True
                },
                'memory_health': {
                    'command': 'tools/memory/memory_status.sh',
                    'frequency': 'daily',
                    'success_criteria': 'memory_accessible',
                    'alert_on_failure': True
                }
            },
            'alert_channels': {
                'desktop_notification': {
                    'enabled': True,
                    'severity_threshold': 'warning'
                },
                'log_file': {
                    'enabled': True,
                    'path': 'registry/alerts.log'
                }
            },
            'thresholds': {
                'warning': {
                    'failed_tests': 2,
                    'health_score_drop': 20,
                    'memory_usage': 80
                },
                'critical': {
                    'failed_tests': 5,
                    'health_score_drop': 50,
                    'memory_usage': 95
                }
            }
        }
        
        return health_config
    
    def create_alert_handler(self):
        """Create unified alert handling script"""
        alert_script = '''#!/bin/bash
# Unified Alert Handler for Catalyst

SEVERITY="$1"
MESSAGE="$2"
SOURCE="$3"

ALERT_LOG="{{CATALYST_ROOT}}/registry/alerts.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Log alert
echo "[$TIMESTAMP] [$SEVERITY] [$SOURCE] $MESSAGE" >> "$ALERT_LOG"

# Desktop notification for warnings and above
if [[ "$SEVERITY" != "info" ]]; then
    osascript -e "display notification \\"$MESSAGE\\" with title \\"Builder Alert\\" subtitle \\"$SOURCE ($SEVERITY)\\""
fi

# Critical alerts get additional attention
if [[ "$SEVERITY" == "critical" ]]; then
    echo "🚨 CRITICAL ALERT: $MESSAGE" | tee -a "$ALERT_LOG"
    # Could add additional escalation here
fi
'''
        return alert_script
    
    def create_health_monitor(self):
        """Create health monitoring dashboard"""
        monitor_script = '''#!/usr/bin/env python3
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
            score_line = [line for line in result.stdout.split('\\n') if 'Health Score:' in line][0]
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
'''
        return monitor_script
    
    def deploy_monitoring(self):
        """Deploy consolidated monitoring system"""
        # Create health config
        health_config = self.consolidate_health_signals()
        config_file = self.registry_dir / 'health_config.json'
        with open(config_file, 'w') as f:
            json.dump(health_config, f, indent=2)
        
        # Create alert handler
        alert_script = self.create_alert_handler()
        alert_file = self.builder_root / 'tools' / 'alert_handler.sh'
        with open(alert_file, 'w') as f:
            f.write(alert_script)
        os.chmod(alert_file, 0o755)
        
        # Create health monitor
        monitor_script = self.create_health_monitor()
        monitor_file = self.builder_root / 'tools' / 'health_monitor.py'
        with open(monitor_file, 'w') as f:
            f.write(monitor_script)
        
        return {
            'health_config': str(config_file),
            'alert_handler': str(alert_file),
            'health_monitor': str(monitor_file)
        }

def main():
    consolidator = MonitoringConsolidator()
    deployed = consolidator.deploy_monitoring()
    
    print("✅ Monitoring system consolidated and deployed")
    print(f"📊 Health config: {deployed['health_config']}")
    print(f"🚨 Alert handler: {deployed['alert_handler']}")
    print(f"💓 Health monitor: {deployed['health_monitor']}")
    
    # Test the health monitor
    print("\n🧪 Testing health monitor...")
    import subprocess
    result = subprocess.run(['python3', deployed['health_monitor']], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Health monitor working")
    else:
        print(f"❌ Health monitor error: {result.stderr}")

if __name__ == "__main__":
    main()