#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Session Manager - Cross-Session Context Persistence
Maintains continuity and relationship tracking for Number-2 intelligence
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

class {{ORCHESTRATOR_NAME}}SessionManager:
    def __init__(self, builder_root: str = None):
        self.builder_root = Path(builder_root or '{{CATALYST_ROOT}}')
        self.session_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/session_persistence.json'
        self.current_session = None
        
        # Ensure directory exists
        self.session_db.parent.mkdir(parents=True, exist_ok=True)
        
    def start_session(self, context: Dict = None) -> str:
        """Start new session with context carryover from previous sessions"""
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Load previous context
        previous_context = self._get_recent_context()
        
        # Create new session
        session_data = {
            'session_id': session_id,
            'start_time': datetime.now().isoformat(),
            'context_inherited': previous_context,
            'current_context': context or {},
            'decisions_made': [],
            'topics_discussed': [],
            'learnings_captured': [],
            'relationship_updates': [],
            'status': 'active'
        }
        
        self.current_session = session_data
        self._save_session(session_data)
        
        return session_id
    
    def update_session_context(self, updates: Dict) -> None:
        """Update current session with new context"""
        if not self.current_session:
            self.start_session()
        
        # Merge updates into current context
        current_context = self.current_session.get('current_context', {})
        current_context.update(updates)
        self.current_session['current_context'] = current_context
        
        # Track significant updates
        if 'decisions' in updates:
            self.current_session['decisions_made'].extend(updates['decisions'])
        if 'topics' in updates:
            self.current_session['topics_discussed'].extend(updates['topics'])
        if 'learnings' in updates:
            self.current_session['learnings_captured'].extend(updates['learnings'])
        
        self._save_session(self.current_session)
    
    def log_decision_pattern(self, decision: Dict) -> None:
        """Log decision with context for pattern learning"""
        if not self.current_session:
            self.start_session()
        
        enhanced_decision = {
            **decision,
            'session_id': self.current_session['session_id'],
            'context_at_time': self.current_session.get('current_context', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        self.current_session['decisions_made'].append(enhanced_decision)
        self._save_session(self.current_session)
        
        # Also update MCP memory with relationship data
        self._update_mcp_relationships(enhanced_decision)
    
    def _update_mcp_relationships(self, decision: Dict) -> None:
        """Update MCP memory with decision relationship data"""
        try:
            from mcp__builder_memory__add_observations import add_observations
            
            # Add decision pattern observations
            observations = [
                f"Decision: {decision.get('description', 'Unknown')}",
                f"Classification: {decision.get('classification', 'Unknown')}",
                f"Outcome: {decision.get('outcome', 'Pending')}",
                f"Context: {decision.get('reasoning', 'N/A')}"
            ]
            
            add_observations([{
                'entityName': '{{USER_NAME}}',
                'contents': observations
            }])
        except Exception as e:
            # Fallback to local storage if MCP unavailable
            pass
    
    def get_carry_forward_context(self) -> Dict:
        """Get context to carry forward to next session"""
        if not self.current_session:
            return {}
        
        # Extract key insights and patterns
        carry_forward = {
            'recent_decisions': self.current_session.get('decisions_made', [])[-3:],  # Last 3 decisions
            'active_topics': list(set(self.current_session.get('topics_discussed', [])))[-5:],  # Last 5 unique topics
            'current_priorities': self.current_session.get('current_context', {}).get('priorities', []),
            'relationship_insights': self._extract_relationship_insights(),
            'learning_summary': self._generate_learning_summary()
        }
        
        return carry_forward
    
    def _extract_relationship_insights(self) -> List[Dict]:
        """Extract insights about relationships and patterns"""
        insights = []
        
        if self.current_session and self.current_session.get('decisions_made'):
            decisions = self.current_session['decisions_made']
            
            # Pattern: Classification preference
            classifications = [d.get('classification') for d in decisions if d.get('classification')]
            if classifications:
                most_common = max(set(classifications), key=classifications.count)
                insights.append({
                    'type': 'classification_preference',
                    'pattern': f"Tends toward {most_common} classifications in current session",
                    'confidence': 0.7,
                    'sample_size': len(classifications)
                })
            
            # Pattern: Decision speed
            decision_times = []
            for i in range(1, len(decisions)):
                if decisions[i-1].get('timestamp') and decisions[i].get('timestamp'):
                    prev_time = datetime.fromisoformat(decisions[i-1]['timestamp'])
                    curr_time = datetime.fromisoformat(decisions[i]['timestamp'])
                    decision_times.append((curr_time - prev_time).total_seconds() / 60)  # minutes
            
            if decision_times:
                avg_time = sum(decision_times) / len(decision_times)
                insights.append({
                    'type': 'decision_timing',
                    'pattern': f"Average time between decisions: {avg_time:.1f} minutes",
                    'confidence': 0.6,
                    'sample_size': len(decision_times)
                })
        
        return insights
    
    def _generate_learning_summary(self) -> Dict:
        """Generate summary of session learnings"""
        if not self.current_session:
            return {}
        
        return {
            'total_decisions': len(self.current_session.get('decisions_made', [])),
            'topics_covered': len(set(self.current_session.get('topics_discussed', []))),
            'new_patterns_identified': len(self.current_session.get('learnings_captured', [])),
            'session_duration_minutes': self._calculate_session_duration(),
            'effectiveness_score': self._calculate_effectiveness_score()
        }
    
    def _calculate_session_duration(self) -> float:
        """Calculate current session duration in minutes"""
        if not self.current_session or not self.current_session.get('start_time'):
            return 0.0
        
        start_time = datetime.fromisoformat(self.current_session['start_time'])
        duration = datetime.now() - start_time
        return duration.total_seconds() / 60
    
    def _calculate_effectiveness_score(self) -> float:
        """Calculate session effectiveness score"""
        if not self.current_session:
            return 0.0
        
        decisions = len(self.current_session.get('decisions_made', []))
        topics = len(set(self.current_session.get('topics_discussed', [])))
        duration = max(self._calculate_session_duration(), 1.0)  # Avoid division by zero
        
        # Simple effectiveness metric: (decisions + topics) per hour
        effectiveness = ((decisions * 2 + topics) / duration) * 60  # Per hour
        return min(effectiveness, 10.0)  # Cap at 10
    
    def _get_recent_context(self) -> Dict:
        """Get context from recent sessions"""
        sessions = self._load_all_sessions()
        if not sessions:
            return {}
        
        # Get context from last session
        recent_sessions = sorted(sessions, key=lambda x: x.get('start_time', ''), reverse=True)[:3]
        
        combined_context = {
            'recent_patterns': [],
            'ongoing_topics': [],
            'persistent_preferences': {},
            'relationship_history': []
        }
        
        for session in recent_sessions:
            # Aggregate patterns
            if session.get('learnings_captured'):
                combined_context['recent_patterns'].extend(session['learnings_captured'])
            
            # Carry forward active topics
            if session.get('topics_discussed'):
                combined_context['ongoing_topics'].extend(session['topics_discussed'])
        
        # Deduplicate and limit
        combined_context['ongoing_topics'] = list(set(combined_context['ongoing_topics']))[-10:]
        
        return combined_context
    
    def _load_all_sessions(self) -> List[Dict]:
        """Load all session data"""
        if not self.session_db.exists():
            return []
        
        try:
            with open(self.session_db, 'r') as f:
                data = json.load(f)
            return data.get('sessions', [])
        except Exception:
            return []
    
    def _save_session(self, session_data: Dict) -> None:
        """Save session data to persistent storage"""
        all_sessions = self._load_all_sessions()
        
        # Update or add current session
        session_id = session_data['session_id']
        updated = False
        for i, session in enumerate(all_sessions):
            if session.get('session_id') == session_id:
                all_sessions[i] = session_data
                updated = True
                break
        
        if not updated:
            all_sessions.append(session_data)
        
        # Keep only recent sessions (last 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        all_sessions = [
            s for s in all_sessions 
            if datetime.fromisoformat(s.get('start_time', '2000-01-01T00:00:00')) > cutoff_date
        ]
        
        # Save to file
        session_db_data = {
            'last_updated': datetime.now().isoformat(),
            'total_sessions': len(all_sessions),
            'sessions': all_sessions
        }
        
        with open(self.session_db, 'w') as f:
            json.dump(session_db_data, f, indent=2)
    
    def end_session(self) -> Dict:
        """End current session and prepare context for next session"""
        if not self.current_session:
            return {}
        
        # Generate session summary
        self.current_session['end_time'] = datetime.now().isoformat()
        self.current_session['status'] = 'completed'
        self.current_session['session_summary'] = self._generate_learning_summary()
        self.current_session['carry_forward'] = self.get_carry_forward_context()
        
        # Save final session state
        self._save_session(self.current_session)
        
        summary = self.current_session['session_summary'].copy()
        summary['session_id'] = self.current_session['session_id']
        
        # Clear current session
        self.current_session = None
        
        return summary
    
    def get_session_insights(self) -> Dict:
        """Get insights about current session"""
        if not self.current_session:
            return {'status': 'no_active_session'}
        
        return {
            'session_id': self.current_session['session_id'],
            'duration_minutes': self._calculate_session_duration(),
            'decisions_count': len(self.current_session.get('decisions_made', [])),
            'topics_count': len(set(self.current_session.get('topics_discussed', []))),
            'effectiveness_score': self._calculate_effectiveness_score(),
            'recent_patterns': self._extract_relationship_insights(),
            'status': 'active'
        }

def main():
    """Test session manager functionality"""
    manager = {{ORCHESTRATOR_NAME}}SessionManager()
    
    print("🔄 Testing {{ORCHESTRATOR_NAME}} Session Manager...")
    
    # Start session
    session_id = manager.start_session({'initial_context': 'test_session'})
    print(f"✅ Started session: {session_id}")
    
    # Add some test data
    manager.update_session_context({
        'topics': ['system_optimization', 'decision_patterns'],
        'decisions': [{
            'classification': 'GREEN',
            'description': 'Test optimization',
            'outcome': 'approved'
        }]
    })
    
    # Get insights
    insights = manager.get_session_insights()
    print(f"📊 Session insights: {insights}")
    
    # End session
    summary = manager.end_session()
    print(f"🏁 Session ended: {summary}")

if __name__ == "__main__":
    main()