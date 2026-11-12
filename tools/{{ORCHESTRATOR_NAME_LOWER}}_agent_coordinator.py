#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Advanced Agent Coordination System
Orchestrates multi-agent workflows and specialist collaboration
Enhanced with Context Intelligence for smart delegation
"""

import json
import asyncio
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Import context intelligence components and telemetry helpers
try:
    from context_intelligence_engine import ContextIntelligenceEngine, ContextType, PrivacyLevel
    from context_analyzer import ContextAnalyzer
    from task_analyzer import TaskAnalyzer, TaskCharacteristics
    CONTEXT_INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Context intelligence not available: {e}")
    CONTEXT_INTELLIGENCE_AVAILABLE = False
    TaskAnalyzer = None

try:
    from .agent_effectiveness_tracker import AgentEffectivenessTracker, AgentPerformanceRecord  # type: ignore
except Exception:
    try:
        from agent_effectiveness_tracker import AgentEffectivenessTracker, AgentPerformanceRecord  # type: ignore
    except ImportError as e:
        logging.warning(f"Agent effectiveness tracking unavailable: {e}")
        AgentEffectivenessTracker = None
        AgentPerformanceRecord = None

try:
    from .agent_usage_tracker import AgentUsageTracker  # type: ignore
except Exception:
    try:
        from agent_usage_tracker import AgentUsageTracker  # type: ignore
    except ImportError as e:
        logging.warning(f"Agent usage tracker unavailable: {e}")
        AgentUsageTracker = None

logger = logging.getLogger(__name__)

@dataclass
class AgentTask:
    agent_type: str
    task_description: str
    priority: str  # high, medium, low
    dependencies: List[str]  # List of task IDs this depends on
    expected_output: str
    timeout_minutes: int = 30
    status: str = 'pending'  # pending, running, completed, failed
    task_id: str = None
    assigned_at: str = None
    completed_at: str = None
    output: Dict = None
    error: str = None

@dataclass
class WorkflowPlan:
    workflow_id: str
    description: str
    tasks: List[AgentTask]
    coordination_strategy: str  # sequential, parallel, dependency_based
    created_at: str
    status: str = 'planned'  # planned, executing, completed, failed

@dataclass
class ContextBriefing:
    """Context briefing for agent delegation"""
    relevant_context: List[Dict[str, Any]]
    success_patterns: List[str]
    potential_pitfalls: List[str]
    domain_insights: Dict[str, Any]
    confidence_score: float
    recommendations: List[str]

@dataclass
class EnhancedAgentRecommendation:
    """Enhanced agent recommendation with context"""
    agent_type: str
    confidence_score: float
    context_alignment: float
    effectiveness_score: float
    risk_assessment: str
    reasoning: str
    context_briefing: ContextBriefing

class {{ORCHESTRATOR_NAME}}AgentCoordinator:
    def __init__(self, builder_root: str = None):
        self.builder_root = Path(builder_root or '{{CATALYST_ROOT}}')
        self.workflows_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/agent_workflows.json'
        self.coordination_db = self.builder_root / 'global/{{ORCHESTRATOR_NAME_LOWER}}/coordination_history.json'
        
        # Ensure directories exist
        self.workflows_db.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize context intelligence if available
        if CONTEXT_INTELLIGENCE_AVAILABLE and ContextIntelligenceEngine and ContextAnalyzer and TaskAnalyzer:
            self.context_engine = ContextIntelligenceEngine()
            self.context_analyzer = ContextAnalyzer(self.context_engine)
            self.task_analyzer = TaskAnalyzer()
            logger.info("{{ORCHESTRATOR_NAME}} initialized with Context Intelligence")
        else:
            self.context_engine = None
            self.context_analyzer = None
            self.task_analyzer = None
            logger.warning("{{ORCHESTRATOR_NAME}} initialized without Context Intelligence")

        self.effectiveness_tracker = AgentEffectivenessTracker() if AgentEffectivenessTracker else None
        self.usage_tracker = AgentUsageTracker() if AgentUsageTracker else None

        if not self.effectiveness_tracker:
            logger.warning("Agent effectiveness tracker unavailable; telemetry will be limited")
        if AgentUsageTracker and not self.usage_tracker:
            logger.warning("Agent usage tracker failed to initialize")
        
        # Current session tracking
        self.current_session_id = None
        self.conversation_history = []
        
        # Available specialist agents
        self.available_agents = {
            'code_reviewer': {
                'description': 'Quality, security, best practices analysis',
                'typical_tasks': ['code_review', 'security_audit', 'best_practices_check'],
                'estimated_time': 15
            },
            'system_architect': {
                'description': 'Design, scalability, planning',
                'typical_tasks': ['architecture_design', 'scalability_analysis', 'system_planning'],
                'estimated_time': 30
            },
            'security_analyst': {
                'description': 'Threat modeling, vulnerability assessment',
                'typical_tasks': ['threat_modeling', 'vulnerability_scan', 'security_compliance'],
                'estimated_time': 20
            },
            'performance_optimizer': {
                'description': 'Bottleneck identification, optimization',
                'typical_tasks': ['performance_analysis', 'optimization_suggestions', 'resource_monitoring'],
                'estimated_time': 25
            },
            'debugger': {
                'description': 'Issue investigation, root cause analysis',
                'typical_tasks': ['error_investigation', 'root_cause_analysis', 'debugging'],
                'estimated_time': 20
            },
            'frontend_specialist': {
                'description': 'UI/UX, accessibility, modern web tech',
                'typical_tasks': ['ui_development', 'accessibility_audit', 'frontend_optimization'],
                'estimated_time': 35
            }
        }
    
    def start_context_session(self, session_id: str = None, user_intent: str = "", 
                             active_capsule: str = None) -> str:
        """Start a new context-aware session"""
        if not session_id:
            session_id = f"{{ORCHESTRATOR_NAME_LOWER}}_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session_id = session_id
        self.conversation_history = []
        
        if self.context_engine:
            self.context_engine.start_session(session_id, user_intent, active_capsule)
            logger.info(f"Started context session: {session_id}")
        
        return session_id
    
    def get_agent_recommendations_with_context(self, task_description: str, 
                                              user_input: str = "",
                                              priority: str = "medium") -> List[EnhancedAgentRecommendation]:
        """Get intelligent agent recommendations using context intelligence"""
        if not CONTEXT_INTELLIGENCE_AVAILABLE:
            # Fallback to basic recommendations
            return self._get_basic_agent_recommendations(task_description)
        
        try:
            # Analyze task with context
            task_analysis = self.task_analyzer.analyze_task(task_description, {
                "user_input": user_input,
                "priority": priority,
                "session_id": self.current_session_id
            })
            
            # Get context analysis
            context_analysis = self.context_analyzer.analyze_context_relevance(
                query=task_description,
                task_type=task_analysis.task_type,
                domain=task_analysis.primary_domain
            )
            
            # Get agent effectiveness data
            agent_metrics = self.effectiveness_tracker.get_all_agent_metrics()
            
            # Generate enhanced recommendations
            recommendations = []
            
            # Analyze each available agent
            for agent_type, agent_info in self.available_agents.items():
                # Calculate base effectiveness score
                effectiveness_score = self._calculate_agent_effectiveness(
                    agent_type, task_analysis, agent_metrics
                )
                
                # Calculate context alignment
                context_alignment = self._calculate_context_alignment(
                    agent_type, context_analysis.relevant_entities
                )
                
                # Calculate confidence score
                confidence_score = (effectiveness_score + context_alignment) / 2.0
                
                # Risk assessment
                risk_assessment = self._assess_delegation_risk(
                    agent_type, task_analysis, context_analysis
                )
                
                # Generate reasoning
                reasoning = self._generate_delegation_reasoning(
                    agent_type, task_analysis, context_analysis, 
                    effectiveness_score, context_alignment
                )
                
                # Create context briefing
                context_briefing = self._create_context_briefing(
                    agent_type, context_analysis, task_analysis
                )
                
                recommendation = EnhancedAgentRecommendation(
                    agent_type=agent_type,
                    confidence_score=confidence_score,
                    context_alignment=context_alignment,
                    effectiveness_score=effectiveness_score,
                    risk_assessment=risk_assessment,
                    reasoning=reasoning,
                    context_briefing=context_briefing
                )
                
                recommendations.append(recommendation)
            
            # Sort by confidence score
            recommendations.sort(key=lambda x: x.confidence_score, reverse=True)
            
            logger.info(f"Generated {len(recommendations)} context-aware agent recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Context-aware recommendations failed: {e}")
            return self._get_basic_agent_recommendations(task_description)
    
    def delegate_with_context(self, task_description: str, user_input: str = "",
                             auto_select: bool = False, min_confidence: float = 0.7) -> Dict[str, Any]:
        """Delegate task using context intelligence"""
        if not self.current_session_id:
            self.start_context_session()
        
        # Get context-aware recommendations
        recommendations = self.get_agent_recommendations_with_context(
            task_description, user_input
        )
        
        if not recommendations:
            return {"error": "No agent recommendations available"}
        
        # Select best agent
        best_recommendation = recommendations[0]
        
        # Check confidence threshold
        if best_recommendation.confidence_score < min_confidence and not auto_select:
            return {
                "requires_approval": True,
                "recommendations": [asdict(r) for r in recommendations[:3]],
                "reason": f"Low confidence ({best_recommendation.confidence_score:.2f} < {min_confidence})"
            }
        
        # Proceed with delegation
        selected_agent = best_recommendation.agent_type
        
        # Track conversation turn
        if self.context_engine:
            self.context_engine.track_conversation_turn(
                user_input=user_input,
                agent_response=f"Delegating to {selected_agent}: {task_description}",
                agent_name="{{ORCHESTRATOR_NAME}}",
                metadata={
                    "delegation_confidence": best_recommendation.confidence_score,
                    "selected_agent": selected_agent,
                    "task_type": task_description
                }
            )
        
        # Record delegation
        delegation_id = None
        if self.effectiveness_tracker:
            delegation_id = self.effectiveness_tracker.record_agent_invocation(
                agent_type=selected_agent,
                task_description=task_description,
                context={
                    "user_input": user_input,
                    "confidence_score": best_recommendation.confidence_score,
                    "context_alignment": best_recommendation.context_alignment,
                    "session_id": self.current_session_id
                }
            )
        
        return {
            "delegated_to": selected_agent,
            "confidence": best_recommendation.confidence_score,
            "context_briefing": asdict(best_recommendation.context_briefing),
            "reasoning": best_recommendation.reasoning,
            "risk_assessment": best_recommendation.risk_assessment,
            "delegation_id": delegation_id,
            "all_recommendations": [asdict(r) for r in recommendations]
        }
    
    def _calculate_agent_effectiveness(self, agent_type: str, task_analysis: Any, 
                                     agent_metrics: Dict[str, Any]) -> float:
        """Calculate agent effectiveness score"""
        if not agent_metrics or agent_type not in agent_metrics:
            return 0.5  # Default score for new agents
        
        metrics = agent_metrics[agent_type]
        
        # Base effectiveness from historical performance
        success_rate = metrics.success_rate if hasattr(metrics, 'success_rate') else 0.5
        avg_completion_time = getattr(metrics, 'avg_completion_time', 30.0)
        
        # Adjust for task complexity
        complexity_factor = 1.0
        if hasattr(task_analysis, 'complexity_score'):
            if task_analysis.complexity_score > 0.8:
                complexity_factor = 0.9  # Slightly lower for very complex tasks
            elif task_analysis.complexity_score < 0.3:
                complexity_factor = 1.1  # Boost for simple tasks
        
        # Time efficiency factor
        expected_time = self.available_agents.get(agent_type, {}).get('estimated_time', 30)
        time_factor = min(1.2, expected_time / max(avg_completion_time, 1.0))
        
        effectiveness = success_rate * complexity_factor * time_factor
        return min(1.0, max(0.0, effectiveness))
    
    def _calculate_context_alignment(self, agent_type: str, 
                                   relevant_entities: List[Any]) -> float:
        """Calculate how well agent aligns with relevant context"""
        if not relevant_entities:
            return 0.5  # Neutral alignment
        
        alignment_scores = []
        
        for entity in relevant_entities[:5]:  # Top 5 most relevant
            if hasattr(entity, 'source_agent') and entity.source_agent:
                if entity.source_agent.lower() == agent_type.lower():
                    alignment_scores.append(1.0)  # Perfect match
                elif self._are_related_agents(agent_type, entity.source_agent):
                    alignment_scores.append(0.7)  # Related agent
                else:
                    alignment_scores.append(0.3)  # Different agent
            else:
                alignment_scores.append(0.5)  # Unknown source
        
        return sum(alignment_scores) / len(alignment_scores) if alignment_scores else 0.5
    
    def _are_related_agents(self, agent1: str, agent2: str) -> bool:
        """Check if two agents are in related domains"""
        related_groups = [
            ["frontend_specialist", "debugger", "performance_optimizer"],
            ["system_architect", "security_analyst"],
            ["code_reviewer", "debugger", "security_analyst"]
        ]
        
        agent1_lower = agent1.lower()
        agent2_lower = agent2.lower()
        
        for group in related_groups:
            if any(agent1_lower in a.lower() for a in group) and any(agent2_lower in a.lower() for a in group):
                return True
        
        return False
    
    def _assess_delegation_risk(self, agent_type: str, task_analysis: Any, 
                              context_analysis: Any) -> str:
        """Assess risk level for delegating to specific agent"""
        risk_factors = []
        
        # Task complexity risk
        if hasattr(task_analysis, 'complexity_score') and task_analysis.complexity_score > 0.8:
            risk_factors.append("high_complexity")
        
        # Context uncertainty risk
        if len(context_analysis.relevant_entities) < 2:
            risk_factors.append("limited_context")
        
        # Agent experience risk
        agent_info = self.available_agents.get(agent_type, {})
        typical_tasks = agent_info.get('typical_tasks', [])
        
        task_type = getattr(task_analysis, 'task_type', '').lower()
        if not any(task_type in task.lower() for task in typical_tasks):
            risk_factors.append("outside_expertise")
        
        # Determine overall risk
        if len(risk_factors) >= 3:
            return "RED"  # High risk
        elif len(risk_factors) >= 1:
            return "YELLOW"  # Medium risk
        else:
            return "GREEN"  # Low risk
    
    def _generate_delegation_reasoning(self, agent_type: str, task_analysis: Any,
                                     context_analysis: Any, effectiveness_score: float,
                                     context_alignment: float) -> str:
        """Generate human-readable reasoning for delegation choice"""
        reasons = []
        
        # Effectiveness reasoning
        if effectiveness_score > 0.8:
            reasons.append(f"{agent_type} has strong historical performance")
        elif effectiveness_score > 0.6:
            reasons.append(f"{agent_type} has moderate historical performance")
        else:
            reasons.append(f"{agent_type} has limited performance history")
        
        # Context reasoning
        if context_alignment > 0.7:
            reasons.append("strong alignment with recent context")
        elif context_alignment > 0.4:
            reasons.append("moderate context alignment")
        else:
            reasons.append("limited context alignment")
        
        # Task type reasoning
        agent_info = self.available_agents.get(agent_type, {})
        task_type = getattr(task_analysis, 'task_type', '')
        
        if task_type in str(agent_info.get('typical_tasks', [])).lower():
            reasons.append("task type matches agent expertise")
        
        return "; ".join(reasons)
    
    def _create_context_briefing(self, agent_type: str, context_analysis: Any, 
                               task_analysis: Any) -> ContextBriefing:
        """Create context briefing for agent"""
        relevant_context = []
        success_patterns = []
        potential_pitfalls = []
        
        # Extract relevant context
        for entity in context_analysis.relevant_entities[:3]:
            relevant_context.append({
                "type": entity.entity_id if hasattr(entity, 'entity_id') else "unknown",
                "content_summary": str(entity)[:100] + "..." if len(str(entity)) > 100 else str(entity),
                "relevance_score": getattr(entity, 'overall_score', 0.0)
            })
        
        # Extract patterns from recommendations
        if hasattr(context_analysis, 'recommendations'):
            for rec in context_analysis.recommendations:
                if "success" in rec.lower():
                    success_patterns.append(rec)
                elif "issue" in rec.lower() or "problem" in rec.lower():
                    potential_pitfalls.append(rec)
        
        # Domain insights
        domain_insights = {
            "primary_domain": getattr(task_analysis, 'primary_domain', 'general'),
            "complexity_score": getattr(task_analysis, 'complexity_score', 0.5),
            "domain_distribution": context_analysis.domain_distribution
        }
        
        # Calculate confidence
        confidence_score = (len(relevant_context) / 3.0 + 
                          len(success_patterns) / 3.0 + 
                          (1.0 if domain_insights['primary_domain'] != 'general' else 0.0)) / 3.0
        
        return ContextBriefing(
            relevant_context=relevant_context,
            success_patterns=success_patterns,
            potential_pitfalls=potential_pitfalls,
            domain_insights=domain_insights,
            confidence_score=min(1.0, confidence_score),
            recommendations=context_analysis.recommendations[:3]
        )
    
    def _get_basic_agent_recommendations(self, task_description: str) -> List[EnhancedAgentRecommendation]:
        """Fallback basic agent recommendations"""
        task_lower = task_description.lower()
        
        # Simple keyword matching
        agent_scores = {}
        for agent_type, agent_info in self.available_agents.items():
            score = 0.5  # Base score
            
            # Check if task description matches typical tasks
            for typical_task in agent_info.get('typical_tasks', []):
                if any(word in task_lower for word in typical_task.split('_')):
                    score += 0.3
            
            agent_scores[agent_type] = min(1.0, score)
        
        # Create basic recommendations
        recommendations = []
        for agent_type, score in sorted(agent_scores.items(), key=lambda x: x[1], reverse=True):
            basic_briefing = ContextBriefing(
                relevant_context=[],
                success_patterns=[],
                potential_pitfalls=[],
                domain_insights={},
                confidence_score=0.3,
                recommendations=["Limited context available - basic task matching"]
            )
            
            recommendation = EnhancedAgentRecommendation(
                agent_type=agent_type,
                confidence_score=score,
                context_alignment=0.5,
                effectiveness_score=0.5,
                risk_assessment="YELLOW",
                reasoning=f"Basic keyword matching for {agent_type}",
                context_briefing=basic_briefing
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def create_workflow(self, description: str, tasks: List[Dict], strategy: str = 'dependency_based') -> WorkflowPlan:
        """Create a new multi-agent workflow"""
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Convert task dictionaries to AgentTask objects
        agent_tasks = []
        for i, task_dict in enumerate(tasks):
            task = AgentTask(
                task_id=f"{workflow_id}_task_{i+1}",
                agent_type=task_dict['agent_type'],
                task_description=task_dict['description'],
                priority=task_dict.get('priority', 'medium'),
                dependencies=task_dict.get('dependencies', []),
                expected_output=task_dict.get('expected_output', 'Analysis report'),
                timeout_minutes=task_dict.get('timeout_minutes', 
                    self.available_agents.get(task_dict['agent_type'], {}).get('estimated_time', 30))
            )
            agent_tasks.append(task)
        
        workflow = WorkflowPlan(
            workflow_id=workflow_id,
            description=description,
            tasks=agent_tasks,
            coordination_strategy=strategy,
            created_at=datetime.now().isoformat()
        )
        
        self._save_workflow(workflow)
        return workflow
    
    def execute_workflow(self, workflow: WorkflowPlan) -> Dict:
        """Execute a multi-agent workflow"""
        print(f"🎯 Executing workflow: {workflow.description}")
        
        workflow.status = 'executing'
        self._save_workflow(workflow)
        
        execution_log = {
            'workflow_id': workflow.workflow_id,
            'start_time': datetime.now().isoformat(),
            'task_results': {},
            'coordination_events': [],
            'final_status': 'unknown'
        }
        
        try:
            if workflow.coordination_strategy == 'sequential':
                results = self._execute_sequential(workflow, execution_log)
            elif workflow.coordination_strategy == 'parallel':
                results = self._execute_parallel(workflow, execution_log)
            else:  # dependency_based
                results = self._execute_dependency_based(workflow, execution_log)
            
            workflow.status = 'completed'
            execution_log['final_status'] = 'completed'
            
        except Exception as e:
            workflow.status = 'failed'
            execution_log['final_status'] = 'failed'
            execution_log['error'] = str(e)
            print(f"❌ Workflow failed: {e}")
        
        execution_log['end_time'] = datetime.now().isoformat()
        self._save_workflow(workflow)
        self._save_coordination_history(execution_log)
        
        return execution_log
    
    def _execute_sequential(self, workflow: WorkflowPlan, execution_log: Dict) -> Dict:
        """Execute tasks sequentially"""
        results = {}
        
        for task in workflow.tasks:
            execution_log['coordination_events'].append({
                'event': 'task_started',
                'task_id': task.task_id,
                'timestamp': datetime.now().isoformat()
            })
            
            result = self._execute_single_task(task)
            results[task.task_id] = result
            execution_log['task_results'][task.task_id] = result
            
            if result['status'] == 'failed':
                raise Exception(f"Task {task.task_id} failed: {result.get('error', 'Unknown error')}")
        
        return results
    
    def _execute_parallel(self, workflow: WorkflowPlan, execution_log: Dict) -> Dict:
        """Execute tasks in parallel (simplified synchronous version)"""
        results = {}
        
        # For now, implement as concurrent execution simulation
        # In a full implementation, this would use asyncio or threading
        for task in workflow.tasks:
            execution_log['coordination_events'].append({
                'event': 'task_started',
                'task_id': task.task_id,
                'timestamp': datetime.now().isoformat()
            })
            
            result = self._execute_single_task(task)
            results[task.task_id] = result
            execution_log['task_results'][task.task_id] = result
        
        return results
    
    def _execute_dependency_based(self, workflow: WorkflowPlan, execution_log: Dict) -> Dict:
        """Execute tasks based on dependency graph"""
        results = {}
        completed_tasks = set()
        
        # Create dependency graph
        task_map = {task.task_id: task for task in workflow.tasks}
        
        while len(completed_tasks) < len(workflow.tasks):
            # Find tasks that can be executed (all dependencies completed)
            ready_tasks = []
            for task in workflow.tasks:
                if (task.task_id not in completed_tasks and 
                    all(dep in completed_tasks for dep in task.dependencies)):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # Check for circular dependencies or orphaned tasks
                remaining_tasks = [t.task_id for t in workflow.tasks if t.task_id not in completed_tasks]
                raise Exception(f"Dependency deadlock: remaining tasks {remaining_tasks}")
            
            # Execute ready tasks
            for task in ready_tasks:
                execution_log['coordination_events'].append({
                    'event': 'task_started',
                    'task_id': task.task_id,
                    'timestamp': datetime.now().isoformat(),
                    'dependencies_satisfied': task.dependencies
                })
                
                result = self._execute_single_task(task)
                results[task.task_id] = result
                execution_log['task_results'][task.task_id] = result
                
                if result['status'] == 'completed':
                    completed_tasks.add(task.task_id)
                else:
                    # Task failed - check if it's critical
                    if task.priority == 'high':
                        raise Exception(f"Critical task {task.task_id} failed: {result.get('error', 'Unknown error')}")
                    else:
                        # Non-critical task failed, continue but log it
                        completed_tasks.add(task.task_id)  # Mark as "completed" to unblock dependencies
                        execution_log['coordination_events'].append({
                            'event': 'task_failed_non_critical',
                            'task_id': task.task_id,
                            'timestamp': datetime.now().isoformat()
                        })
        
        return results
    
    def _execute_single_task(self, task: AgentTask) -> Dict:
        """Execute a single agent task"""
        print(f"  🤖 Executing {task.agent_type}: {task.task_description}")
        
        task.status = 'running'
        task.assigned_at = datetime.now().isoformat()
        start_time = datetime.now()
        invocation_id = None

        if self.effectiveness_tracker:
            invocation_id = self.effectiveness_tracker.record_agent_invocation(
                agent_name=task.agent_type,
                task_description=task.task_description,
                context={
                    "task_id": task.task_id,
                    "priority": task.priority,
                    "dependencies": task.dependencies,
                    "expected_output": task.expected_output
                }
            )
        
        try:
            # Simulate agent execution
            # In a real implementation, this would call the actual agent
            result = self._simulate_agent_execution(task)
            
            task.status = 'completed'
            end_time = datetime.now()
            task.completed_at = end_time.isoformat()
            task.output = result
            duration_seconds = (end_time - start_time).total_seconds()

            if self.usage_tracker:
                self.usage_tracker.log_agent_usage(
                    agent_name=task.agent_type,
                    task_type=task.task_description,
                    success=True,
                    duration_seconds=duration_seconds,
                    context={"task_id": task.task_id, "telemetry": "{{ORCHESTRATOR_NAME_LOWER}}_coordinator"}
                )

            if self.effectiveness_tracker and AgentPerformanceRecord:
                performance_record = AgentPerformanceRecord(
                    agent_name=task.agent_type,
                    task_type=task.task_description,
                    domain=task.agent_type,
                    success=True,
                    completion_time=duration_seconds,
                    quality_score=result.get('confidence_score', 0.85),
                    user_satisfaction=result.get('confidence_score', 0.85),
                    resource_usage=0.5,
                    context={
                        "task_id": task.task_id,
                        "artifacts": result.get('artifacts_generated', []),
                        "delegation_id": invocation_id
                    },
                    timestamp=datetime.now().isoformat(),
                    execution_id=invocation_id or f"exec_{datetime.now().timestamp()}"
                )
                self.effectiveness_tracker.record_performance(performance_record)
            
            return {
                'status': 'completed',
                'task_id': task.task_id,
                'agent_type': task.agent_type,
                'output': result,
                'execution_time_minutes': 1  # Simulated
            }
            
        except Exception as e:
            task.status = 'failed'
            task.error = str(e)
            end_time = datetime.now()
            failure_timestamp = end_time.isoformat()

            if self.usage_tracker:
                self.usage_tracker.log_agent_usage(
                    agent_name=task.agent_type,
                    task_type=task.task_description,
                    success=False,
                    duration_seconds=(end_time - start_time).total_seconds(),
                    context={"task_id": task.task_id, "telemetry": "{{ORCHESTRATOR_NAME_LOWER}}_coordinator"}
                )

            if self.effectiveness_tracker:
                self.effectiveness_tracker.mark_invocation_outcome(
                    invocation_id,
                    success=False,
                    metadata={"error": str(e), "task_id": task.task_id}
                )
            
            return {
                'status': 'failed',
                'task_id': task.task_id,
                'agent_type': task.agent_type,
                'error': str(e)
            }
    
    def _simulate_agent_execution(self, task: AgentTask) -> Dict:
        """Simulate agent execution (placeholder for actual agent calls)"""
        # This is a simulation - in real implementation, would call actual agents
        agent_info = self.available_agents.get(task.agent_type, {})
        
        return {
            'agent_type': task.agent_type,
            'task_description': task.task_description,
            'analysis_summary': f"Completed {task.agent_type} analysis for: {task.task_description}",
            'recommendations': [
                f"Primary recommendation from {task.agent_type}",
                f"Secondary suggestion based on {task.task_description}"
            ],
            'confidence_score': 0.85,
            'execution_notes': f"Task executed successfully by {task.agent_type} specialist",
            'artifacts_generated': [
                f"{task.task_id}_analysis.md",
                f"{task.task_id}_recommendations.json"
            ]
        }
    
    def create_smart_workflow(self, goal: str, context: Dict = None) -> WorkflowPlan:
        """Intelligently create workflow based on goal and context"""
        print(f"🧠 Creating smart workflow for: {goal}")
        
        # Analyze goal to determine required agents
        required_agents = self._analyze_goal_requirements(goal, context or {})
        
        # Create optimized task sequence
        tasks = self._create_optimized_tasks(goal, required_agents, context or {})
        
        # Determine best coordination strategy
        strategy = self._determine_coordination_strategy(tasks)
        
        workflow = self.create_workflow(
            description=f"Smart workflow for: {goal}",
            tasks=tasks,
            strategy=strategy
        )
        
        print(f"  📋 Created workflow with {len(tasks)} tasks using {strategy} strategy")
        return workflow
    
    def _analyze_goal_requirements(self, goal: str, context: Dict) -> List[str]:
        """Analyze goal to determine which agents are needed"""
        goal_lower = goal.lower()
        required_agents = []
        
        # Keyword-based agent selection
        if any(word in goal_lower for word in ['security', 'audit', 'threat', 'vulnerability']):
            required_agents.append('security_analyst')
        
        if any(word in goal_lower for word in ['performance', 'optimize', 'speed', 'bottleneck']):
            required_agents.append('performance_optimizer')
        
        if any(word in goal_lower for word in ['review', 'quality', 'code', 'best practices']):
            required_agents.append('code_reviewer')
        
        if any(word in goal_lower for word in ['design', 'architecture', 'scale', 'structure']):
            required_agents.append('system_architect')
        
        if any(word in goal_lower for word in ['debug', 'error', 'issue', 'problem', 'investigate']):
            required_agents.append('debugger')
        
        if any(word in goal_lower for word in ['ui', 'frontend', 'interface', 'accessibility']):
            required_agents.append('frontend_specialist')
        
        # Default to code reviewer if no specific agents identified
        if not required_agents:
            required_agents.append('code_reviewer')
        
        return required_agents
    
    def _create_optimized_tasks(self, goal: str, agents: List[str], context: Dict) -> List[Dict]:
        """Create optimized task sequence for required agents"""
        tasks = []
        
        # Create base analysis tasks
        for i, agent in enumerate(agents):
            task = {
                'agent_type': agent,
                'description': f"{agent.replace('_', ' ').title()}: {goal}",
                'priority': 'high' if i == 0 else 'medium',
                'dependencies': [],
                'expected_output': f'{agent} analysis report'
            }
            tasks.append(task)
        
        # Add dependencies for logical flow
        if len(tasks) > 1:
            # System architect should go first if present
            architect_index = None
            for i, task in enumerate(tasks):
                if task['agent_type'] == 'system_architect':
                    architect_index = i
                    break
            
            if architect_index is not None and architect_index > 0:
                # Move architect to front
                architect_task = tasks.pop(architect_index)
                tasks.insert(0, architect_task)
                
                # Make other tasks depend on architect
                architect_task_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}_task_1"
                for i, task in enumerate(tasks[1:], 2):
                    task['dependencies'] = [architect_task_id]
        
        return tasks
    
    def _determine_coordination_strategy(self, tasks: List[Dict]) -> str:
        """Determine optimal coordination strategy"""
        # If tasks have dependencies, use dependency-based
        if any(task.get('dependencies') for task in tasks):
            return 'dependency_based'
        
        # If multiple independent tasks, use parallel
        if len(tasks) > 1:
            return 'parallel'
        
        # Single task or sequential requirements
        return 'sequential'
    
    def _save_workflow(self, workflow: WorkflowPlan) -> None:
        """Save workflow to persistent storage"""
        try:
            # Load existing workflows
            if self.workflows_db.exists():
                with open(self.workflows_db, 'r') as f:
                    data = json.load(f)
            else:
                data = {'workflows': []}
            
            # Convert workflow to dict for JSON serialization
            workflow_dict = asdict(workflow)
            
            # Update or add workflow
            updated = False
            for i, wf in enumerate(data['workflows']):
                if wf.get('workflow_id') == workflow.workflow_id:
                    data['workflows'][i] = workflow_dict
                    updated = True
                    break
            
            if not updated:
                data['workflows'].append(workflow_dict)
            
            # Save
            with open(self.workflows_db, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving workflow: {e}")
    
    def _save_coordination_history(self, execution_log: Dict) -> None:
        """Save coordination history for learning"""
        try:
            # Load existing history
            if self.coordination_db.exists():
                with open(self.coordination_db, 'r') as f:
                    data = json.load(f)
            else:
                data = {'coordination_history': []}
            
            # Add execution log
            data['coordination_history'].append(execution_log)
            
            # Keep only recent history (last 50 executions)
            data['coordination_history'] = data['coordination_history'][-50:]
            
            # Save
            with open(self.coordination_db, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️ Error saving coordination history: {e}")
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        """Get status of a specific workflow"""
        try:
            if self.workflows_db.exists():
                with open(self.workflows_db, 'r') as f:
                    data = json.load(f)
                
                for workflow in data.get('workflows', []):
                    if workflow.get('workflow_id') == workflow_id:
                        return workflow
        except Exception:
            pass
        return None
    
    def generate_coordination_report(self) -> str:
        """Generate coordination effectiveness report"""
        try:
            # Load coordination history
            if self.coordination_db.exists():
                with open(self.coordination_db, 'r') as f:
                    data = json.load(f)
                history = data.get('coordination_history', [])
            else:
                history = []
            
            # Load workflows
            if self.workflows_db.exists():
                with open(self.workflows_db, 'r') as f:
                    data = json.load(f)
                workflows = data.get('workflows', [])
            else:
                workflows = []
            
            report = f"""# {{ORCHESTRATOR_NAME}} Agent Coordination Report

