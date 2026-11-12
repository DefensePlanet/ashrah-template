#!/usr/bin/env python3
"""
Context Analyzer for Catalyst
Advanced context analysis and relevance scoring
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import sqlite3
from pathlib import Path
import sys

# Add context intelligence engine
from context_intelligence_engine import (
    ContextEntity, ContextType, PrivacyLevel, ContextIntelligenceEngine
)

# Add global/rag to path
rag_path = Path(__file__).parent.parent / "global" / "rag"
sys.path.append(str(rag_path))

try:
    from chroma_integration import ChromaIntegration
    from knowledge_router import KnowledgeRouter
except ImportError:
    ChromaIntegration = None
    KnowledgeRouter = None

logger = logging.getLogger(__name__)

@dataclass
class ContextRelevanceScore:
    """Context relevance scoring with breakdown"""
    entity_id: str
    overall_score: float
    semantic_similarity: float
    temporal_relevance: float
    agent_alignment: float
    domain_relevance: float
    task_type_match: float
    success_history: float
    confidence: float
    explanation: str

@dataclass
class ContextAnalysisResult:
    """Result of context analysis"""
    query: str
    total_entities_analyzed: int
    relevant_entities: List[ContextRelevanceScore]
    domain_distribution: Dict[str, int]
    agent_distribution: Dict[str, int]
    temporal_distribution: Dict[str, int]
    recommendations: List[str]
    analysis_metadata: Dict[str, Any]

class ContextAnalyzer:
    """Advanced context analysis and scoring system"""
    
    def __init__(self, context_engine: ContextIntelligenceEngine = None):
        self.context_engine = context_engine or ContextIntelligenceEngine()
        self.chroma_integration = ChromaIntegration() if ChromaIntegration else None
        self.knowledge_router = KnowledgeRouter() if KnowledgeRouter else None
        
        # Analysis configuration
        self.config = {
            "semantic_weight": 0.3,
            "temporal_weight": 0.2,
            "agent_weight": 0.15,
            "domain_weight": 0.15,
            "task_type_weight": 0.1,
            "success_weight": 0.1,
            "min_relevance_threshold": 0.1,
            "temporal_decay_hours": 168,  # 1 week
            "success_boost_factor": 1.2
        }
        
        logger.info("Context Analyzer initialized")
    
    def analyze_context_relevance(self, query: str, task_type: str = "", 
                                 domain: str = "", agent_type: str = "",
                                 limit: int = 20) -> ContextAnalysisResult:
        """Comprehensive context relevance analysis"""
        try:
            logger.info(f"Analyzing context relevance for query: {query[:50]}...")
            
            # Get candidate context entities
            candidates = self.context_engine.get_relevant_context(
                task_type=task_type,
                domain=domain,
                agent_type=agent_type,
                limit=limit * 2  # Get more candidates for filtering
            )
            
            if not candidates:
                return ContextAnalysisResult(
                    query=query,
                    total_entities_analyzed=0,
                    relevant_entities=[],
                    domain_distribution={},
                    agent_distribution={},
                    temporal_distribution={},
                    recommendations=["No historical context available - building fresh knowledge base"],
                    analysis_metadata={"status": "no_candidates"}
                )
            
            # Score each candidate
            relevance_scores = []
            for entity in candidates:
                score = self._calculate_relevance_score(entity, query, task_type, domain, agent_type)
                if score.overall_score >= self.config["min_relevance_threshold"]:
                    relevance_scores.append(score)
            
            # Sort by relevance
            relevance_scores.sort(key=lambda x: x.overall_score, reverse=True)
            relevant_entities = relevance_scores[:limit]
            
            # Generate analysis distributions
            domain_dist = self._calculate_domain_distribution(candidates)
            agent_dist = self._calculate_agent_distribution(candidates)
            temporal_dist = self._calculate_temporal_distribution(candidates)
            
            # Generate recommendations
            recommendations = self._generate_context_recommendations(
                relevant_entities, domain_dist, agent_dist, temporal_dist
            )
            
            # Analysis metadata
            metadata = {
                "candidates_analyzed": len(candidates),
                "entities_above_threshold": len(relevance_scores),
                "avg_relevance_score": sum(s.overall_score for s in relevant_entities) / len(relevant_entities) if relevant_entities else 0.0,
                "analysis_time": datetime.utcnow().isoformat(),
                "config_used": self.config.copy()
            }
            
            result = ContextAnalysisResult(
                query=query,
                total_entities_analyzed=len(candidates),
                relevant_entities=relevant_entities,
                domain_distribution=domain_dist,
                agent_distribution=agent_dist,
                temporal_distribution=temporal_dist,
                recommendations=recommendations,
                analysis_metadata=metadata
            )
            
            logger.info(f"Context analysis complete: {len(relevant_entities)} relevant entities found")
            return result
            
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            return ContextAnalysisResult(
                query=query,
                total_entities_analyzed=0,
                relevant_entities=[],
                domain_distribution={},
                agent_distribution={},
                temporal_distribution={},
                recommendations=[f"Analysis failed: {str(e)}"],
                analysis_metadata={"error": str(e)}
            )
    
    def _calculate_relevance_score(self, entity: ContextEntity, query: str, 
                                  task_type: str, domain: str, agent_type: str) -> ContextRelevanceScore:
        """Calculate comprehensive relevance score for a context entity"""
        
        # 1. Semantic similarity
        semantic_score = self._calculate_semantic_similarity(entity, query)
        
        # 2. Temporal relevance
        temporal_score = self._calculate_temporal_relevance(entity)
        
        # 3. Agent alignment
        agent_score = self._calculate_agent_alignment(entity, agent_type)
        
        # 4. Domain relevance
        domain_score = self._calculate_domain_relevance(entity, domain)
        
        # 5. Task type match
        task_score = self._calculate_task_type_match(entity, task_type)
        
        # 6. Success history
        success_score = self._calculate_success_history(entity)
        
        # Calculate weighted overall score
        overall_score = (
            semantic_score * self.config["semantic_weight"] +
            temporal_score * self.config["temporal_weight"] +
            agent_score * self.config["agent_weight"] +
            domain_score * self.config["domain_weight"] +
            task_score * self.config["task_type_weight"] +
            success_score * self.config["success_weight"]
        )
        
        # Calculate confidence based on data availability
        confidence = self._calculate_scoring_confidence(
            entity, semantic_score, temporal_score, agent_score, domain_score, task_score, success_score
        )
        
        # Generate explanation
        explanation = self._generate_score_explanation(
            semantic_score, temporal_score, agent_score, domain_score, task_score, success_score
        )
        
        return ContextRelevanceScore(
            entity_id=entity.id,
            overall_score=overall_score,
            semantic_similarity=semantic_score,
            temporal_relevance=temporal_score,
            agent_alignment=agent_score,
            domain_relevance=domain_score,
            task_type_match=task_score,
            success_history=success_score,
            confidence=confidence,
            explanation=explanation
        )
    
    def _calculate_semantic_similarity(self, entity: ContextEntity, query: str) -> float:
        """Calculate semantic similarity between entity and query"""
        try:
            if not self.chroma_integration:
                # Fallback to keyword matching
                return self._keyword_similarity(entity, query)
            
            # Use Chroma for semantic similarity
            entity_text = json.dumps(entity.content)
            
            # Query Chroma for similar content
            similar_docs = self.chroma_integration.query_documents(query, n_results=10)
            
            # Check if this entity's content appears in similar results
            for doc in similar_docs:
                if entity.id in doc.get("metadata", {}).get("entity_id", ""):
                    # Higher score for closer matches (lower distance)
                    distance = doc.get("distance", 1.0)
                    return max(0.0, 1.0 - distance)
            
            # If not found in top results, use keyword fallback
            return self._keyword_similarity(entity, query) * 0.5
            
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            return self._keyword_similarity(entity, query)
    
    def _keyword_similarity(self, entity: ContextEntity, query: str) -> float:
        """Fallback keyword-based similarity"""
        entity_text = json.dumps(entity.content).lower()
        query_words = set(query.lower().split())
        
        if not query_words:
            return 0.0
        
        matches = sum(1 for word in query_words if word in entity_text)
        return matches / len(query_words)
    
    def _calculate_temporal_relevance(self, entity: ContextEntity) -> float:
        """Calculate temporal relevance with decay"""
        try:
            created_time = datetime.fromisoformat(entity.created_at)
            current_time = datetime.utcnow()
            hours_old = (current_time - created_time).total_seconds() / 3600
            
            # Exponential decay
            decay_rate = math.log(0.5) / self.config["temporal_decay_hours"]
            temporal_score = math.exp(decay_rate * hours_old)
            
            return max(0.0, min(1.0, temporal_score))
            
        except Exception as e:
            logger.warning(f"Temporal relevance calculation failed: {e}")
            return 0.5  # Default middle score
    
    def _calculate_agent_alignment(self, entity: ContextEntity, agent_type: str) -> float:
        """Calculate agent alignment score"""
        if not agent_type or not entity.source_agent:
            return 0.5  # Neutral score
        
        if entity.source_agent.lower() == agent_type.lower():
            return 1.0  # Perfect match
        
        # Check for related agents (e.g., iOS Dev and Xcode Agent)
        agent_relationships = {
            "ios dev": ["xcode", "swift", "apple"],
            "frontend specialist": ["web", "ui", "ux"],
            "automation specialist": ["n8n", "workflow", "process"],
            "system architect": ["design", "architecture", "planning"]
        }
        
        agent_lower = agent_type.lower()
        source_lower = entity.source_agent.lower()
        
        for main_agent, related in agent_relationships.items():
            if main_agent in agent_lower:
                if any(rel in source_lower for rel in related):
                    return 0.7  # Related agent
        
        return 0.2  # Different agent family
    
    def _calculate_domain_relevance(self, entity: ContextEntity, domain: str) -> float:
        """Calculate domain relevance score"""
        if not domain:
            return 0.5  # Neutral score
        
        entity_text = json.dumps(entity.content).lower()
        domain_lower = domain.lower()
        
        # Direct domain match
        if domain_lower in entity_text:
            return 1.0
        
        # Related domain keywords
        domain_keywords = {
            "ios": ["swift", "xcode", "apple", "iphone", "ipad", "app store"],
            "web": ["html", "css", "javascript", "react", "frontend", "browser"],
            "automation": ["workflow", "n8n", "process", "schedule", "trigger"],
            "data": ["csv", "json", "database", "analytics", "processing"],
            "security": ["auth", "permission", "encrypt", "vulnerability", "compliance"]
        }
        
        if domain_lower in domain_keywords:
            keywords = domain_keywords[domain_lower]
            matches = sum(1 for keyword in keywords if keyword in entity_text)
            return min(1.0, matches / len(keywords) * 2)  # Scale up for partial matches
        
        return 0.3  # Default low relevance
    
    def _calculate_task_type_match(self, entity: ContextEntity, task_type: str) -> float:
        """Calculate task type match score"""
        if not task_type:
            return 0.5  # Neutral score
        
        entity_text = json.dumps(entity.content).lower()
        task_lower = task_type.lower()
        
        # Direct task type match
        if task_lower in entity_text:
            return 1.0
        
        # Task type synonyms
        task_synonyms = {
            "creation": ["create", "build", "develop", "implement", "new", "generate"],
            "debugging": ["fix", "debug", "repair", "solve", "error", "issue"],
            "analysis": ["analyze", "review", "check", "audit", "examine", "assess"],
            "optimization": ["optimize", "improve", "enhance", "speed", "performance"],
            "deployment": ["deploy", "setup", "configure", "install", "publish"]
        }
        
        if task_lower in task_synonyms:
            synonyms = task_synonyms[task_lower]
            matches = sum(1 for synonym in synonyms if synonym in entity_text)
            return min(1.0, matches / len(synonyms) * 2)
        
        return 0.3  # Default low relevance
    
    def _calculate_success_history(self, entity: ContextEntity) -> float:
        """Calculate success history score"""
        try:
            # Check if this is an outcome entity
            if entity.type == ContextType.OUTCOME:
                success = entity.content.get("success", False)
                if success:
                    return 1.0 * self.config["success_boost_factor"]
                else:
                    return 0.3  # Failed outcomes still have learning value
            
            # For other entity types, check related outcome entities
            # This would require relationship mapping (future enhancement)
            return 0.5  # Neutral score for non-outcome entities
            
        except Exception as e:
            logger.warning(f"Success history calculation failed: {e}")
            return 0.5
    
    def _calculate_scoring_confidence(self, entity: ContextEntity, *scores) -> float:
        """Calculate confidence in the scoring"""
        confidence_factors = []
        
        # Data completeness
        if entity.content:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.2)
        
        # Agent source availability
        if entity.source_agent:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        # Temporal freshness
        try:
            created_time = datetime.fromisoformat(entity.created_at)
            hours_old = (datetime.utcnow() - created_time).total_seconds() / 3600
            if hours_old < 24:
                confidence_factors.append(0.9)
            elif hours_old < 168:  # 1 week
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
        except:
            confidence_factors.append(0.5)
        
        # Score distribution (avoid all scores being similar)
        score_variance = sum((s - 0.5) ** 2 for s in scores) / len(scores)
        if score_variance > 0.1:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.6)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _generate_score_explanation(self, semantic: float, temporal: float, 
                                   agent: float, domain: float, task: float, success: float) -> str:
        """Generate human-readable score explanation"""
        explanations = []
        
        if semantic > 0.7:
            explanations.append("High semantic similarity")
        elif semantic > 0.4:
            explanations.append("Moderate semantic similarity")
        else:
            explanations.append("Low semantic similarity")
        
        if temporal > 0.8:
            explanations.append("very recent")
        elif temporal > 0.5:
            explanations.append("reasonably recent")
        else:
            explanations.append("older context")
        
        if agent > 0.8:
            explanations.append("same agent expertise")
        elif agent > 0.5:
            explanations.append("related agent expertise")
        
        if domain > 0.7:
            explanations.append("strong domain match")
        elif domain > 0.4:
            explanations.append("moderate domain relevance")
        
        if task > 0.7:
            explanations.append("similar task type")
        
        if success > 0.8:
            explanations.append("successful outcome history")
        
        return ", ".join(explanations) if explanations else "general relevance"
    
    def _calculate_domain_distribution(self, entities: List[ContextEntity]) -> Dict[str, int]:
        """Calculate domain distribution in entities"""
        domains = defaultdict(int)
        
        for entity in entities:
            entity_text = json.dumps(entity.content).lower()
            
            # Check for domain indicators
            if any(word in entity_text for word in ["ios", "swift", "xcode"]):
                domains["ios"] += 1
            if any(word in entity_text for word in ["web", "html", "javascript"]):
                domains["web"] += 1
            if any(word in entity_text for word in ["automation", "workflow", "n8n"]):
                domains["automation"] += 1
            if any(word in entity_text for word in ["data", "analysis", "csv"]):
                domains["data"] += 1
            if any(word in entity_text for word in ["security", "auth", "encrypt"]):
                domains["security"] += 1
        
        return dict(domains)
    
    def _calculate_agent_distribution(self, entities: List[ContextEntity]) -> Dict[str, int]:
        """Calculate agent distribution in entities"""
        agents = defaultdict(int)
        
        for entity in entities:
            if entity.source_agent:
                agents[entity.source_agent] += 1
            else:
                agents["unknown"] += 1
        
        return dict(agents)
    
    def _calculate_temporal_distribution(self, entities: List[ContextEntity]) -> Dict[str, int]:
        """Calculate temporal distribution in entities"""
        temporal = defaultdict(int)
        current_time = datetime.utcnow()
        
        for entity in entities:
            try:
                created_time = datetime.fromisoformat(entity.created_at)
                hours_old = (current_time - created_time).total_seconds() / 3600
                
                if hours_old < 24:
                    temporal["last_24h"] += 1
                elif hours_old < 168:  # 1 week
                    temporal["last_week"] += 1
                elif hours_old < 720:  # 1 month
                    temporal["last_month"] += 1
                else:
                    temporal["older"] += 1
            except:
                temporal["unknown"] += 1
        
        return dict(temporal)
    
    def _generate_context_recommendations(self, relevant_entities: List[ContextRelevanceScore],
                                        domain_dist: Dict[str, int], agent_dist: Dict[str, int],
                                        temporal_dist: Dict[str, int]) -> List[str]:
        """Generate actionable context recommendations"""
        recommendations = []
        
        if not relevant_entities:
            recommendations.append("No relevant historical context - consider this a learning opportunity")
            return recommendations
        
        # Analyze top entities
        top_score = relevant_entities[0].overall_score if relevant_entities else 0
        avg_score = sum(e.overall_score for e in relevant_entities) / len(relevant_entities)
        
        if top_score > 0.8:
            recommendations.append("Strong historical context available - leverage past successful patterns")
        elif top_score > 0.5:
            recommendations.append("Moderate context available - consider adapting previous approaches")
        else:
            recommendations.append("Limited context available - proceed with caution and document learnings")
        
        # Domain analysis
        if domain_dist:
            dominant_domain = max(domain_dist.items(), key=lambda x: x[1])
            if dominant_domain[1] >= 3:
                recommendations.append(f"Strong {dominant_domain[0]} domain experience available")
        
        # Agent analysis
        if agent_dist:
            experienced_agents = [agent for agent, count in agent_dist.items() if count >= 2]
            if experienced_agents:
                recommendations.append(f"Consider involving experienced agents: {', '.join(experienced_agents[:3])}")
        
        # Temporal analysis
        if temporal_dist.get("last_24h", 0) >= 3:
            recommendations.append("High recent activity - context is very current")
        elif temporal_dist.get("older", 0) > temporal_dist.get("last_week", 0):
            recommendations.append("Mostly older context - verify current relevance")
        
        # Confidence analysis
        high_confidence_count = sum(1 for e in relevant_entities if e.confidence > 0.8)
        if high_confidence_count < len(relevant_entities) * 0.3:
            recommendations.append("Low confidence in context scoring - proceed carefully")
        
        return recommendations

    def get_context_insights(self, time_period_hours: int = 168) -> Dict[str, Any]:
        """Get insights about context patterns over time period"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_period_hours)
            
            # Get recent entities
            recent_entities = []
            with sqlite3.connect(self.context_engine.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM context_entities 
                    WHERE created_at > ? 
                    ORDER BY created_at DESC
                """, (cutoff_time.isoformat(),))
                
                rows = cursor.fetchall()
                for row in rows:
                    entity_data = {
                        'id': row[0],
                        'type': row[1],
                        'content': json.loads(row[2]),
                        'relevance_score': row[3],
                        'created_at': row[4],
                        'last_accessed': row[5],
                        'decay_factor': row[6],
                        'privacy_level': row[7],
                        'source_agent': row[8],
                        'related_entities': json.loads(row[9]) if row[9] else [],
                    }
                    recent_entities.append(ContextEntity.from_dict(entity_data))
            
            if not recent_entities:
                return {"insights": ["No recent context data available"]}
            
            # Generate insights
            insights = []
            
            # Activity patterns
            agent_activity = Counter(e.source_agent for e in recent_entities if e.source_agent)
            if agent_activity:
                most_active = agent_activity.most_common(1)[0]
                insights.append(f"Most active agent: {most_active[0]} ({most_active[1]} interactions)")
            
            # Domain trends
            domain_trends = self._calculate_domain_distribution(recent_entities)
            if domain_trends:
                trending_domain = max(domain_trends.items(), key=lambda x: x[1])
                insights.append(f"Trending domain: {trending_domain[0]} ({trending_domain[1]} contexts)")
            
            # Context type breakdown
            type_breakdown = Counter(e.type.value for e in recent_entities)
            insights.append(f"Context types: {dict(type_breakdown)}")
            
            # Success rate for outcomes
            outcomes = [e for e in recent_entities if e.type == ContextType.OUTCOME]
            if outcomes:
                successful = sum(1 for e in outcomes if e.content.get("success", False))
                success_rate = successful / len(outcomes)
                insights.append(f"Recent success rate: {success_rate:.1%} ({successful}/{len(outcomes)})")
            
            return {
                "time_period_hours": time_period_hours,
                "total_contexts": len(recent_entities),
                "insights": insights,
                "domain_distribution": domain_trends,
                "agent_activity": dict(agent_activity),
                "context_types": dict(type_breakdown)
            }
            
        except Exception as e:
            logger.error(f"Failed to get context insights: {e}")
            return {"error": str(e)}

# Convenience functions
def analyze_query_context(query: str, task_type: str = "", domain: str = "", 
                         agent_type: str = "") -> Dict[str, Any]:
    """Quick context analysis for a query"""
    analyzer = ContextAnalyzer()
    result = analyzer.analyze_context_relevance(query, task_type, domain, agent_type)
    
    return {
        "relevant_count": len(result.relevant_entities),
        "top_scores": [e.overall_score for e in result.relevant_entities[:3]],
        "recommendations": result.recommendations,
        "domains": result.domain_distribution,
        "agents": result.agent_distribution
    }

def get_recent_context_insights(hours: int = 24) -> Dict[str, Any]:
    """Get insights about recent context patterns"""
    analyzer = ContextAnalyzer()
    return analyzer.get_context_insights(hours)

if __name__ == "__main__":
    # Test the context analyzer
    logging.basicConfig(level=logging.INFO)
    
    print("Context Analyzer Test")
    print("=" * 50)
    
    analyzer = ContextAnalyzer()
    
    # Test context analysis
    result = analyzer.analyze_context_relevance(
        query="Create an iOS app for expense tracking",
        task_type="creation",
        domain="ios",
        agent_type="iOS Dev"
    )
    
    print(f"✓ Analyzed {result.total_entities_analyzed} entities")
    print(f"✓ Found {len(result.relevant_entities)} relevant entities")
    
    if result.relevant_entities:
        top_entity = result.relevant_entities[0]
        print(f"✓ Top relevance score: {top_entity.overall_score:.3f}")
        print(f"✓ Explanation: {top_entity.explanation}")
    
    print(f"✓ Recommendations: {len(result.recommendations)}")
    for rec in result.recommendations[:2]:
        print(f"  - {rec}")
    
    # Test insights
    insights = analyzer.get_context_insights(168)  # 1 week
    print(f"✓ Context insights: {len(insights.get('insights', []))} insights generated")
    
    print("\nContext Analyzer ready for integration")