#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Learning Engine - Decision Pattern Analysis and Context Persistence
Implements Number-2 intelligence capabilities for Catalyst
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

class {{ORCHESTRATOR_NAME}}LearningEngine:
    def __init__(self, builder_root: str = None):
        self.builder_root = Path(builder_root or '{{CATALYST_ROOT}}')
        self.decision_journal = self.builder_root / 'capsules/builder-system/logs/decision_journal.md'
        self.learning_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/learning_database.json'
        self.context_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/context_persistence.json'
        self.patterns_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/decision_patterns.json'
        
        # Ensure directories exist
        self.learning_db.parent.mkdir(parents=True, exist_ok=True)
        
    def analyze_decision_patterns(self) -> Dict[str, Any]:
        """Analyze historical decisions to extract {{USER_NAME}}'s patterns"""
        patterns = {
            'risk_tolerance': {},
            'approval_patterns': {},
            'time_preferences': {},
            'priority_indicators': {},
            'communication_style': {},
            'last_updated': datetime.now().isoformat()
        }
        
        # Read decision journal
        if self.decision_journal.exists():
            with open(self.decision_journal, 'r') as f:
                content = f.read()
            
            decisions = self._parse_decision_entries(content)
            patterns.update(self._extract_patterns(decisions))
        
        # Save patterns
        with open(self.patterns_db, 'w') as f:
            json.dump(patterns, f, indent=2)
            
        return patterns
    
    def _parse_decision_entries(self, content: str) -> List[Dict]:
        """Parse decision journal entries into structured data"""
        entries = []
        current_entry = {}
        
        for line in content.split('\n'):
            if line.startswith('## '):
                if current_entry:
                    entries.append(current_entry)
                # Parse timestamp and basic info
                header = line[3:].strip()
                current_entry = {
                    'raw_header': header,
                    'timestamp': self._extract_timestamp(header),
                    'classification': self._extract_classification(header),
                    'description': self._extract_description(header)
                }
            elif line.startswith('**') and ':' in line:
                key = line.split('**')[1].split(':')[0].lower().replace(' ', '_')
                value = line.split(':', 1)[1].strip()
                current_entry[key] = value
        
        if current_entry:
            entries.append(current_entry)
            
        return entries
    
    def _extract_timestamp(self, header: str) -> Optional[str]:
        """Extract timestamp from decision header"""
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', header)
        return timestamp_match.group(1) if timestamp_match else None
    
    def _extract_classification(self, header: str) -> Optional[str]:
        """Extract risk classification from header"""
        if 'RED' in header:
            return 'RED'
        elif 'YELLOW' in header:
            return 'YELLOW'
        elif 'GREEN' in header:
            return 'GREEN'
        return None
    
    def _extract_description(self, header: str) -> str:
        """Extract decision description"""
        parts = header.split(' - ')
        return parts[-1] if len(parts) > 1 else header
    
    def _extract_patterns(self, decisions: List[Dict]) -> Dict:
        """Extract patterns from decision history"""
        patterns = {}
        
        # Risk tolerance analysis
        risk_counts = {'RED': 0, 'YELLOW': 0, 'GREEN': 0}
        approval_by_risk = {'RED': 0, 'YELLOW': 0, 'GREEN': 0}
        
        for decision in decisions:
            classification = decision.get('classification')
            if classification:
                risk_counts[classification] += 1
                if decision.get('decision') == 'approved':
                    approval_by_risk[classification] += 1
        
        patterns['risk_distribution'] = risk_counts
        patterns['approval_rates'] = {
            risk: (approval_by_risk[risk] / max(risk_counts[risk], 1)) * 100
            for risk in risk_counts.keys()
        }
        
        # Time patterns
        timestamps = [d.get('timestamp') for d in decisions if d.get('timestamp')]
        if timestamps:
            patterns['decision_frequency'] = len(timestamps)
            patterns['average_decisions_per_week'] = len(timestamps) / max(1, 
                (datetime.now() - datetime.fromisoformat(timestamps[0].replace(' ', 'T'))).days / 7)
        
        # Common categories
        categories = [d.get('nist_category') for d in decisions if d.get('nist_category')]
        if categories:
            category_counts = {}
            for cat in categories:
                category_counts[cat] = category_counts.get(cat, 0) + 1
            patterns['preferred_categories'] = category_counts
        
        return patterns
    
    def enhance_context_persistence(self, session_data: Dict) -> None:
        """Store and update cross-session context"""
        context = self._load_context_db()
        
        # Update session tracking
        session_id = session_data.get('session_id', datetime.now().strftime('%Y%m%d_%H%M%S'))
        context['sessions'][session_id] = {
            'timestamp': datetime.now().isoformat(),
            'decisions_made': session_data.get('decisions', []),
            'topics_discussed': session_data.get('topics', []),
            'outcomes': session_data.get('outcomes', []),
            'context_carry_forward': session_data.get('carry_forward', {})
        }
        
        # Update long-term memory
        self._update_long_term_memory(context, session_data)
        
        # Save updated context
        with open(self.context_db, 'w') as f:
            json.dump(context, f, indent=2)
    
    def _load_context_db(self) -> Dict:
        """Load existing context database"""
        if self.context_db.exists():
            with open(self.context_db, 'r') as f:
                return json.load(f)
        return {
            'sessions': {},
            'long_term_memory': {
                'preferences': {},
                'recurring_patterns': {},
                'project_history': {},
                'relationship_maps': {}
            },
            'proactive_insights': [],
            'learning_metrics': {
                'accuracy_score': 0.0,
                'pattern_confidence': 0.0,
                'prediction_success_rate': 0.0
            }
        }
    
    def _update_long_term_memory(self, context: Dict, session_data: Dict) -> None:
        """Update long-term patterns and preferences"""
        ltm = context['long_term_memory']
        
        # Update preferences based on decisions
        if 'preferences' in session_data:
            for pref_type, value in session_data['preferences'].items():
                if pref_type not in ltm['preferences']:
                    ltm['preferences'][pref_type] = []
                ltm['preferences'][pref_type].append({
                    'value': value,
                    'timestamp': datetime.now().isoformat(),
                    'confidence': session_data.get('confidence', 0.5)
                })
        
        # Track recurring patterns
        if 'patterns' in session_data:
            for pattern in session_data['patterns']:
                pattern_key = pattern.get('type', 'general')
                if pattern_key not in ltm['recurring_patterns']:
                    ltm['recurring_patterns'][pattern_key] = []
                ltm['recurring_patterns'][pattern_key].append({
                    'pattern': pattern,
                    'frequency': pattern.get('frequency', 1),
                    'last_seen': datetime.now().isoformat()
                })
    
    def generate_proactive_insights(self) -> List[Dict]:
        """Generate proactive recommendations based on learned patterns"""
        patterns = self.load_decision_patterns()
        context = self._load_context_db()
        insights = []
        
        # Analyze system health trends
        health_insight = self._analyze_system_health_trends()
        if health_insight:
            insights.append(health_insight)
        
        # Suggest optimizations based on patterns
        optimization_insights = self._suggest_optimizations(patterns, context)
        insights.extend(optimization_insights)
        
        # Predict potential issues
        predictive_insights = self._predict_potential_issues(patterns)
        insights.extend(predictive_insights)
        
        return insights
    
    def _analyze_system_health_trends(self) -> Optional[Dict]:
        """Analyze system health for proactive recommendations"""
        try:
            # Check recent health status
            health_file = self.builder_root / 'registry/health_status.json'
            if health_file.exists():
                with open(health_file, 'r') as f:
                    health = json.load(f)
                
                # Look for degradation patterns
                if health.get('overall_status') != 'healthy':
                    return {
                        'type': 'system_health',
                        'priority': 'high',
                        'recommendation': f"System status is {health.get('overall_status')} - proactive maintenance recommended",
                        'confidence': 0.8,
                        'suggested_actions': [
                            'Run comprehensive health check',
                            'Review failed components',
                            'Schedule maintenance window'
                        ]
                    }
        except Exception:
            pass
        return None
    
    def _suggest_optimizations(self, patterns: Dict, context: Dict) -> List[Dict]:
        """Suggest optimizations based on learned patterns"""
        insights = []
        
        # Capsule usage optimization
        if patterns.get('preferred_categories'):
            most_used = max(patterns['preferred_categories'].items(), key=lambda x: x[1])
            insights.append({
                'type': 'optimization',
                'priority': 'medium',
                'recommendation': f"Consider creating templates/shortcuts for {most_used[0]} category (used {most_used[1]} times)",
                'confidence': 0.7,
                'suggested_actions': [
                    f'Create {most_used[0]} template',
                    'Automate common workflows',
                    'Add shortcuts for frequent operations'
                ]
            })
        
        return insights
    
    def _predict_potential_issues(self, patterns: Dict) -> List[Dict]:
        """Predict potential issues based on patterns"""
        insights = []
        
        # Check for concerning trends
        approval_rates = patterns.get('approval_rates', {})
        if approval_rates.get('RED', 0) > 50:
            insights.append({
                'type': 'prediction',
                'priority': 'medium',
                'recommendation': "High RED classification approval rate suggests risk thresholds may need adjustment",
                'confidence': 0.6,
                'suggested_actions': [
                    'Review risk classification criteria',
                    'Analyze RED approvals for patterns',
                    'Consider threshold adjustments'
                ]
            })
        
        return insights
    
    def load_decision_patterns(self) -> Dict:
        """Load existing decision patterns"""
        if self.patterns_db.exists():
            with open(self.patterns_db, 'r') as f:
                return json.load(f)
        return {}
    
    def update_learning_metrics(self, accuracy_data: Dict) -> None:
        """Update learning effectiveness metrics"""
        context = self._load_context_db()
        metrics = context['learning_metrics']
        
        # Update accuracy based on feedback
        if 'prediction_correct' in accuracy_data:
            current_success = metrics.get('prediction_success_rate', 0.0)
            new_success = (current_success + (1.0 if accuracy_data['prediction_correct'] else 0.0)) / 2
            metrics['prediction_success_rate'] = new_success
        
        # Update pattern confidence
        if 'pattern_match' in accuracy_data:
            current_confidence = metrics.get('pattern_confidence', 0.0)
            new_confidence = (current_confidence + accuracy_data['pattern_match']) / 2
            metrics['pattern_confidence'] = new_confidence
        
        # Save updates
        with open(self.context_db, 'w') as f:
            json.dump(context, f, indent=2)
    
    def generate_learning_report(self) -> str:
        """Generate comprehensive learning status report"""
        patterns = self.load_decision_patterns()
        context = self._load_context_db()
        insights = self.generate_proactive_insights()
        
        report = f"""# {{ORCHESTRATOR_NAME}} Learning Engine Status Report

## Decision Pattern Analysis
- **Total Decisions Analyzed:** {patterns.get('risk_distribution', {}).get('GREEN', 0) + patterns.get('risk_distribution', {}).get('YELLOW', 0) + patterns.get('risk_distribution', {}).get('RED', 0)}
- **Risk Distribution:** {patterns.get('risk_distribution', {})}
- **Approval Rates:** {patterns.get('approval_rates', {})}
- **Decision Frequency:** {patterns.get('average_decisions_per_week', 0):.1f} per week

## Context Persistence
- **Active Sessions:** {len(context.get('sessions', {}))}
- **Long-term Memory Entries:** {len(context.get('long_term_memory', {}).get('preferences', {}))}
- **Pattern Confidence:** {context.get('learning_metrics', {}).get('pattern_confidence', 0.0):.2f}

## Proactive Intelligence
- **Current Insights:** {len(insights)}
- **High Priority:** {len([i for i in insights if i.get('priority') == 'high'])}
- **Prediction Success Rate:** {context.get('learning_metrics', {}).get('prediction_success_rate', 0.0):.2f}

## Current Insights
"""
        
        for i, insight in enumerate(insights, 1):
            report += f"\n### {i}. {insight.get('type', 'General').title()} - {insight.get('priority', 'medium').title()} Priority\n"
            report += f"**Recommendation:** {insight.get('recommendation', 'N/A')}\n"
            report += f"**Confidence:** {insight.get('confidence', 0.0):.2f}\n"
            if insight.get('suggested_actions'):
                report += f"**Actions:** {', '.join(insight['suggested_actions'])}\n"
        
        return report

def main():
    """Initialize and run learning engine"""
    engine = {{ORCHESTRATOR_NAME}}LearningEngine()
    
    print("🧠 Initializing {{ORCHESTRATOR_NAME}} Learning Engine...")
    
    # Analyze existing decision patterns
    patterns = engine.analyze_decision_patterns()
    print(f"✅ Analyzed {sum(patterns.get('risk_distribution', {}).values())} decisions")
    
    # Generate proactive insights
    insights = engine.generate_proactive_insights()
    print(f"💡 Generated {len(insights)} proactive insights")
    
    # Create learning report
    report = engine.generate_learning_report()
    print(report)
    
    # Save report
    report_file = engine.builder_root / 'registry/{{ORCHESTRATOR_NAME_LOWER}}_learning_report.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📊 Learning report saved to: {report_file}")

if __name__ == "__main__":
    main()