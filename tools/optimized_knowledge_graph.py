#!/usr/bin/env python3
"""
Optimized Knowledge Graph for Catalyst
Replaces O(n²) operations with indexed lookups and Chroma vector integration
"""

import json
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sys

# Add global/rag to path for knowledge router
rag_path = Path(__file__).parent.parent / "global" / "rag"
sys.path.append(str(rag_path))

try:
    from knowledge_router import KnowledgeRouter, search_builder_knowledge
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Knowledge router not available, using basic implementation")
    KnowledgeRouter = None

logger = logging.getLogger(__name__)

class OptimizedKnowledgeGraph:
    """High-performance knowledge graph with vector search integration"""
    
    def __init__(self):
        self.entities = {}  # id -> entity data
        self.relationships = {}  # id -> relationship data
        
        # Optimization indexes
        self.entity_name_index = {}  # name -> entity_id
        self.entity_type_index = defaultdict(set)  # type -> set of entity_ids
        self.relationship_from_index = defaultdict(set)  # from_entity -> set of relationship_ids
        self.relationship_to_index = defaultdict(set)  # to_entity -> set of relationship_ids
        self.relationship_type_index = defaultdict(set)  # type -> set of relationship_ids
        
        # Vector search integration
        self.knowledge_router = KnowledgeRouter() if KnowledgeRouter else None
        
        # Performance tracking
        self.query_stats = {
            "entity_lookups": 0,
            "relationship_queries": 0,
            "vector_searches": 0,
            "cache_hits": 0
        }
        
        # Simple cache for frequent queries
        self.query_cache = {}
        self.cache_max_size = 100
    
    def add_entity(self, entity_id: str, name: str, entity_type: str, observations: List[str] = None) -> bool:
        """Add entity with automatic indexing"""
        try:
            observations = observations or []
            
            entity_data = {
                "id": entity_id,
                "name": name,
                "type": entity_type,
                "observations": observations,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Store entity
            self.entities[entity_id] = entity_data
            
            # Update indexes
            self.entity_name_index[name.lower()] = entity_id
            self.entity_type_index[entity_type].add(entity_id)
            
            logger.debug(f"Added entity: {name} ({entity_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add entity {name}: {e}")
            return False
    
    def add_relationship(self, rel_id: str, from_entity: str, to_entity: str, relationship_type: str, metadata: Dict = None) -> bool:
        """Add relationship with automatic indexing"""
        try:
            metadata = metadata or {}
            
            relationship_data = {
                "id": rel_id,
                "from": from_entity,
                "to": to_entity,
                "type": relationship_type,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Store relationship
            self.relationships[rel_id] = relationship_data
            
            # Update indexes
            self.relationship_from_index[from_entity].add(rel_id)
            self.relationship_to_index[to_entity].add(rel_id)
            self.relationship_type_index[relationship_type].add(rel_id)
            
            # Clear cache for affected entities
            self._invalidate_cache_for_entity(from_entity)
            self._invalidate_cache_for_entity(to_entity)
            
            logger.debug(f"Added relationship: {from_entity} → {relationship_type} → {to_entity}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add relationship {from_entity} → {to_entity}: {e}")
            return False
    
    def find_entity_by_name(self, name: str) -> Optional[Dict]:
        """O(1) entity lookup by name"""
        self.query_stats["entity_lookups"] += 1
        
        entity_id = self.entity_name_index.get(name.lower())
        if entity_id:
            self.query_stats["cache_hits"] += 1
            return self.entities.get(entity_id)
        
        return None
    
    def find_entities_by_type(self, entity_type: str) -> List[Dict]:
        """O(1) entity lookup by type"""
        self.query_stats["entity_lookups"] += 1
        
        entity_ids = self.entity_type_index.get(entity_type, set())
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def get_entity_relationships(self, entity_name: str, direction: str = "both") -> List[Dict]:
        """O(log n) relationship lookup for entity"""
        self.query_stats["relationship_queries"] += 1
        
        # Check cache first
        cache_key = f"relationships_{entity_name}_{direction}"
        if cache_key in self.query_cache:
            self.query_stats["cache_hits"] += 1
            return self.query_cache[cache_key]
        
        relationships = []
        
        if direction in ["both", "outgoing"]:
            # Get outgoing relationships
            rel_ids = self.relationship_from_index.get(entity_name, set())
            relationships.extend([self.relationships[rid] for rid in rel_ids if rid in self.relationships])
        
        if direction in ["both", "incoming"]:
            # Get incoming relationships
            rel_ids = self.relationship_to_index.get(entity_name, set())
            relationships.extend([self.relationships[rid] for rid in rel_ids if rid in self.relationships])
        
        # Cache result
        self._cache_result(cache_key, relationships)
        
        return relationships
    
    def find_path_between_entities(self, start_entity: str, end_entity: str, max_depth: int = 3) -> List[List[str]]:
        """Find relationship paths between entities (optimized BFS)"""
        if start_entity == end_entity:
            return [[start_entity]]
        
        visited = set()
        queue = [(start_entity, [start_entity])]
        paths = []
        
        for depth in range(max_depth):
            next_queue = []
            
            while queue:
                current_entity, path = queue.pop(0)
                
                if current_entity in visited:
                    continue
                visited.add(current_entity)
                
                # Get connected entities using indexed lookup
                relationships = self.get_entity_relationships(current_entity, "outgoing")
                
                for rel in relationships:
                    next_entity = rel["to"]
                    new_path = path + [next_entity]
                    
                    if next_entity == end_entity:
                        paths.append(new_path)
                    elif next_entity not in visited:
                        next_queue.append((next_entity, new_path))
            
            queue = next_queue
            if paths:  # Found at least one path at this depth
                break
        
        return paths
    
    def semantic_search(self, query: str, entity_types: List[str] = None, max_results: int = 5) -> List[Dict]:
        """Semantic search using vector database integration"""
        if not self.knowledge_router:
            return self._fallback_text_search(query, entity_types, max_results)
        
        self.query_stats["vector_searches"] += 1
        
        try:
            # Use knowledge router for semantic search
            results = self.knowledge_router.get_knowledge(query, max_results=max_results)
            
            # Filter by entity types if specified
            if entity_types:
                filtered_results = []
                for result in results:
                    entity_type = result.metadata.get("entity_type")
                    if entity_type in entity_types:
                        filtered_results.append(result.to_dict())
                return filtered_results
            
            return [result.to_dict() for result in results]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return self._fallback_text_search(query, entity_types, max_results)
    
    def _fallback_text_search(self, query: str, entity_types: List[str] = None, max_results: int = 5) -> List[Dict]:
        """Fallback text search when vector search unavailable"""
        query_lower = query.lower()
        results = []
        
        for entity in self.entities.values():
            if entity_types and entity["type"] not in entity_types:
                continue
            
            # Simple text matching
            entity_text = f"{entity['name']} {' '.join(entity['observations'])}".lower()
            if query_lower in entity_text:
                score = len([word for word in query_lower.split() if word in entity_text]) / len(query_lower.split())
                results.append({
                    "entity": entity,
                    "score": score,
                    "match_type": "text"
                })
        
        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]
    
    def get_entity_clusters(self, min_connections: int = 2) -> Dict[str, List[str]]:
        """Find clusters of highly connected entities"""
        clusters = defaultdict(list)
        
        for entity_id, entity in self.entities.items():
            entity_name = entity["name"]
            connections = len(self.get_entity_relationships(entity_name))
            
            if connections >= min_connections:
                cluster_key = f"cluster_{connections}_connections"
                clusters[cluster_key].append(entity_name)
        
        return dict(clusters)
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        total_queries = sum(self.query_stats.values())
        
        return {
            "total_entities": len(self.entities),
            "total_relationships": len(self.relationships),
            "index_sizes": {
                "entity_names": len(self.entity_name_index),
                "entity_types": len(self.entity_type_index),
                "relationship_from": len(self.relationship_from_index),
                "relationship_to": len(self.relationship_to_index)
            },
            "query_stats": self.query_stats,
            "cache_hit_rate": self.query_stats["cache_hits"] / max(total_queries, 1),
            "cache_size": len(self.query_cache)
        }
    
    def _cache_result(self, key: str, result: Any):
        """Cache query result with size limit"""
        if len(self.query_cache) >= self.cache_max_size:
            # Simple FIFO eviction
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[key] = result
    
    def _invalidate_cache_for_entity(self, entity_name: str):
        """Invalidate cache entries related to entity"""
        keys_to_remove = [key for key in self.query_cache.keys() if entity_name in key]
        for key in keys_to_remove:
            del self.query_cache[key]
    
    def export_to_dict(self) -> Dict:
        """Export graph data for persistence"""
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "total_entities": len(self.entities),
                "total_relationships": len(self.relationships)
            }
        }
    
    def import_from_dict(self, data: Dict):
        """Import graph data and rebuild indexes"""
        try:
            # Clear existing data
            self.entities.clear()
            self.relationships.clear()
            self._clear_indexes()
            
            # Import entities
            for entity_id, entity_data in data.get("entities", {}).items():
                self.entities[entity_id] = entity_data
                # Rebuild indexes
                name = entity_data.get("name", "")
                entity_type = entity_data.get("type", "")
                if name:
                    self.entity_name_index[name.lower()] = entity_id
                if entity_type:
                    self.entity_type_index[entity_type].add(entity_id)
            
            # Import relationships
            for rel_id, rel_data in data.get("relationships", {}).items():
                self.relationships[rel_id] = rel_data
                # Rebuild indexes
                from_entity = rel_data.get("from", "")
                to_entity = rel_data.get("to", "")
                rel_type = rel_data.get("type", "")
                
                if from_entity:
                    self.relationship_from_index[from_entity].add(rel_id)
                if to_entity:
                    self.relationship_to_index[to_entity].add(rel_id)
                if rel_type:
                    self.relationship_type_index[rel_type].add(rel_id)
            
            logger.info(f"Imported {len(self.entities)} entities and {len(self.relationships)} relationships")
            
        except Exception as e:
            logger.error(f"Failed to import graph data: {e}")
            raise
    
    def _clear_indexes(self):
        """Clear all indexes"""
        self.entity_name_index.clear()
        self.entity_type_index.clear()
        self.relationship_from_index.clear()
        self.relationship_to_index.clear()
        self.relationship_type_index.clear()
        self.query_cache.clear()

