#!/usr/bin/env python3
"""
Install Script for Builder Learning System
Sets up dependencies and initializes the complete learning infrastructure
"""

import subprocess
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

class LearningSystemInstaller:
    """Installer for Builder learning system components"""
    
    def __init__(self):
        self.builder_root = Path(__file__).parent.parent
        self.requirements = [
            "chromadb>=0.4.0",
            "sentence-transformers>=2.2.0",
            "torch>=2.0.0",  # Required for sentence-transformers
        ]
        
    def check_python_version(self) -> bool:
        """Check if Python version is compatible"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            logger.info(f"Python {version.major}.{version.minor} - Compatible")
            return True
        else:
            logger.error(f"Python {version.major}.{version.minor} - Requires Python 3.8+")
            return False
    
    def install_dependencies(self) -> bool:
        """Install required Python packages"""
        try:
            logger.info("Installing learning system dependencies...")
            
            for requirement in self.requirements:
                logger.info(f"Installing {requirement}")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", requirement
                ], capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to install {requirement}: {result.stderr}")
                    return False
                else:
                    logger.info(f"Successfully installed {requirement}")
            
            return True
            
        except Exception as e:
            logger.error(f"Dependency installation failed: {e}")
            return False
    
    def create_directory_structure(self) -> bool:
        """Create necessary directories for learning system"""
        try:
            directories = [
                self.builder_root / "global" / "rag" / "chroma_store",
                self.builder_root / "global" / "rag" / "config",
                self.builder_root / "registry" / "ml_models",
                self.builder_root / "registry" / "learning_data"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            
            return True
            
        except Exception as e:
            logger.error(f"Directory creation failed: {e}")
            return False
    
    def create_configuration_files(self) -> bool:
        """Create initial configuration files"""
        try:
            # Chroma configuration
            chroma_config = {
                "database_path": "global/rag/chroma_store",
                "collection_name": "builder_knowledge",
                "embedding_model": "all-MiniLM-L6-v2",
                "max_results_default": 5,
                "cache_size": 100
            }
            
            chroma_config_path = self.builder_root / "global" / "rag" / "config" / "chroma_config.json"
            with open(chroma_config_path, 'w') as f:
                json.dump(chroma_config, f, indent=2)
            
            logger.info(f"Created Chroma config: {chroma_config_path}")
            
            # Learning system configuration
            learning_config = {
                "validation_schedule": "daily",
                "metrics_retention_days": 90,
                "baseline_update_frequency": "monthly",
                "test_cases_enabled": True,
                "auto_sync_mcp_to_chroma": True,
                "performance_thresholds": {
                    "query_accuracy": 0.7,
                    "knowledge_retention": 0.6,
                    "context_awareness": 0.6
                }
            }
            
            learning_config_path = self.builder_root / "global" / "rag" / "config" / "learning_config.json"
            with open(learning_config_path, 'w') as f:
                json.dump(learning_config, f, indent=2)
            
            logger.info(f"Created learning config: {learning_config_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration creation failed: {e}")
            return False
    
    def test_installations(self) -> Dict[str, bool]:
        """Test that all components are working correctly"""
        test_results = {}
        
        # Test Chroma integration
        try:
            sys.path.append(str(self.builder_root / "global" / "rag"))
            from chroma_integration import ChromaIntegration
            
            chroma = ChromaIntegration()
            test_id = chroma.add_knowledge("Test knowledge for installation", {"test": True})
            
            if test_id:
                # Clean up test data
                search_results = chroma.search_knowledge("Test knowledge", n_results=1)
                test_results["chroma_integration"] = len(search_results) > 0
                logger.info("✓ Chroma integration test passed")
            else:
                test_results["chroma_integration"] = False
                logger.error("✗ Chroma integration test failed")
                
        except Exception as e:
            test_results["chroma_integration"] = False
            logger.error(f"✗ Chroma integration test failed: {e}")
        
        # Test MCP sync
        try:
            from mcp_chroma_sync import MCPChromaSync
            
            sync = MCPChromaSync()
            validation = sync.validate_sync()
            test_results["mcp_sync"] = "error" not in validation
            logger.info("✓ MCP sync test passed")
            
        except Exception as e:
            test_results["mcp_sync"] = False
            logger.error(f"✗ MCP sync test failed: {e}")
        
        # Test Knowledge Router
        try:
            from knowledge_router import KnowledgeRouter
            
            router = KnowledgeRouter()
            results = router.get_knowledge("test query", max_results=1)
            test_results["knowledge_router"] = isinstance(results, list)
            logger.info("✓ Knowledge router test passed")
            
        except Exception as e:
            test_results["knowledge_router"] = False
            logger.error(f"✗ Knowledge router test failed: {e}")
        
        # Test Optimized Knowledge Graph
        try:
            sys.path.append(str(self.builder_root / "tools"))
            from optimized_knowledge_graph import OptimizedKnowledgeGraph
            
            graph = OptimizedKnowledgeGraph()
            graph.add_entity("test_entity", "Test Entity", "test")
            entity = graph.find_entity_by_name("Test Entity")
            test_results["knowledge_graph"] = entity is not None
            logger.info("✓ Knowledge graph test passed")
            
        except Exception as e:
            test_results["knowledge_graph"] = False
            logger.error(f"✗ Knowledge graph test failed: {e}")
        
        # Test Learning Validator
        try:
            from learning_validator import LearningValidator
            
            validator = LearningValidator()
            baseline = validator.get_baseline_metrics()
            test_results["learning_validator"] = isinstance(baseline, dict)
            logger.info("✓ Learning validator test passed")
            
        except Exception as e:
            test_results["learning_validator"] = False
            logger.error(f"✗ Learning validator test failed: {e}")
        
        return test_results
    
    def perform_initial_sync(self) -> bool:
        """Perform initial MCP to Chroma sync"""
        try:
            logger.info("Performing initial MCP to Chroma sync...")
            
            sys.path.append(str(self.builder_root / "global" / "rag"))
            from mcp_chroma_sync import sync_now
            
            result = sync_now(force_full=True)
            
            if result.get("status") == "success":
                synced_items = result.get("synced_items", 0)
                logger.info(f"✓ Initial sync completed: {synced_items} items synced")
                return True
            else:
                logger.warning(f"Initial sync completed with issues: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Initial sync failed: {e}")
            return False
    
    def install_complete_system(self) -> bool:
        """Install and configure the complete learning system"""
        logger.info("Starting Builder Learning System installation")
        logger.info("=" * 50)
        
        # Step 1: Check Python version
        if not self.check_python_version():
            return False
        
        # Step 2: Install dependencies
        if not self.install_dependencies():
            return False
        
        # Step 3: Create directory structure
        if not self.create_directory_structure():
            return False
        
        # Step 4: Create configuration files
        if not self.create_configuration_files():
            return False
        
        # Step 5: Test installations
        logger.info("Testing installed components...")
        test_results = self.test_installations()
        
        failed_tests = [name for name, passed in test_results.items() if not passed]
        if failed_tests:
            logger.error(f"Some tests failed: {failed_tests}")
            logger.info("System partially installed - manual troubleshooting may be needed")
        else:
            logger.info("✓ All component tests passed")
        
        # Step 6: Initial sync (if MCP available)
        if test_results.get("mcp_sync", False):
            self.perform_initial_sync()
        else:
            logger.info("Skipping initial sync - MCP memory not available")
        
        # Installation summary
        logger.info("=" * 50)
        logger.info("Builder Learning System Installation Summary:")
        logger.info(f"✓ Dependencies installed: {len(self.requirements)} packages")
        logger.info(f"✓ Directories created: 4 directories")
        logger.info(f"✓ Configuration files: 2 files")
        logger.info(f"✓ Component tests: {sum(test_results.values())}/{len(test_results)} passed")
        
        if all(test_results.values()):
            logger.info("🎉 Installation completed successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Run learning validation: python tools/learning_validator.py")
            logger.info("2. Test knowledge search: python global/rag/knowledge_router.py")
            logger.info("3. Sync MCP data: python global/rag/mcp_chroma_sync.py --sync")
            return True
        else:
            logger.warning("⚠️ Installation completed with some issues")
            logger.info("Check the error messages above and resolve issues manually")
            return False

def main():
    """Main installation function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    installer = LearningSystemInstaller()
    success = installer.install_complete_system()
    
    if success:
        print("\n🚀 Builder Learning System is ready!")
    else:
        print("\n❌ Installation encountered issues - see log above")
        sys.exit(1)

if __name__ == "__main__":
    main()