## Summary
- **Total Workflows Created:** {len(workflows)}
- **Workflows Executed:** {len(history)}
- **Available Specialist Agents:** {len(self.available_agents)}

## Workflow Statistics
"""
            
            if workflows:
                strategies = {}
                statuses = {}
                
                for wf in workflows:
                    strategy = wf.get('coordination_strategy', 'unknown')
                    strategies[strategy] = strategies.get(strategy, 0) + 1
                    
                    status = wf.get('status', 'unknown')
                    statuses[status] = statuses.get(status, 0) + 1
                
                report += f"### Coordination Strategies\n"
                for strategy, count in strategies.items():
                    report += f"- {strategy.replace('_', ' ').title()}: {count}\n"
                
                report += f"\n### Workflow Status\n"
                for status, count in statuses.items():
                    report += f"- {status.title()}: {count}\n"
            
            if history:
                successful = len([h for h in history if h.get('final_status') == 'completed'])
                success_rate = (successful / len(history)) * 100
                
                report += f"""
## Execution Performance
- **Success Rate:** {success_rate:.1f}%
- **Total Executions:** {len(history)}
- **Successful Executions:** {successful}
"""
                
                # Average task count
                total_tasks = sum(len(h.get('task_results', {})) for h in history)
                avg_tasks = total_tasks / len(history) if history else 0
                report += f"- **Average Tasks per Workflow:** {avg_tasks:.1f}\n"
            
            report += f"""