# Global instance for Catalyst
_graph_instance = None

def get_optimized_graph() -> OptimizedKnowledgeGraph:
    """Get singleton optimized graph instance"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = OptimizedKnowledgeGraph()
    return _graph_instance

def search_entities(query: str, entity_types: List[str] = None, max_results: int = 5) -> List[Dict]:
    """Quick entity search function"""
    graph = get_optimized_graph()
    return graph.semantic_search(query, entity_types, max_results)

def get_entity_connections(entity_name: str) -> List[Dict]:
    """Quick function to get entity relationships"""
    graph = get_optimized_graph()
    return graph.get_entity_relationships(entity_name)

if __name__ == "__main__":
    # Test the optimized knowledge graph
    logging.basicConfig(level=logging.INFO)
    
    graph = OptimizedKnowledgeGraph()
    
    # Test adding entities and relationships
    print("Testing Optimized Knowledge Graph")
    print("=" * 40)
    
    # Add test entities
    graph.add_entity("builder_system", "Catalyst", "system", ["Core system for building projects"])
    graph.add_entity("{{ORCHESTRATOR_NAME_LOWER}}", "{{ORCHESTRATOR_NAME}}", "agent", ["Number-2 agent", "Learning system"])
    graph.add_entity("chroma", "Chroma Database", "technology", ["Vector database", "Local deployment"])
    
    # Add test relationships
    graph.add_relationship("rel1", "{{ORCHESTRATOR_NAME}}", "Catalyst", "enhances")
    graph.add_relationship("rel2", "Chroma Database", "Catalyst", "provides_knowledge_for")
    graph.add_relationship("rel3", "{{ORCHESTRATOR_NAME}}", "Chroma Database", "uses")
    
    # Test optimized operations
    print(f"\nPerformance stats: {graph.get_performance_stats()}")
    
    print(f"\nEntity lookup: {graph.find_entity_by_name('Catalyst')}")
    print(f"\n{{ORCHESTRATOR_NAME}} relationships: {len(graph.get_entity_relationships('{{ORCHESTRATOR_NAME}}'))} found")
    
    # Test semantic search
    search_results = graph.semantic_search("learning system")
    print(f"\nSemantic search results: {len(search_results)} found")
    
    print("\nOptimized Knowledge Graph ready for integration")