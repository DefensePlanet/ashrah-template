#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Proactive Intelligence Monitor
Continuous background monitoring and proactive recommendation engine
"""

import json
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

class {{ORCHESTRATOR_NAME}}ProactiveMonitor:
    def __init__(self, builder_root: str = None):
        self.builder_root = Path(builder_root or '{{CATALYST_ROOT}}')
        self.monitoring_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/proactive_monitoring.json'
        self.recommendations_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/recommendations.json'
        
        # Ensure directories exist
        self.monitoring_db.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize monitoring state
        self.last_health_check = None
        self.trend_analysis = {}
        self.recommendation_queue = []
        
    def continuous_monitor(self, duration_minutes: int = 60) -> None:
        """Run continuous monitoring for specified duration"""
        print(f"🔍 Starting proactive monitoring for {duration_minutes} minutes...")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        while datetime.now() < end_time:
            try:
                self._perform_monitoring_cycle()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                print("\n⏹️ Monitoring stopped by user")
                break
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
                time.sleep(60)  # Wait longer on error
        
        print("✅ Proactive monitoring completed")
    
    def _perform_monitoring_cycle(self) -> None:
        """Perform one monitoring cycle"""
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'system_health': self._check_system_health(),
            'performance_metrics': self._collect_performance_metrics(),
            'usage_patterns': self._analyze_usage_patterns(),
            'potential_optimizations': self._identify_optimizations(),
            'threat_indicators': self._scan_threat_indicators()
        }
        
        # Analyze trends
        self._update_trend_analysis(monitoring_data)
        
        # Generate recommendations
        recommendations = self._generate_proactive_recommendations(monitoring_data)
        if recommendations:
            self._queue_recommendations(recommendations)
        
        # Save monitoring data
        self._save_monitoring_data(monitoring_data)
    
    def _check_system_health(self) -> Dict:
        """Check current system health status"""
        try:
            # Run health monitor
            result = subprocess.run(
                ['python3', str(self.builder_root / 'tools/health_monitor.py')],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                health_data = json.loads(result.stdout)
                return {
                    'status': health_data.get('overall_status', 'unknown'),
                    'checks': health_data.get('checks', {}),
                    'timestamp': health_data.get('timestamp'),
                    'health_score': self._calculate_health_score(health_data)
                }
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'health_score': 0}
        
        return {'status': 'unknown', 'health_score': 50}
    
    def _calculate_health_score(self, health_data: Dict) -> int:
        """Calculate numeric health score (0-100)"""
        checks = health_data.get('checks', {})
        if not checks:
            return 50
        
        passed_checks = sum(1 for check in checks.values() if check.get('status') == 'passed')
        total_checks = len(checks)
        
        return int((passed_checks / total_checks) * 100) if total_checks > 0 else 50
    
    def _collect_performance_metrics(self) -> Dict:
        """Collect system performance metrics"""
        metrics = {}
        
        try:
            # Disk usage
            result = subprocess.run(['df', '-h', str(self.builder_root)], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        metrics['disk_usage_percent'] = int(parts[4].rstrip('%'))
            
            # File counts in key directories
            metrics['capsule_count'] = len(list((self.builder_root / 'capsules').glob('*')))
            metrics['log_file_count'] = len(list(self.builder_root.glob('**/*.log')))
            metrics['temp_file_count'] = len(list(self.builder_root.glob('**/*.tmp')))
            
            # Recent activity
            recent_files = list(self.builder_root.glob('**/*'))
            day_ago = datetime.now() - timedelta(days=1)
            recent_count = sum(1 for f in recent_files 
                             if f.is_file() and 
                             datetime.fromtimestamp(f.stat().st_mtime) > day_ago)
            metrics['files_modified_last_24h'] = recent_count
            
        except Exception as e:
            metrics['error'] = str(e)
        
        return metrics
    
    def _analyze_usage_patterns(self) -> Dict:
        """Analyze recent usage patterns"""
        patterns = {}
        
        try:
            # Check recent git activity
            git_result = subprocess.run(
                ['git', 'log', '--oneline', '--since=24 hours ago'],
                cwd=self.builder_root, capture_output=True, text=True
            )
            if git_result.returncode == 0:
                patterns['git_commits_24h'] = len(git_result.stdout.strip().split('\n')) if git_result.stdout.strip() else 0
            
            # Check decision journal activity
            decision_journal = self.builder_root / 'capsules/builder-system/logs/decision_journal.md'
            if decision_journal.exists():
                with open(decision_journal, 'r') as f:
                    content = f.read()
                    recent_decisions = content.count(datetime.now().strftime('%Y-%m-%d'))
                    patterns['decisions_today'] = recent_decisions
            
            # Check active capsules
            active_capsules = []
            capsules_dir = self.builder_root / 'capsules'
            for capsule in capsules_dir.iterdir():
                if capsule.is_dir() and (capsule / 'capsule.json').exists():
                    try:
                        with open(capsule / 'capsule.json', 'r') as f:
                            capsule_data = json.load(f)
                            if capsule_data.get('status') == 'active':
                                active_capsules.append(capsule.name)
                    except:
                        continue
            patterns['active_capsules'] = active_capsules
            
        except Exception as e:
            patterns['error'] = str(e)
        
        return patterns
    
    def _identify_optimizations(self) -> List[Dict]:
        """Identify potential system optimizations"""
        optimizations = []
        
        try:
            # Check for large log files
            log_files = list(self.builder_root.glob('**/*.log'))
            large_logs = [f for f in log_files if f.stat().st_size > 10_000_000]  # > 10MB
            if large_logs:
                optimizations.append({
                    'type': 'maintenance',
                    'priority': 'medium',
                    'description': f'{len(large_logs)} log files > 10MB need rotation',
                    'action': 'rotate_logs',
                    'files': [str(f) for f in large_logs[:5]]
                })
            
            # Check for temporary files
            temp_files = list(self.builder_root.glob('**/*.tmp'))
            if len(temp_files) > 10:
                optimizations.append({
                    'type': 'cleanup',
                    'priority': 'low',
                    'description': f'{len(temp_files)} temporary files can be cleaned',
                    'action': 'cleanup_temp_files',
                    'count': len(temp_files)
                })
            
            # Check disk usage
            try:
                result = subprocess.run(['df', '-h', str(self.builder_root)], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        parts = lines[1].split()
                        if len(parts) >= 5:
                            usage_percent = int(parts[4].rstrip('%'))
                            if usage_percent > 80:
                                optimizations.append({
                                    'type': 'storage',
                                    'priority': 'high',
                                    'description': f'Disk usage at {usage_percent}% - cleanup recommended',
                                    'action': 'free_disk_space',
                                    'usage_percent': usage_percent
                                })
            except:
                pass
                
        except Exception as e:
            optimizations.append({
                'type': 'error',
                'description': f'Error identifying optimizations: {e}'
            })
        
        return optimizations
    
    def _scan_threat_indicators(self) -> List[Dict]:
        """Scan for potential security or stability threats"""
        threats = []
        
        try:
            # Check for potential secrets in recent commits
            git_result = subprocess.run(
                ['git', 'log', '--oneline', '--since=24 hours ago', '--grep=secret'],
                cwd=self.builder_root, capture_output=True, text=True
            )
            if git_result.returncode == 0 and git_result.stdout.strip():
                threats.append({
                    'type': 'security',
                    'priority': 'high',
                    'description': 'Recent commits mention "secret" - manual review recommended',
                    'action': 'review_recent_commits'
                })
            
            # Check for failed processes or error patterns
            error_patterns = ['ERROR', 'CRITICAL', 'FAILED']
            recent_logs = []
            for log_file in self.builder_root.glob('**/*.log'):
                try:
                    if (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days < 1:
                        recent_logs.append(log_file)
                except:
                    continue
            
            error_count = 0
            for log_file in recent_logs[:5]:  # Check up to 5 recent logs
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                        for pattern in error_patterns:
                            error_count += content.count(pattern)
                except:
                    continue
            
            if error_count > 10:
                threats.append({
                    'type': 'stability',
                    'priority': 'medium',
                    'description': f'{error_count} error patterns found in recent logs',
                    'action': 'investigate_errors',
                    'error_count': error_count
                })
                
        except Exception as e:
            threats.append({
                'type': 'monitoring_error',
                'description': f'Error scanning threats: {e}'
            })
        
        return threats
    
    def _update_trend_analysis(self, current_data: Dict) -> None:
        """Update trend analysis with current data"""
        # Load existing trends
        if hasattr(self, 'trend_analysis') and self.trend_analysis:
            trends = self.trend_analysis
        else:
            trends = {'health_scores': [], 'performance_trends': {}, 'pattern_changes': []}
        
        # Add current health score
        health_score = current_data.get('system_health', {}).get('health_score', 50)
        trends['health_scores'].append({
            'timestamp': current_data['timestamp'],
            'score': health_score
        })
        
        # Keep only last 24 hours of data
        cutoff_time = datetime.now() - timedelta(hours=24)
        trends['health_scores'] = [
            entry for entry in trends['health_scores']
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]
        
        # Analyze performance trends
        performance = current_data.get('performance_metrics', {})
        for metric, value in performance.items():
            if isinstance(value, (int, float)):
                if metric not in trends['performance_trends']:
                    trends['performance_trends'][metric] = []
                trends['performance_trends'][metric].append({
                    'timestamp': current_data['timestamp'],
                    'value': value
                })
                # Keep only recent data
                trends['performance_trends'][metric] = [
                    entry for entry in trends['performance_trends'][metric]
                    if datetime.fromisoformat(entry['timestamp']) > cutoff_time
                ]
        
        self.trend_analysis = trends
    
    def _generate_proactive_recommendations(self, monitoring_data: Dict) -> List[Dict]:
        """Generate proactive recommendations based on monitoring data"""
        recommendations = []
        
        # Health-based recommendations
        health_score = monitoring_data.get('system_health', {}).get('health_score', 50)
        if health_score < 70:
            recommendations.append({
                'type': 'proactive_maintenance',
                'priority': 'high',
                'description': f'System health score dropped to {health_score}% - maintenance recommended',
                'suggested_actions': ['Run comprehensive health check', 'Review failed components', 'Clear temporary files'],
                'confidence': 0.8,
                'trigger': 'health_score_threshold'
            })
        
        # Performance-based recommendations
        performance = monitoring_data.get('performance_metrics', {})
        if performance.get('disk_usage_percent', 0) > 85:
            recommendations.append({
                'type': 'resource_optimization',
                'priority': 'high',
                'description': f'Disk usage at {performance["disk_usage_percent"]}% - cleanup needed',
                'suggested_actions': ['Archive old logs', 'Clean temporary files', 'Review capsule storage'],
                'confidence': 0.9,
                'trigger': 'disk_usage_threshold'
            })
        
        # Pattern-based recommendations
        patterns = monitoring_data.get('usage_patterns', {})
        if patterns.get('decisions_today', 0) > 10:
            recommendations.append({
                'type': 'workflow_optimization',
                'priority': 'medium',
                'description': f'{patterns["decisions_today"]} decisions today - consider batch processing',
                'suggested_actions': ['Group similar decisions', 'Create decision templates', 'Implement approval workflows'],
                'confidence': 0.6,
                'trigger': 'high_decision_frequency'
            })
        
        # Trend-based recommendations
        if hasattr(self, 'trend_analysis') and self.trend_analysis.get('health_scores'):
            recent_scores = [entry['score'] for entry in self.trend_analysis['health_scores'][-5:]]
            if len(recent_scores) >= 3 and all(recent_scores[i] > recent_scores[i+1] for i in range(len(recent_scores)-1)):
                recommendations.append({
                    'type': 'trend_alert',
                    'priority': 'medium',
                    'description': 'Health score trending downward - preventive action recommended',
                    'suggested_actions': ['Investigate recent changes', 'Review system logs', 'Schedule maintenance'],
                    'confidence': 0.7,
                    'trigger': 'negative_health_trend'
                })
        
        return recommendations
    
    def _queue_recommendations(self, recommendations: List[Dict]) -> None:
        """Queue recommendations for review"""
        for rec in recommendations:
            rec['queued_at'] = datetime.now().isoformat()
            rec['status'] = 'pending'
            self.recommendation_queue.append(rec)
        
        # Save to persistent storage
        self._save_recommendations()
    
    def _save_monitoring_data(self, data: Dict) -> None:
        """Save monitoring data to persistent storage"""
        try:
            # Load existing data
            if self.monitoring_db.exists():
                with open(self.monitoring_db, 'r') as f:
                    existing_data = json.load(f)
            else:
                existing_data = {'monitoring_history': []}
            
            # Add current data
            existing_data['monitoring_history'].append(data)
            
            # Keep only last 48 hours
            cutoff_time = datetime.now() - timedelta(hours=48)
            existing_data['monitoring_history'] = [
                entry for entry in existing_data['monitoring_history']
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time
            ]
            
            # Save
            with open(self.monitoring_db, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving monitoring data: {e}")
    
    def _save_recommendations(self) -> None:
        """Save recommendations to persistent storage"""
        try:
            recommendations_data = {
                'last_updated': datetime.now().isoformat(),
                'pending_recommendations': self.recommendation_queue,
                'total_queued': len(self.recommendation_queue)
            }
            
            with open(self.recommendations_db, 'w') as f:
                json.dump(recommendations_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving recommendations: {e}")
    
    def get_current_recommendations(self) -> List[Dict]:
        """Get current pending recommendations"""
        try:
            if self.recommendations_db.exists():
                with open(self.recommendations_db, 'r') as f:
                    data = json.load(f)
                return data.get('pending_recommendations', [])
        except Exception:
            pass
        return []
    
    def generate_proactive_report(self) -> str:
        """Generate proactive intelligence report"""
        recommendations = self.get_current_recommendations()
        
        # Get recent monitoring data
        recent_data = None
        try:
            if self.monitoring_db.exists():
                with open(self.monitoring_db, 'r') as f:
                    monitoring_data = json.load(f)
                if monitoring_data.get('monitoring_history'):
                    recent_data = monitoring_data['monitoring_history'][-1]
        except Exception:
            pass
        
        report = f"""# {{ORCHESTRATOR_NAME}} Proactive Intelligence Report