## Available Specialist Agents
"""
            for agent_type, info in self.available_agents.items():
                report += f"### {agent_type.replace('_', ' ').title()}\n"
                report += f"- **Description:** {info['description']}\n"
                report += f"- **Typical Tasks:** {', '.join(info['typical_tasks'])}\n"
                report += f"- **Estimated Time:** {info['estimated_time']} minutes\n\n"
            
            return report
            
        except Exception as e:
            return f"Error generating coordination report: {e}"

def main():
    """Test agent coordination system"""
    coordinator = {{ORCHESTRATOR_NAME}}AgentCoordinator()
    
    print("🎯 {{ORCHESTRATOR_NAME}} Agent Coordination System")
    print("==================================")
    
    # Test smart workflow creation
    workflow = coordinator.create_smart_workflow(
        goal="Optimize Catalyst performance and security",
        context={'priority': 'high', 'scope': 'system_wide'}
    )
    
    print(f"\n📋 Created workflow: {workflow.workflow_id}")
    print(f"   Tasks: {len(workflow.tasks)}")
    print(f"   Strategy: {workflow.coordination_strategy}")
    
    # Execute workflow
    execution_result = coordinator.execute_workflow(workflow)
    print(f"\n✅ Workflow executed: {execution_result['final_status']}")
    
    # Generate report
    report = coordinator.generate_coordination_report()
    print(report)
    
    # Save report
    report_file = coordinator.builder_root / 'registry/{{ORCHESTRATOR_NAME_LOWER}}_coordination_report.md'
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📊 Coordination report saved to: {report_file}")

if __name__ == "__main__":
    main()
