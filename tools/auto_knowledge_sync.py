#!/usr/bin/env python3
"""
Automatic Knowledge Sync for Catalyst
Continuously syncs MCP memory to Chroma vector database
"""

import sys
import logging
from pathlib import Path

# Add RAG path
rag_path = Path(__file__).parent.parent / "global" / "rag"
sys.path.append(str(rag_path))

from mcp_chroma_sync import sync_now
from knowledge_router import KnowledgeRouter

logger = logging.getLogger(__name__)

def auto_sync_knowledge():
    """Automatically sync MCP memory to Chroma vector database"""
    try:
        logger.info("Starting automatic knowledge sync...")
        
        # Perform sync
        result = sync_now(force_full=False)
        
        if result.get("status") == "success":
            synced_items = result.get("synced_items", 0)
            logger.info(f"✓ Auto-sync completed: {synced_items} items synced")
            return True
        elif result.get("status") == "no_data":
            logger.info("✓ Auto-sync: No new data to sync")
            return True
        else:
            logger.warning(f"Auto-sync completed with issues: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Auto-sync failed: {e}")
        return False

def search_knowledge(query: str, max_results: int = 5):
    """Quick knowledge search function"""
    try:
        router = KnowledgeRouter()
        results = router.get_knowledge(query, max_results=max_results)
        return [r.to_dict() for r in results]
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        return []

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Catalyst - Automatic Knowledge Sync")
    print("=" * 45)
    
    # Test sync
    success = auto_sync_knowledge()
    
    if success:
        print("✓ Knowledge sync activated")
        
        # Test search
        print("\nTesting knowledge search:")
        results = search_knowledge("What is the Catalyst?")
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results[:2], 1):
                print(f"  {i}. {result['content'][:60]}...")
        else:
            print("No results found")
    else:
        print("✗ Knowledge sync failed")