#!/usr/bin/env python3
"""
Learning Effectiveness Validation Framework
Measures and validates learning improvements in Catalyst
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
import sys

# Add global/rag to path
rag_path = Path(__file__).parent.parent / "global" / "rag"
sys.path.append(str(rag_path))

try:
    from knowledge_router import KnowledgeRouter
    from optimized_knowledge_graph import get_optimized_graph
except ImportError:
    KnowledgeRouter = None
    get_optimized_graph = None

logger = logging.getLogger(__name__)

class LearningMetricType(Enum):
    """Types of learning metrics to track"""
    QUERY_ACCURACY = "query_accuracy"
    RESPONSE_QUALITY = "response_quality"  
    KNOWLEDGE_RETENTION = "knowledge_retention"
    TASK_COMPLETION = "task_completion"
    CONTEXT_AWARENESS = "context_awareness"
    PREDICTION_ACCURACY = "prediction_accuracy"

@dataclass
class LearningMetric:
    """Individual learning metric measurement"""
    metric_type: LearningMetricType
    value: float
    timestamp: str
    context: str
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        # Convert enum to string for JSON serialization
        result['metric_type'] = self.metric_type.value
        return result

@dataclass
class ValidationResult:
    """Result of learning validation"""
    overall_score: float
    metrics: List[LearningMetric]
    improvement_over_baseline: float
    recommendations: List[str]
    timestamp: str
    confidence: float = 1.0

class LearningValidator:
    """Validates and measures learning effectiveness"""
    
    def __init__(self):
        self.knowledge_router = KnowledgeRouter() if KnowledgeRouter else None
        self.knowledge_graph = get_optimized_graph() if get_optimized_graph else None
        self.metrics_history_file = Path(__file__).parent.parent / "registry" / "learning_metrics.jsonl"
        self.baseline_file = Path(__file__).parent.parent / "registry" / "learning_baseline.json"
        
        # Ensure registry directory exists
        self.metrics_history_file.parent.mkdir(exist_ok=True)
        
        # Test cases for validation
        self.test_cases = self._load_test_cases()
    
    def _load_test_cases(self) -> List[Dict]:
        """Load test cases for learning validation"""
        return [
            {
                "query": "What is the Catalyst?",
                "expected_topics": ["capsule architecture", "personal system", "{{ORCHESTRATOR_NAME_LOWER}}"],
                "context": "basic_system_knowledge"
            },
            {
                "query": "How does {{ORCHESTRATOR_NAME}} learn from decisions?",
                "expected_topics": ["decision patterns", "learning engine", "mcp memory"],
                "context": "learning_mechanisms"
            },
            {
                "query": "What capsules are currently active?",
                "expected_topics": ["production capsules", "jellyfin", "brandjack"],
                "context": "current_state"
            },
            {
                "query": "How do I optimize knowledge graph performance?",
                "expected_topics": ["chroma integration", "indexed lookups", "vector search"],
                "context": "technical_optimization"
            },
            {
                "query": "What are {{USER_NAME}}'s decision patterns?",
                "expected_topics": ["risk classification", "approval patterns", "governance"],
                "context": "user_behavior"
            }
        ]
    
    def measure_query_accuracy(self, test_cases: List[Dict] = None) -> LearningMetric:
        """Measure accuracy of knowledge queries"""
        test_cases = test_cases or self.test_cases
        
        if not self.knowledge_router:
            return LearningMetric(
                LearningMetricType.QUERY_ACCURACY,
                0.0,
                datetime.utcnow().isoformat(),
                "Knowledge router not available",
                {"error": "missing_dependency"}
            )
        
        try:
            total_score = 0.0
            successful_queries = 0
            
            for test_case in test_cases:
                query = test_case["query"]
                expected_topics = test_case["expected_topics"]
                
                # Execute query
                results = self.knowledge_router.get_knowledge(query, max_results=5)
                
                if results:
                    # Calculate relevance score
                    relevance_score = self._calculate_relevance_score(results, expected_topics)
                    total_score += relevance_score
                    successful_queries += 1
                    
                    logger.debug(f"Query '{query}' scored {relevance_score:.2f}")
            
            accuracy = total_score / len(test_cases) if test_cases else 0.0
            
            return LearningMetric(
                LearningMetricType.QUERY_ACCURACY,
                accuracy,
                datetime.utcnow().isoformat(),
                f"Tested {len(test_cases)} queries",
                {"successful_queries": successful_queries, "total_queries": len(test_cases)}
            )
            
        except Exception as e:
            logger.error(f"Query accuracy measurement failed: {e}")
            return LearningMetric(
                LearningMetricType.QUERY_ACCURACY,
                0.0,
                datetime.utcnow().isoformat(),
                f"Error: {str(e)}",
                {"error": str(e)}
            )
    
    def _calculate_relevance_score(self, results: List, expected_topics: List[str]) -> float:
        """Calculate how well results match expected topics"""
        if not results:
            return 0.0
        
        topic_matches = 0
        total_weight = 0
        
        for i, result in enumerate(results[:3]):  # Top 3 results
            content = result.content.lower()
            weight = 1.0 / (i + 1)  # Decreasing weight for lower results
            
            topic_score = 0
            for topic in expected_topics:
                if topic.lower() in content:
                    topic_score += 1
            
            if topic_score > 0:
                topic_matches += weight * (topic_score / len(expected_topics))
            
            total_weight += weight
        
        return topic_matches / total_weight if total_weight > 0 else 0.0
    
    def measure_knowledge_retention(self) -> LearningMetric:
        """Measure how well knowledge persists over time"""
        try:
            if not self.knowledge_graph:
                return LearningMetric(
                    LearningMetricType.KNOWLEDGE_RETENTION,
                    0.0,
                    datetime.utcnow().isoformat(),
                    "Knowledge graph not available"
                )
            
            # Get performance stats from knowledge graph
            stats = self.knowledge_graph.get_performance_stats()
            
            # Calculate retention score based on:
            # 1. Total entities and relationships
            # 2. Cache hit rate (indicates frequently accessed knowledge)
            # 3. Query success rate
            
            entity_score = min(stats.get("total_entities", 0) / 50.0, 1.0)  # Max score at 50 entities
            relationship_score = min(stats.get("total_relationships", 0) / 100.0, 1.0)  # Max score at 100 relationships
            cache_score = stats.get("cache_hit_rate", 0.0)
            
            retention_score = (entity_score + relationship_score + cache_score) / 3.0
            
            return LearningMetric(
                LearningMetricType.KNOWLEDGE_RETENTION,
                retention_score,
                datetime.utcnow().isoformat(),
                "Knowledge graph performance analysis",
                stats
            )
            
        except Exception as e:
            logger.error(f"Knowledge retention measurement failed: {e}")
            return LearningMetric(
                LearningMetricType.KNOWLEDGE_RETENTION,
                0.0,
                datetime.utcnow().isoformat(),
                f"Error: {str(e)}"
            )
    
    def measure_context_awareness(self) -> LearningMetric:
        """Measure how well system maintains context across interactions"""
        try:
            # Test context-dependent queries
            context_tests = [
                {
                    "context": "We're working on Chroma integration",
                    "query": "How is this integrated with MCP?",
                    "expected_context": ["chroma", "mcp", "integration"]
                },
                {
                    "context": "Builder system needs optimization",
                    "query": "What performance improvements are available?",
                    "expected_context": ["performance", "optimization", "builder"]
                }
            ]
            
            total_score = 0.0
            
            if self.knowledge_router:
                for test in context_tests:
                    context = test["context"]
                    query = test["query"]
                    expected = test["expected_context"]
                    
                    # Query with context
                    results = self.knowledge_router.get_knowledge(query, context=context, max_results=3)
                    
                    # Score based on context relevance
                    context_score = self._calculate_context_score(results, expected, context)
                    total_score += context_score
            
            awareness_score = total_score / len(context_tests) if context_tests else 0.0
            
            return LearningMetric(
                LearningMetricType.CONTEXT_AWARENESS,
                awareness_score,
                datetime.utcnow().isoformat(),
                f"Tested {len(context_tests)} context scenarios",
                {"test_count": len(context_tests)}
            )
            
        except Exception as e:
            logger.error(f"Context awareness measurement failed: {e}")
            return LearningMetric(
                LearningMetricType.CONTEXT_AWARENESS,
                0.0,
                datetime.utcnow().isoformat(),
                f"Error: {str(e)}"
            )
    
    def _calculate_context_score(self, results: List, expected_context: List[str], context: str) -> float:
        """Calculate how well results incorporate context"""
        if not results:
            return 0.0
        
        # Check if results contain context-relevant information
        context_relevance = 0.0
        
        for result in results[:2]:  # Top 2 results
            content = result.content.lower()
            context_lower = context.lower()
            
            # Score based on context keywords present
            context_keywords_found = sum(1 for keyword in expected_context if keyword.lower() in content)
            context_relevance += context_keywords_found / len(expected_context)
            
            # Bonus if original context is referenced
            if any(word in content for word in context_lower.split() if len(word) > 3):
                context_relevance += 0.2
        
        return min(context_relevance / 2.0, 1.0)  # Average over top 2 results, cap at 1.0
    
    def get_baseline_metrics(self) -> Dict[str, float]:
        """Get or create baseline metrics for comparison"""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file, 'r') as f:
                    baseline = json.load(f)
                logger.info("Loaded existing baseline metrics")
                return baseline
            else:
                # Create initial baseline
                logger.info("Creating initial baseline metrics")
                baseline = self._create_initial_baseline()
                with open(self.baseline_file, 'w') as f:
                    json.dump(baseline, f, indent=2)
                return baseline
                
        except Exception as e:
            logger.error(f"Failed to get baseline metrics: {e}")
            return {
                "query_accuracy": 0.5,
                "knowledge_retention": 0.5,
                "context_awareness": 0.5,
                "created_at": datetime.utcnow().isoformat()
            }
    
    def _create_initial_baseline(self) -> Dict[str, float]:
        """Create initial baseline by measuring current performance"""
        baseline_metrics = {}
        
        # Measure current performance as baseline
        accuracy_metric = self.measure_query_accuracy()
        baseline_metrics["query_accuracy"] = accuracy_metric.value
        
        retention_metric = self.measure_knowledge_retention()
        baseline_metrics["knowledge_retention"] = retention_metric.value
        
        context_metric = self.measure_context_awareness()
        baseline_metrics["context_awareness"] = context_metric.value
        
        baseline_metrics.update({
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "description": "Initial baseline measurement"
        })
        
        return baseline_metrics
    
    def validate_learning_effectiveness(self) -> ValidationResult:
        """Comprehensive learning effectiveness validation"""
        try:
            logger.info("Starting learning effectiveness validation")
            
            # Collect current metrics
            current_metrics = []
            
            # Query accuracy
            accuracy_metric = self.measure_query_accuracy()
            current_metrics.append(accuracy_metric)
            
            # Knowledge retention
            retention_metric = self.measure_knowledge_retention()
            current_metrics.append(retention_metric)
            
            # Context awareness
            context_metric = self.measure_context_awareness()
            current_metrics.append(context_metric)
            
            # Calculate overall score
            metric_values = [m.value for m in current_metrics if m.value > 0]
            overall_score = statistics.mean(metric_values) if metric_values else 0.0
            
            # Compare with baseline
            baseline = self.get_baseline_metrics()
            improvements = {}
            
            for metric in current_metrics:
                metric_name = metric.metric_type.value
                baseline_value = baseline.get(metric_name, 0.5)
                improvement = metric.value - baseline_value
                improvements[metric_name] = improvement
            
            avg_improvement = statistics.mean(improvements.values()) if improvements else 0.0
            
            # Generate recommendations
            recommendations = self._generate_recommendations(current_metrics, improvements)
            
            # Save metrics to history
            self._save_metrics_to_history(current_metrics)
            
            validation_result = ValidationResult(
                overall_score=overall_score,
                metrics=current_metrics,
                improvement_over_baseline=avg_improvement,
                recommendations=recommendations,
                timestamp=datetime.utcnow().isoformat(),
                confidence=0.8  # Based on test case coverage
            )
            
            logger.info(f"Learning validation completed. Overall score: {overall_score:.2f}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Learning validation failed: {e}")
            return ValidationResult(
                overall_score=0.0,
                metrics=[],
                improvement_over_baseline=0.0,
                recommendations=[f"Validation failed: {str(e)}"],
                timestamp=datetime.utcnow().isoformat(),
                confidence=0.0
            )
    
    def _generate_recommendations(self, metrics: List[LearningMetric], improvements: Dict[str, float]) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        for metric in metrics:
            metric_name = metric.metric_type.value
            value = metric.value
            improvement = improvements.get(metric_name, 0.0)
            
            if value < 0.6:  # Below acceptable threshold
                if metric_name == "query_accuracy":
                    recommendations.append("Improve knowledge base content quality and query processing")
                elif metric_name == "knowledge_retention":
                    recommendations.append("Increase knowledge graph population and indexing efficiency")
                elif metric_name == "context_awareness":
                    recommendations.append("Enhance context propagation and session memory")
            
            if improvement < 0:  # Declining performance
                recommendations.append(f"Address declining {metric_name} - investigate recent changes")
        
        if not recommendations:
            recommendations.append("Learning systems performing well - continue current approach")
        
        return recommendations
    
    def _save_metrics_to_history(self, metrics: List[LearningMetric]):
        """Save metrics to historical log"""
        try:
            with open(self.metrics_history_file, 'a') as f:
                for metric in metrics:
                    f.write(json.dumps(metric.to_dict()) + '\n')
                    
        except Exception as e:
            logger.error(f"Failed to save metrics history: {e}")
    
    def get_learning_trends(self, days: int = 30) -> Dict[str, List[float]]:
        """Get learning trends over specified time period"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            trends = {}
            
            if not self.metrics_history_file.exists():
                return trends
            
            with open(self.metrics_history_file, 'r') as f:
                for line in f:
                    metric_data = json.loads(line.strip())
                    metric_time = datetime.fromisoformat(metric_data['timestamp'])
                    
                    if metric_time >= cutoff_date:
                        metric_type = metric_data['metric_type']
                        if metric_type not in trends:
                            trends[metric_type] = []
                        trends[metric_type].append(metric_data['value'])
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get learning trends: {e}")
            return {}