## System Status
"""
        
        if recent_data:
            health = recent_data.get('system_health', {})
            performance = recent_data.get('performance_metrics', {})
            
            report += f"""- **Health Score:** {health.get('health_score', 'Unknown')}%
- **System Status:** {health.get('status', 'Unknown')}
- **Active Capsules:** {len(recent_data.get('usage_patterns', {}).get('active_capsules', []))}
- **Disk Usage:** {performance.get('disk_usage_percent', 'Unknown')}%
- **Recent Activity:** {performance.get('files_modified_last_24h', 'Unknown')} files modified in 24h

"""
        
        report += f"""## Proactive Recommendations ({len(recommendations)})
"""
        
        if recommendations:
            high_priority = [r for r in recommendations if r.get('priority') == 'high']
            medium_priority = [r for r in recommendations if r.get('priority') == 'medium']
            
            if high_priority:
                report += f"\n### High Priority ({len(high_priority)})\n"
                for i, rec in enumerate(high_priority, 1):
                    report += f"{i}. **{rec.get('description', 'No description')}**\n"
                    report += f"   - Type: {rec.get('type', 'Unknown')}\n"
                    report += f"   - Confidence: {rec.get('confidence', 0.0):.2f}\n"
                    if rec.get('suggested_actions'):
                        report += f"   - Actions: {', '.join(rec['suggested_actions'])}\n"
                    report += "\n"
            
            if medium_priority:
                report += f"\n### Medium Priority ({len(medium_priority)})\n"
                for i, rec in enumerate(medium_priority, 1):
                    report += f"{i}. {rec.get('description', 'No description')}\n"
        else:
            report += "\nNo pending recommendations - system operating optimally.\n"
        
        report += f"""
## Monitoring Summary
- **Last Check:** {recent_data.get('timestamp', 'Unknown') if recent_data else 'No data'}
- **Trend Analysis:** {'Active' if hasattr(self, 'trend_analysis') and self.trend_analysis else 'Inactive'}
- **Threat Scanning:** {'Active' if recent_data and recent_data.get('threat_indicators') is not None else 'Inactive'}
"""
        
        return report

def main():
    """Run proactive monitoring"""
    monitor = {{ORCHESTRATOR_NAME}}ProactiveMonitor()
    
    print("🧠 {{ORCHESTRATOR_NAME}} Proactive Intelligence Monitor")
    print("========================================")
    
    # Run one monitoring cycle
    monitor._perform_monitoring_cycle()
    
    # Generate and display report
    report = monitor.generate_proactive_report()
    print(report)
    
    # Save report
    report_file = monitor.builder_root / 'registry/{{ORCHESTRATOR_NAME_LOWER}}_proactive_report.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📊 Proactive report saved to: {report_file}")

if __name__ == "__main__":
    main()