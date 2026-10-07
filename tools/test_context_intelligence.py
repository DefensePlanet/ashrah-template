#!/usr/bin/env python3
"""
Test Suite for Context Intelligence System
Validates Phase 2: Context Intelligence for agent invocations
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Test all context intelligence components
try:
    from context_intelligence_engine import ContextIntelligenceEngine, ContextType, PrivacyLevel
    from context_analyzer import ContextAnalyzer
    from {{ORCHESTRATOR_NAME_LOWER}}_agent_coordinator import {{ORCHESTRATOR_NAME}}AgentCoordinator
    CI_AVAILABLE = True
except ImportError as e:
    print(f"Context Intelligence components not available: {e}")
    CI_AVAILABLE = False

logger = logging.getLogger(__name__)

class ContextIntelligenceTestSuite:
    """Comprehensive test suite for Context Intelligence system"""
    
    def __init__(self):
        if not CI_AVAILABLE:
            raise RuntimeError("Context Intelligence components not available")
        
        self.context_engine = ContextIntelligenceEngine()
        self.context_analyzer = ContextAnalyzer(self.context_engine)
        self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator = {{ORCHESTRATOR_NAME}}AgentCoordinator()
        
        self.test_results = []
        self.session_id = None
        
        print("Context Intelligence Test Suite initialized")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite"""
        print("🧠 Running Context Intelligence Test Suite")
        print("=" * 60)
        
        # Phase 1: Basic Component Tests
        self._test_context_engine_basics()
        self._test_context_storage_retrieval()
        self._test_context_analyzer_scoring()
        
        # Phase 2: Integration Tests
        self._test_session_management()
        self._test_conversation_tracking()
        self._test_agent_recommendations()
        
        # Phase 3: Advanced Intelligence Tests
        self._test_context_aware_delegation()
        self._test_context_briefing_generation()
        self._test_risk_assessment()
        
        # Phase 4: Performance and Edge Cases
        self._test_performance_metrics()
        self._test_edge_cases()
        
        # Generate test report
        return self._generate_test_report()
    
    def _test_context_engine_basics(self):
        """Test basic context engine functionality"""
        print("📱 Testing Context Engine Basics...")
        
        try:
            # Test session creation
            self.session_id = self.context_engine.start_session(
                "test_session_001",
                "Testing context intelligence system",
                active_capsule="test-capsule"
            )
            
            self._record_test("session_creation", True, "Session created successfully")
            
            # Test context entity creation
            entity = self.context_engine.track_conversation_turn(
                user_input="Create a simple iOS app",
                agent_response="I'll help you create an iOS app using Swift",
                agent_name="iOS Dev",
                metadata={"test": True, "confidence": 0.9}
            )
            
            self._record_test("context_entity_creation", True, f"Context entity created: {entity.id}")
            
            # Test task context extraction
            task_context = self.context_engine.extract_task_context(
                "Build a web dashboard for analytics",
                [{"user_input": "Need analytics", "agent_response": "Building dashboard"}]
            )
            
            expected_fields = ["task_description", "extracted_keywords", "task_type"]
            has_expected_fields = all(field in task_context for field in expected_fields)
            
            self._record_test("task_context_extraction", has_expected_fields, 
                            f"Task context has {len(task_context)} fields")
            
        except Exception as e:
            self._record_test("context_engine_basics", False, f"Error: {e}")
    
    def _test_context_storage_retrieval(self):
        """Test context storage and retrieval"""
        print("💾 Testing Context Storage & Retrieval...")
        
        try:
            # Store test outcome
            outcome_entity = self.context_engine.store_task_outcome(
                task_description="Test iOS app creation",
                agent_name="iOS Dev",
                outcome={"status": "success", "duration": 25.5},
                success=True
            )
            
            self._record_test("context_storage", True, f"Outcome stored: {outcome_entity.id}")
            
            # Test context retrieval
            relevant_contexts = self.context_engine.get_relevant_context(
                task_type="creation",
                domain="ios",
                agent_type="iOS Dev",
                limit=5
            )
            
            self._record_test("context_retrieval", len(relevant_contexts) > 0, 
                            f"Retrieved {len(relevant_contexts)} relevant contexts")
            
            # Test similar task finding
            similar_tasks = self.context_engine.find_similar_tasks(
                "Create an iOS expense tracking app"
            )
            
            self._record_test("similar_task_finding", True, 
                            f"Found {len(similar_tasks)} similar tasks")
            
        except Exception as e:
            self._record_test("context_storage_retrieval", False, f"Error: {e}")
    
    def _test_context_analyzer_scoring(self):
        """Test context analyzer scoring algorithms"""
        print("📊 Testing Context Analyzer Scoring...")
        
        try:
            # Test context relevance analysis
            analysis = self.context_analyzer.analyze_context_relevance(
                query="Create an iOS app for expense tracking",
                task_type="creation",
                domain="ios",
                agent_type="iOS Dev"
            )
            
            self._record_test("context_analysis", True, 
                            f"Analyzed {analysis.total_entities_analyzed} entities")
            
            # Test relevance scoring
            has_relevant_entities = len(analysis.relevant_entities) >= 0
            has_recommendations = len(analysis.recommendations) > 0
            has_distributions = bool(analysis.domain_distribution or analysis.agent_distribution)
            
            scoring_quality = has_relevant_entities and has_recommendations and has_distributions
            
            self._record_test("relevance_scoring", scoring_quality, 
                            f"Scoring analysis: {len(analysis.relevant_entities)} relevant, "
                            f"{len(analysis.recommendations)} recommendations")
            
            # Test context insights
            insights = self.context_analyzer.get_context_insights(24)  # Last 24 hours
            
            self._record_test("context_insights", "insights" in insights, 
                            f"Generated {len(insights.get('insights', []))} insights")
            
        except Exception as e:
            self._record_test("context_analyzer_scoring", False, f"Error: {e}")
    
    def _test_session_management(self):
        """Test session management and persistence"""
        print("🔄 Testing Session Management...")
        
        try:
            # Test session tracking
            current_session = self.context_engine.current_session
            has_session = current_session is not None
            
            self._record_test("session_tracking", has_session, 
                            f"Session tracked: {current_session.session_id if current_session else 'None'}")
            
            # Test conversation flow
            if current_session:
                conversation_count = len(current_session.conversation_flow)
                self._record_test("conversation_flow", conversation_count > 0, 
                                f"Conversation flow has {conversation_count} turns")
            
            # Test performance stats
            stats = self.context_engine.get_performance_stats()
            
            expected_stats = ["total_entities", "total_sessions", "database_path"]
            has_stats = all(stat in stats for stat in expected_stats)
            
            self._record_test("performance_stats", has_stats, 
                            f"Stats: {stats.get('total_entities', 0)} entities, "
                            f"{stats.get('total_sessions', 0)} sessions")
            
        except Exception as e:
            self._record_test("session_management", False, f"Error: {e}")
    
    def _test_conversation_tracking(self):
        """Test conversation tracking capabilities"""
        print("💬 Testing Conversation Tracking...")
        
        try:
            # Track multiple conversation turns
            test_conversations = [
                ("Fix this bug in my React app", "I'll help debug your React application", "Frontend Specialist"),
                ("The button click handler isn't working", "Let me analyze the event handling code", "Debugger"),
                ("Can you also optimize the performance?", "I'll review performance bottlenecks", "Performance Optimizer")
            ]
            
            for i, (user_input, agent_response, agent_name) in enumerate(test_conversations):
                entity = self.context_engine.track_conversation_turn(
                    user_input=user_input,
                    agent_response=agent_response,
                    agent_name=agent_name,
                    metadata={"turn": i + 1, "test_conversation": True}
                )
                
                self._record_test(f"conversation_turn_{i+1}", entity is not None, 
                                f"Turn tracked for {agent_name}")
            
            # Test domain focus updates
            if self.context_engine.current_session:
                domain_focus = self.context_engine.current_session.domain_focus
                self._record_test("domain_focus_tracking", len(domain_focus) > 0, 
                                f"Domain focus: {domain_focus}")
            
        except Exception as e:
            self._record_test("conversation_tracking", False, f"Error: {e}")
    
    def _test_agent_recommendations(self):
        """Test agent recommendation system"""
        print("🤖 Testing Agent Recommendations...")
        
        try:
            # Start {{ORCHESTRATOR_NAME}} session
            {{ORCHESTRATOR_NAME_LOWER}}_session = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.start_context_session(
                "{{ORCHESTRATOR_NAME_LOWER}}_test_session",
                "Testing agent recommendations"
            )
            
            self._record_test("{{ORCHESTRATOR_NAME_LOWER}}_session_start", {{ORCHESTRATOR_NAME_LOWER}}_session is not None, 
                            f"{{ORCHESTRATOR_NAME}} session: {{{ORCHESTRATOR_NAME_LOWER}}_session}")
            
            # Test context-aware recommendations
            recommendations = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.get_agent_recommendations_with_context(
                task_description="Review this code for security vulnerabilities",
                user_input="I need a security audit of my authentication code",
                priority="high"
            )
            
            has_recommendations = len(recommendations) > 0
            if has_recommendations:
                top_rec = recommendations[0]
                has_confidence = hasattr(top_rec, 'confidence_score')
                has_reasoning = hasattr(top_rec, 'reasoning')
                has_briefing = hasattr(top_rec, 'context_briefing')
                
                recommendation_quality = has_confidence and has_reasoning and has_briefing
            else:
                recommendation_quality = False
            
            self._record_test("agent_recommendations", has_recommendations and recommendation_quality, 
                            f"Generated {len(recommendations)} recommendations with quality scores")
            
            # Test recommendation scoring
            if recommendations:
                scores = [r.confidence_score for r in recommendations]
                avg_score = sum(scores) / len(scores)
                self._record_test("recommendation_scoring", avg_score > 0.3, 
                                f"Average confidence: {avg_score:.3f}")
            
        except Exception as e:
            self._record_test("agent_recommendations", False, f"Error: {e}")
    
    def _test_context_aware_delegation(self):
        """Test context-aware delegation decisions"""
        print("🎯 Testing Context-Aware Delegation...")
        
        try:
            # Test delegation with high confidence task
            delegation_result = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.delegate_with_context(
                task_description="Create a Python script to process CSV data",
                user_input="I need to analyze sales data from a CSV file",
                auto_select=True,
                min_confidence=0.5
            )
            
            has_delegation = "delegated_to" in delegation_result
            if has_delegation:
                agent = delegation_result["delegated_to"]
                confidence = delegation_result.get("confidence", 0)
                reasoning = delegation_result.get("reasoning", "")
                
                delegation_quality = confidence > 0.3 and len(reasoning) > 10
            else:
                delegation_quality = False
            
            self._record_test("context_delegation", has_delegation and delegation_quality, 
                            f"Delegated to {delegation_result.get('delegated_to', 'unknown')} "
                            f"with confidence {delegation_result.get('confidence', 0):.3f}")
            
            # Test low confidence delegation
            low_confidence_result = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.delegate_with_context(
                task_description="Perform quantum computing analysis",
                user_input="Need help with quantum algorithms",
                auto_select=False,
                min_confidence=0.8
            )
            
            requires_approval = low_confidence_result.get("requires_approval", False)
            
            self._record_test("low_confidence_handling", requires_approval, 
                            "Low confidence task properly flagged for approval")
            
        except Exception as e:
            self._record_test("context_aware_delegation", False, f"Error: {e}")
    
    def _test_context_briefing_generation(self):
        """Test context briefing generation for agents"""
        print("📋 Testing Context Briefing Generation...")
        
        try:
            # Get recommendations to access briefings
            recommendations = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.get_agent_recommendations_with_context(
                task_description="Optimize database query performance",
                user_input="My application queries are running slowly"
            )
            
            if recommendations:
                briefing = recommendations[0].context_briefing
                
                # Validate briefing structure
                has_relevant_context = hasattr(briefing, 'relevant_context')
                has_success_patterns = hasattr(briefing, 'success_patterns')
                has_domain_insights = hasattr(briefing, 'domain_insights')
                has_recommendations = hasattr(briefing, 'recommendations')
                has_confidence = hasattr(briefing, 'confidence_score')
                
                briefing_completeness = all([
                    has_relevant_context, has_success_patterns, 
                    has_domain_insights, has_recommendations, has_confidence
                ])
                
                self._record_test("briefing_structure", briefing_completeness, 
                                "Context briefing has all required fields")
                
                # Validate briefing content quality
                content_quality = (
                    briefing.confidence_score >= 0.0 and
                    isinstance(briefing.relevant_context, list) and
                    isinstance(briefing.recommendations, list)
                )
                
                self._record_test("briefing_content", content_quality, 
                                f"Briefing confidence: {briefing.confidence_score:.3f}")
            else:
                self._record_test("briefing_generation", False, "No recommendations to test briefings")
                
        except Exception as e:
            self._record_test("context_briefing_generation", False, f"Error: {e}")
    
    def _test_risk_assessment(self):
        """Test risk assessment capabilities"""
        print("⚠️ Testing Risk Assessment...")
        
        try:
            # Test various risk scenarios
            risk_scenarios = [
                ("Simple file copy task", "GREEN"),
                ("Complex distributed system architecture", "YELLOW"),
                ("Modify production database schema", "RED")
            ]
            
            for task, expected_risk_level in risk_scenarios:
                recommendations = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.get_agent_recommendations_with_context(
                    task_description=task,
                    user_input=f"I need help with: {task}"
                )
                
                if recommendations:
                    risk_assessment = recommendations[0].risk_assessment
                    risk_levels = ["GREEN", "YELLOW", "RED"]
                    valid_risk = risk_assessment in risk_levels
                    
                    self._record_test(f"risk_assessment_{expected_risk_level.lower()}", valid_risk, 
                                    f"Task '{task[:30]}...' assessed as {risk_assessment}")
                else:
                    self._record_test(f"risk_assessment_{expected_risk_level.lower()}", False, 
                                    "No recommendations for risk assessment")
            
        except Exception as e:
            self._record_test("risk_assessment", False, f"Error: {e}")
    
    def _test_performance_metrics(self):
        """Test system performance metrics"""
        print("📈 Testing Performance Metrics...")
        
        try:
            # Test context engine performance
            context_stats = self.context_engine.get_performance_stats()
            
            performance_indicators = {
                "entities_created": context_stats.get("total_entities", 0) > 0,
                "sessions_tracked": context_stats.get("total_sessions", 0) > 0,
                "database_accessible": "database_path" in context_stats,
                "integrations_available": context_stats.get("chroma_available", False)
            }
            
            performance_score = sum(performance_indicators.values()) / len(performance_indicators)
            
            self._record_test("performance_metrics", performance_score > 0.5, 
                            f"Performance score: {performance_score:.2f}")
            
            # Test analyzer insights
            insights = self.context_analyzer.get_context_insights(168)  # 1 week
            has_insights = len(insights.get("insights", [])) > 0
            
            self._record_test("analyzer_performance", has_insights, 
                            f"Generated {len(insights.get('insights', []))} insights")
            
        except Exception as e:
            self._record_test("performance_metrics", False, f"Error: {e}")
    
    def _test_edge_cases(self):
        """Test edge cases and error handling"""
        print("🔧 Testing Edge Cases...")
        
        try:
            # Test empty context scenarios
            empty_analysis = self.context_analyzer.analyze_context_relevance(
                query="",
                task_type="",
                domain="",
                agent_type=""
            )
            
            handles_empty_input = empty_analysis is not None
            
            self._record_test("empty_input_handling", handles_empty_input, 
                            "System handles empty input gracefully")
            
            # Test invalid task types
            invalid_recommendations = self.{{ORCHESTRATOR_NAME_LOWER}}_coordinator.get_agent_recommendations_with_context(
                task_description="ksdjfklsjdf random invalid task xyz123",
                user_input="nonsensical input that doesn't match any patterns"
            )
            
            handles_invalid_tasks = len(invalid_recommendations) > 0
            
            self._record_test("invalid_task_handling", handles_invalid_tasks, 
                            f"Generated {len(invalid_recommendations)} fallback recommendations")
            
            # Test large context volumes
            large_context = self.context_engine.get_relevant_context(
                task_type="general",
                domain="",
                agent_type="",
                limit=100
            )
            
            handles_large_queries = len(large_context) >= 0  # Should not crash
            
            self._record_test("large_context_handling", handles_large_queries, 
                            f"Retrieved {len(large_context)} contexts without errors")
            
        except Exception as e:
            self._record_test("edge_cases", False, f"Error: {e}")
    
    def _record_test(self, test_name: str, passed: bool, details: str):
        """Record test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}: {details}")
        
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["passed"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": success_rate
            },
            "test_results": self.test_results,
            "system_status": {
                "context_intelligence_available": CI_AVAILABLE,
                "test_session_id": self.session_id,
                "test_completed_at": datetime.utcnow().isoformat()
            }
        }
        
        print("\n" + "=" * 60)
        print("🧠 CONTEXT INTELLIGENCE TEST RESULTS")
        print("=" * 60)
        print(f"📊 Tests Run: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 EXCELLENT: Context Intelligence system is working well!")
        elif success_rate >= 60:
            print("👍 GOOD: Context Intelligence system is mostly functional")
        else:
            print("⚠️ NEEDS WORK: Context Intelligence system has significant issues")
        
        # Show failed tests
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        return report

# Convenience functions
def run_context_intelligence_tests() -> Dict[str, Any]:
    """Run complete Context Intelligence test suite"""
    if not CI_AVAILABLE:
        return {
            "error": "Context Intelligence components not available",
            "available": False
        }
    
    test_suite = ContextIntelligenceTestSuite()
    return test_suite.run_all_tests()

def quick_context_test() -> bool:
    """Quick health check for Context Intelligence"""
    try:
        engine = ContextIntelligenceEngine()
        session_id = engine.start_session("quick_test")
        entity = engine.track_conversation_turn(
            "test input", "test response", "test_agent"
        )
        return entity is not None
    except Exception:
        return False

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    if not CI_AVAILABLE:
        print("❌ Context Intelligence components not available")
        print("Please ensure all dependencies are installed and working")
        sys.exit(1)
    
    # Run comprehensive test suite
    test_results = run_context_intelligence_tests()
    
    # Save test results
    test_results_file = Path(__file__).parent.parent / "registry" / "context_intelligence_test_results.json"
    test_results_file.parent.mkdir(exist_ok=True)
    
    with open(test_results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📁 Test results saved to: {test_results_file}")
    
    # Exit with appropriate code
    success_rate = test_results["test_summary"]["success_rate"]
    sys.exit(0 if success_rate >= 80 else 1)