# Convenience functions
def validate_learning() -> Dict:
    """Quick function to validate learning effectiveness"""
    validator = LearningValidator()
    result = validator.validate_learning_effectiveness()
    return {
        "overall_score": result.overall_score,
        "improvement": result.improvement_over_baseline,
        "recommendations": result.recommendations,
        "timestamp": result.timestamp
    }

def get_learning_report() -> Dict:
    """Generate comprehensive learning report"""
    validator = LearningValidator()
    validation = validator.validate_learning_effectiveness()
    trends = validator.get_learning_trends()
    
    return {
        "current_performance": validation,
        "trends": trends,
        "generated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Test the learning validator
    logging.basicConfig(level=logging.INFO)
    
    print("Learning Effectiveness Validation Test")
    print("=" * 50)
    
    validator = LearningValidator()
    
    # Run validation
    result = validator.validate_learning_effectiveness()
    
    print(f"Overall Score: {result.overall_score:.2f}")
    print(f"Improvement over baseline: {result.improvement_over_baseline:+.2f}")
    print(f"Confidence: {result.confidence:.2f}")
    
    print("\nMetrics:")
    for metric in result.metrics:
        print(f"  {metric.metric_type.value}: {metric.value:.2f}")
    
    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")
    
    print("\nLearning Validator ready for integration")