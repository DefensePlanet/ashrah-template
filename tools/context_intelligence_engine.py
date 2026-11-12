#!/usr/bin/env python3
"""
Context Intelligence Engine for Catalyst
Provides contextual awareness for enhanced agent coordination
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import hashlib
import sys

# Add global/rag to path for existing integrations
rag_path = Path(__file__).parent.parent / "global" / "rag"
sys.path.append(str(rag_path))

try:
    from chroma_integration import ChromaIntegration
    from knowledge_router import KnowledgeRouter
except ImportError:
    ChromaIntegration = None
    KnowledgeRouter = None

logger = logging.getLogger(__name__)

class ContextType(Enum):
    """Types of context entities"""
    SESSION = "session"
    TASK = "task"
    DOMAIN = "domain"
    HISTORICAL = "historical"
    AGENT_INTERACTION = "agent_interaction"
    OUTCOME = "outcome"

class PrivacyLevel(Enum):
    """Privacy levels for context data"""
    PUBLIC = "public"
    INTERNAL = "internal"
    PRIVATE = "private"
    SECRET = "secret"

class RelationType(Enum):
    """Types of relationships between context entities"""
    SEQUENTIAL = "sequential"
    CAUSAL = "causal"
    SIMILAR = "similar"
    CONTRADICTS = "contradicts"
    ENHANCES = "enhances"
    DEPENDS_ON = "depends_on"

@dataclass
class ContextEntity:
    """Core context entity with metadata and relationships"""
    id: str
    type: ContextType
    content: Dict[str, Any]
    relevance_score: float
    created_at: str
    last_accessed: str
    decay_factor: float
    privacy_level: PrivacyLevel
    source_agent: Optional[str] = None
    related_entities: List[str] = None
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        if self.related_entities is None:
            self.related_entities = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        result = asdict(self)
        result['type'] = self.type.value
        result['privacy_level'] = self.privacy_level.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContextEntity':
        """Create from dictionary"""
        data['type'] = ContextType(data['type'])
        data['privacy_level'] = PrivacyLevel(data['privacy_level'])
        return cls(**data)

@dataclass
class SessionContext:
    """Session-level context tracking"""
    session_id: str
    user_intent: str
    conversation_flow: List[Dict]
    active_capsule: Optional[str]
    lane_preference: str
    domain_focus: List[str]
    context_entities: List[ContextEntity]
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['context_entities'] = [entity.to_dict() for entity in self.context_entities]
        return result

@dataclass
class ContextRelationship:
    """Relationship between context entities"""
    source_id: str
    target_id: str
    relationship_type: RelationType
    strength: float
    confidence: float
    created_by: str
    created_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['relationship_type'] = self.relationship_type.value
        return result

class ContextIntelligenceEngine:
    """Core context intelligence system"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent / "registry" / "context_intelligence.db"
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Initialize components
        self.chroma_integration = ChromaIntegration() if ChromaIntegration else None
        self.knowledge_router = KnowledgeRouter() if KnowledgeRouter else None
        
        # Setup database
        self._init_database()
        
        # Current session tracking
        self.current_session: Optional[SessionContext] = None
        
        logger.info("Context Intelligence Engine initialized")
    
    def _init_database(self):
        """Initialize SQLite database for context storage"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Context entities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_entities (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    relevance_score REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    decay_factor REAL NOT NULL,
                    privacy_level TEXT NOT NULL,
                    source_agent TEXT,
                    related_entities TEXT,
                    embedding TEXT
                )
            """)
            
            # Context relationships table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS context_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES context_entities (id),
                    FOREIGN KEY (target_id) REFERENCES context_entities (id)
                )
            """)
            
            # Session contexts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_contexts (
                    session_id TEXT PRIMARY KEY,
                    user_intent TEXT,
                    conversation_flow TEXT,
                    active_capsule TEXT,
                    lane_preference TEXT,
                    domain_focus TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def start_session(self, session_id: str, user_intent: str = "", 
                     active_capsule: str = None, lane_preference: str = "auto") -> SessionContext:
        """Initialize a new session context"""
        self.current_session = SessionContext(
            session_id=session_id,
            user_intent=user_intent,
            conversation_flow=[],
            active_capsule=active_capsule,
            lane_preference=lane_preference,
            domain_focus=[],
            context_entities=[],
            created_at=datetime.utcnow().isoformat()
        )
        
        # Store in database
        self._store_session_context(self.current_session)
        
        logger.info(f"Started session context: {session_id}")
        return self.current_session
    
    def track_conversation_turn(self, user_input: str, agent_response: str, 
                               agent_name: str, metadata: Dict[str, Any] = None) -> ContextEntity:
        """Track a single conversation turn"""
        if not self.current_session:
            self.start_session(f"session_{datetime.utcnow().timestamp()}")
        
        # Create conversation turn context
        turn_context = {
            "user_input": user_input,
            "agent_response": agent_response,
            "agent_name": agent_name,
            "metadata": metadata or {},
            "turn_number": len(self.current_session.conversation_flow) + 1
        }
        
        # Add to conversation flow
        self.current_session.conversation_flow.append(turn_context)
        
        # Create context entity
        entity_id = self._generate_entity_id(f"turn_{self.current_session.session_id}_{len(self.current_session.conversation_flow)}")
        
        context_entity = ContextEntity(
            id=entity_id,
            type=ContextType.AGENT_INTERACTION,
            content=turn_context,
            relevance_score=1.0,  # Recent interactions are highly relevant
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
            decay_factor=0.1,  # How quickly this context becomes less relevant
            privacy_level=self._classify_privacy_level(turn_context),
            source_agent=agent_name,
            related_entities=[]
        )
        
        # Store context entity
        self._store_context_entity(context_entity)
        
        # Add to session context
        self.current_session.context_entities.append(context_entity)
        
        # Update domain focus
        self._update_domain_focus(user_input, agent_response)
        
        logger.debug(f"Tracked conversation turn for agent {agent_name}")
        return context_entity
    
    def extract_task_context(self, task_description: str, 
                           conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Extract structured context from task description and history"""
        context = {
            "task_description": task_description,
            "extracted_keywords": self._extract_keywords(task_description),
            "task_type": self._classify_task_type(task_description),
            "complexity_indicators": self._identify_complexity_indicators(task_description),
            "domain_indicators": self._identify_domain_indicators(task_description),
            "urgency_indicators": self._identify_urgency_indicators(task_description),
            "dependency_hints": self._identify_dependencies(task_description)
        }
        
        # Add conversation history context if available
        if conversation_history:
            context["conversation_context"] = self._extract_conversation_context(conversation_history)
        
        # Add related historical context
        if self.knowledge_router:
            try:
                related_knowledge = self.knowledge_router.get_knowledge(task_description, max_results=3)
                context["related_knowledge"] = [r.to_dict() for r in related_knowledge]
            except Exception as e:
                logger.warning(f"Failed to get related knowledge: {e}")
                context["related_knowledge"] = []
        
        return context
    
    def get_relevant_context(self, task_type: str, domain: str = "", 
                           agent_type: str = "", limit: int = 10) -> List[ContextEntity]:
        """Retrieve most relevant context for a task"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build query based on available filters
                query = """
                    SELECT * FROM context_entities 
                    WHERE privacy_level != 'secret'
                    ORDER BY relevance_score DESC, created_at DESC
                    LIMIT ?
                """
                
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                
                # Convert to ContextEntity objects
                context_entities = []
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
                        'embedding': json.loads(row[10]) if row[10] else None
                    }
                    
                    context_entities.append(ContextEntity.from_dict(entity_data))
                
                # Apply time-based decay to relevance scores
                context_entities = self._apply_temporal_decay(context_entities)
                
                # Filter by task type and domain if specified
                if task_type or domain or agent_type:
                    context_entities = self._filter_by_relevance(
                        context_entities, task_type, domain, agent_type
                    )
                
                return context_entities[:limit]
                
        except Exception as e:
            logger.error(f"Failed to get relevant context: {e}")
            return []
    
    def store_task_outcome(self, task_description: str, agent_name: str, 
                          outcome: Dict[str, Any], success: bool) -> ContextEntity:
        """Store task outcome as context for future reference"""
        entity_id = self._generate_entity_id(f"outcome_{agent_name}_{datetime.utcnow().timestamp()}")
        
        outcome_context = {
            "task_description": task_description,
            "agent_name": agent_name,
            "outcome": outcome,
            "success": success,
            "lessons_learned": self._extract_lessons_learned(outcome, success),
            "performance_metrics": outcome.get("performance_metrics", {})
        }
        
        context_entity = ContextEntity(
            id=entity_id,
            type=ContextType.OUTCOME,
            content=outcome_context,
            relevance_score=1.0 if success else 0.7,  # Successful outcomes more relevant
            created_at=datetime.utcnow().isoformat(),
            last_accessed=datetime.utcnow().isoformat(),
            decay_factor=0.05,  # Outcomes decay slowly
            privacy_level=self._classify_privacy_level(outcome_context),
            source_agent=agent_name,
            related_entities=[]
        )
        
        self._store_context_entity(context_entity)
        
        logger.info(f"Stored task outcome for {agent_name}: {'success' if success else 'failure'}")
        return context_entity
    
    def find_similar_tasks(self, task_description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar tasks from historical context"""
        if not self.chroma_integration:
            return []
        
        try:
            # Use Chroma vector search for semantic similarity
            similar_docs = self.chroma_integration.query_documents(task_description, n_results=limit)
            
            similar_tasks = []
            for doc in similar_docs:
                if doc.get("metadata", {}).get("type") == "task":
                    similar_tasks.append({
                        "task_description": doc.get("content", ""),
                        "similarity_score": doc.get("distance", 0.0),
                        "metadata": doc.get("metadata", {})
                    })
            
            return similar_tasks
            
        except Exception as e:
            logger.error(f"Failed to find similar tasks: {e}")
            return []
    
    def _store_context_entity(self, entity: ContextEntity):
        """Store context entity in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO context_entities
                    (id, type, content, relevance_score, created_at, last_accessed, 
                     decay_factor, privacy_level, source_agent, related_entities, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.id,
                    entity.type.value,
                    json.dumps(entity.content),
                    entity.relevance_score,
                    entity.created_at,
                    entity.last_accessed,
                    entity.decay_factor,
                    entity.privacy_level.value,
                    entity.source_agent,
                    json.dumps(entity.related_entities),
                    json.dumps(entity.embedding) if entity.embedding else None
                ))
                
                conn.commit()
                
                # Also store in Chroma for semantic search if available
                if self.chroma_integration and entity.privacy_level != PrivacyLevel.SECRET:
                    try:
                        content_text = json.dumps(entity.content)
                        self.chroma_integration.add_document(
                            content_text, 
                            metadata={
                                "entity_id": entity.id,
                                "type": entity.type.value,
                                "source_agent": entity.source_agent,
                                "created_at": entity.created_at
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to store in Chroma: {e}")
                
        except Exception as e:
            logger.error(f"Failed to store context entity: {e}")
    
    def _store_session_context(self, session: SessionContext):
        """Store session context in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO session_contexts
                    (session_id, user_intent, conversation_flow, active_capsule, 
                     lane_preference, domain_focus, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.session_id,
                    session.user_intent,
                    json.dumps(session.conversation_flow),
                    session.active_capsule,
                    session.lane_preference,
                    json.dumps(session.domain_focus),
                    session.created_at
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store session context: {e}")
    
    def _generate_entity_id(self, seed: str) -> str:
        """Generate unique entity ID"""
        return hashlib.md5(seed.encode()).hexdigest()
    
    def _classify_privacy_level(self, content: Dict[str, Any]) -> PrivacyLevel:
        """Classify privacy level of content"""
        content_str = json.dumps(content).lower()
        
        # Check for secret indicators
        secret_keywords = ["password", "key", "token", "secret", "credential"]
        if any(keyword in content_str for keyword in secret_keywords):
            return PrivacyLevel.SECRET
        
        # Check for private indicators
        private_keywords = ["personal", "private", "confidential"]
        if any(keyword in content_str for keyword in private_keywords):
            return PrivacyLevel.PRIVATE
        
        # Default to internal for system content
        return PrivacyLevel.INTERNAL
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction - can be enhanced with NLP
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3 and word.isalpha()]
        return list(set(keywords))[:10]  # Top 10 unique keywords
    
    def _classify_task_type(self, task_description: str) -> str:
        """Classify the type of task"""
        task_lower = task_description.lower()
        
        if any(keyword in task_lower for keyword in ["create", "build", "develop", "implement"]):
            return "creation"
        elif any(keyword in task_lower for keyword in ["fix", "debug", "repair", "solve"]):
            return "debugging"
        elif any(keyword in task_lower for keyword in ["analyze", "review", "check", "audit"]):
            return "analysis"
        elif any(keyword in task_lower for keyword in ["optimize", "improve", "enhance", "speed"]):
            return "optimization"
        elif any(keyword in task_lower for keyword in ["deploy", "setup", "configure", "install"]):
            return "deployment"
        else:
            return "general"
    
    def _identify_complexity_indicators(self, text: str) -> List[str]:
        """Identify complexity indicators in task description"""
        indicators = []
        text_lower = text.lower()
        
        complexity_patterns = {
            "high": ["complex", "advanced", "sophisticated", "enterprise", "scalable"],
            "medium": ["integration", "multiple", "various", "several", "coordination"],
            "simple": ["simple", "basic", "quick", "small", "minimal"]
        }
        
        for level, keywords in complexity_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                indicators.append(level)
        
        return indicators
    
    def _identify_domain_indicators(self, text: str) -> List[str]:
        """Identify domain indicators in task description"""
        domains = []
        text_lower = text.lower()
        
        domain_keywords = {
            "ios": ["ios", "swift", "xcode", "app store", "iphone", "ipad"],
            "web": ["web", "html", "css", "javascript", "react", "frontend"],
            "automation": ["automation", "workflow", "n8n", "pipeline", "schedule"],
            "data": ["data", "analysis", "csv", "json", "database", "sql"],
            "security": ["security", "auth", "permission", "encrypt", "vulnerability"],
            "performance": ["performance", "optimize", "speed", "memory", "cache"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                domains.append(domain)
        
        return domains
    
    def _identify_urgency_indicators(self, text: str) -> List[str]:
        """Identify urgency indicators in task description"""
        indicators = []
        text_lower = text.lower()
        
        urgency_keywords = {
            "high": ["urgent", "asap", "immediately", "critical", "emergency"],
            "medium": ["soon", "important", "priority", "needed"],
            "low": ["whenever", "eventually", "future", "nice to have"]
        }
        
        for level, keywords in urgency_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                indicators.append(level)
        
        return indicators or ["medium"]  # Default to medium if no indicators
    
    def _identify_dependencies(self, text: str) -> List[str]:
        """Identify potential dependencies in task description"""
        dependencies = []
        text_lower = text.lower()
        
        if "after" in text_lower or "depends on" in text_lower:
            dependencies.append("sequential_dependency")
        
        if "api" in text_lower or "service" in text_lower:
            dependencies.append("external_service")
        
        if "database" in text_lower or "storage" in text_lower:
            dependencies.append("data_dependency")
        
        return dependencies
    
    def _extract_conversation_context(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """Extract context from conversation history"""
        if not conversation_history:
            return {}
        
        return {
            "turn_count": len(conversation_history),
            "agents_involved": list(set(turn.get("agent_name", "unknown") for turn in conversation_history)),
            "topics_discussed": self._extract_topics_from_history(conversation_history),
            "recent_actions": conversation_history[-3:] if len(conversation_history) > 3 else conversation_history
        }
    
    def _extract_topics_from_history(self, history: List[Dict]) -> List[str]:
        """Extract topics from conversation history"""
        all_text = " ".join([
            turn.get("user_input", "") + " " + turn.get("agent_response", "")
            for turn in history
        ])
        return self._extract_keywords(all_text)[:5]  # Top 5 topics
    
    def _update_domain_focus(self, user_input: str, agent_response: str):
        """Update session domain focus based on conversation"""
        if not self.current_session:
            return
        
        # Extract domains from current interaction
        current_domains = self._identify_domain_indicators(user_input + " " + agent_response)
        
        # Update domain focus
        for domain in current_domains:
            if domain not in self.current_session.domain_focus:
                self.current_session.domain_focus.append(domain)
        
        # Keep only recent domains (max 5)
        self.current_session.domain_focus = self.current_session.domain_focus[-5:]
    
    def _apply_temporal_decay(self, entities: List[ContextEntity]) -> List[ContextEntity]:
        """Apply time-based decay to context relevance"""
        current_time = datetime.utcnow()
        
        for entity in entities:
            created_time = datetime.fromisoformat(entity.created_at)
            time_diff = (current_time - created_time).total_seconds() / 3600  # Hours
            
            # Apply exponential decay
            decay_multiplier = pow(0.99, time_diff * entity.decay_factor)
            entity.relevance_score *= decay_multiplier
        
        return sorted(entities, key=lambda e: e.relevance_score, reverse=True)
    
    def _filter_by_relevance(self, entities: List[ContextEntity], task_type: str, 
                           domain: str, agent_type: str) -> List[ContextEntity]:
        """Filter entities by relevance to current task"""
        filtered = []
        
        for entity in entities:
            relevance_boost = 0.0
            
            # Check task type relevance
            if task_type and task_type in json.dumps(entity.content).lower():
                relevance_boost += 0.2
            
            # Check domain relevance
            if domain and domain in json.dumps(entity.content).lower():
                relevance_boost += 0.2
            
            # Check agent type relevance
            if agent_type and entity.source_agent == agent_type:
                relevance_boost += 0.1
            
            # Apply boost
            entity.relevance_score += relevance_boost
            
            # Include if still relevant
            if entity.relevance_score > 0.1:
                filtered.append(entity)
        
        return sorted(filtered, key=lambda e: e.relevance_score, reverse=True)
    
    def _extract_lessons_learned(self, outcome: Dict[str, Any], success: bool) -> List[str]:
        """Extract lessons learned from task outcome"""
        lessons = []
        
        if success:
            lessons.append("Task completed successfully with current approach")
            if "duration" in outcome:
                lessons.append(f"Task completion time: {outcome['duration']}")
        else:
            lessons.append("Task encountered difficulties - review approach")
            if "error" in outcome:
                lessons.append(f"Error pattern: {outcome['error']}")
        
        return lessons
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get context intelligence performance statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count entities by type
                cursor.execute("SELECT type, COUNT(*) FROM context_entities GROUP BY type")
                entity_counts = dict(cursor.fetchall())
                
                # Count total entities
                cursor.execute("SELECT COUNT(*) FROM context_entities")
                total_entities = cursor.fetchone()[0]
                
                # Count relationships
                cursor.execute("SELECT COUNT(*) FROM context_relationships")
                total_relationships = cursor.fetchone()[0]
                
                # Count sessions
                cursor.execute("SELECT COUNT(*) FROM session_contexts")
                total_sessions = cursor.fetchone()[0]
                
                return {
                    "total_entities": total_entities,
                    "total_relationships": total_relationships,
                    "total_sessions": total_sessions,
                    "entity_breakdown": entity_counts,
                    "database_path": str(self.db_path),
                    "chroma_available": self.chroma_integration is not None,
                    "knowledge_router_available": self.knowledge_router is not None
                }
                
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {"error": str(e)}

# Convenience functions
def get_context_engine() -> ContextIntelligenceEngine:
    """Get shared context intelligence engine instance"""
    return ContextIntelligenceEngine()

def quick_context_lookup(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Quick context lookup function"""
    engine = get_context_engine()
    entities = engine.get_relevant_context("general", limit=limit)
    return [entity.to_dict() for entity in entities]

if __name__ == "__main__":
    # Test the context intelligence engine
    logging.basicConfig(level=logging.INFO)
    
    print("Context Intelligence Engine Test")
    print("=" * 50)
    
    engine = ContextIntelligenceEngine()
    
    # Test session creation
    session = engine.start_session("test_session", "Testing context intelligence")
    print(f"✓ Created session: {session.session_id}")
    
    # Test conversation tracking
    context_entity = engine.track_conversation_turn(
        "Create a simple iOS app",
        "I'll help you create an iOS app using Swift and Xcode",
        "iOS Dev",
        {"confidence": 0.9}
    )
    print(f"✓ Tracked conversation turn: {context_entity.id}")
    
    # Test task context extraction
    task_context = engine.extract_task_context("Build a web dashboard for analytics")
    print(f"✓ Extracted task context: {len(task_context)} fields")
    
    # Test context retrieval
    relevant_context = engine.get_relevant_context("creation", "ios", limit=5)
    print(f"✓ Retrieved {len(relevant_context)} relevant context entities")
    
    # Test performance stats
    stats = engine.get_performance_stats()
    print(f"✓ Performance stats: {stats['total_entities']} entities, {stats['total_sessions']} sessions")
    
    print("\nContext Intelligence Engine ready for integration")