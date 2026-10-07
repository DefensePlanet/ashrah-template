#!/usr/bin/env python3
"""
Test Lane Guard - Protect production capsules and redirect test operations
Implements environment partitioning with write-guards for production safety
"""

import os
import sys
import json
import pathlib
import shutil
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re

# Add Builder tools to path  
BUILDER_ROOT = pathlib.Path.home() / "Documents" / "Builder"
sys.path.append(str(BUILDER_ROOT / "tools"))

try:
    from events_logger import log_event
except ImportError:
    # Fallback event logging
    def log_event(stage, level, message, capsule="system", data=None):
        print(f"[{level}] {stage}: {message}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class GuardResult:
    """Result of guard operation"""
    allowed: bool
    action: str
    original_path: str
    redirected_path: Optional[str] = None
    reason: str = ""
    guard_type: str = ""

class TestLaneGuard:
    """Guards production resources from test contamination"""
    
    def __init__(self, builder_root: pathlib.Path = None):
        self.builder_root = builder_root or BUILDER_ROOT
        self.production_root = self.builder_root
        self.testing_root = self.builder_root / "testing"
        
        # Ensure testing directory structure exists
        self._ensure_testing_structure()
        
        # Define protection patterns
        self.protected_paths = [
            "capsules",          # Production capsules
            "registry/daily",    # Daily audit results
            "registry/weekly",   # Weekly audit results
            "global/events.log", # Main event log
            "global/rag/service/chroma_db", # Production RAG database
        ]
        
        # Define test-safe operations
        self.test_safe_operations = [
            "read", "query", "validate", "analyze", "report", "dry_run"
        ]
        
    def _ensure_testing_structure(self):
        """Create testing directory structure if it doesn't exist"""
        testing_dirs = [
            self.testing_root,
            self.testing_root / "capsules",
            self.testing_root / "registry" / "daily",
            self.testing_root / "registry" / "weekly", 
            self.testing_root / "global" / "rag" / "service",
            self.testing_root / "global" / "backups",
        ]
        
        for test_dir in testing_dirs:
            test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test-specific config
        test_config_file = self.testing_root / "global" / "config.json"
        if not test_config_file.exists():
            test_config = {
                "environment": "test",
                "rag": {
                    "enabled": True,
                    "endpoint": "http://localhost:8003",  # Different port for test
                    "database_path": str(self.testing_root / "global" / "rag" / "service" / "chroma_db")
                },
                "events": {
                    "log_file": str(self.testing_root / "global" / "events.log")
                },
                "safety": {
                    "test_mode": True,
                    "production_guard": True
                }
            }
            
            with open(test_config_file, 'w') as f:
                json.dump(test_config, f, indent=2)
    
    def detect_operation_intent(self, operation: str, paths: List[str]) -> str:
        """Detect if operation is read-only or write-intensive"""
        operation_lower = operation.lower()
        
        # Check for explicit safe operations
        for safe_op in self.test_safe_operations:
            if safe_op in operation_lower:
                return "read"
        
        # Check for write operations
        write_indicators = [
            "create", "write", "delete", "remove", "update", "modify", 
            "insert", "upsert", "save", "commit", "deploy", "install"
        ]
        
        for write_op in write_indicators:
            if write_op in operation_lower:
                return "write"
        
        # Check paths for write indicators
        for path in paths:
            if any(indicator in path.lower() for indicator in ["temp", "tmp", "test", "staging"]):
                return "write"  # Assume temp/test paths are for writing
        
        # Default to read for safety
        return "read"
    
    def is_protected_path(self, path: pathlib.Path) -> bool:
        """Check if path is protected from test operations"""
        try:
            # Convert to relative path from builder root
            rel_path = path.relative_to(self.builder_root)
            path_str = str(rel_path)
            
            # Check against protected patterns
            for protected in self.protected_paths:
                if path_str.startswith(protected):
                    return True
            
            # Check for specific file patterns
            if path.name.endswith('.pid'):  # Process ID files
                return True
                
            if path.name.startswith('.lock'):  # Lock files
                return True
                
            return False
            
        except ValueError:
            # Path is not relative to builder root, likely external
            return False
    
    def get_test_redirect_path(self, original_path: pathlib.Path) -> pathlib.Path:
        """Get the corresponding test path for a production path"""
        try:
            # Get relative path from production root
            rel_path = original_path.relative_to(self.production_root)
            
            # Create corresponding test path
            test_path = self.testing_root / rel_path
            
            # Ensure parent directories exist
            test_path.parent.mkdir(parents=True, exist_ok=True)
            
            return test_path
            
        except ValueError:
            # Path not under production root, return as-is
            return original_path
    
    def check_operation(self, operation: str, paths: List[str], 
                       context: Dict[str, Any] = None) -> GuardResult:
        """Check if operation is allowed or needs redirection"""
        context = context or {}
        
        # Detect operation intent
        operation_intent = self.detect_operation_intent(operation, paths)
        
        # Check for explicit test mode
        test_mode = (
            context.get('test_mode', False) or
            any('test' in p.lower() for p in paths) or
            os.environ.get('BUILDER_TEST_MODE') == 'true'
        )
        
        if not paths:
            return GuardResult(
                allowed=True,
                action="allow",
                original_path="",
                reason="No paths to check"
            )
        
        primary_path = pathlib.Path(paths[0])
        
        # Always allow read operations on production
        if operation_intent == "read":
            return GuardResult(
                allowed=True,
                action="allow",
                original_path=str(primary_path),
                reason="Read operation allowed",
                guard_type="read_guard"
            )
        
        # Check if path is protected
        is_protected = self.is_protected_path(primary_path)
        
        if not is_protected:
            return GuardResult(
                allowed=True,
                action="allow", 
                original_path=str(primary_path),
                reason="Path not protected",
                guard_type="path_guard"
            )
        
        # Protected path with write operation
        if test_mode:
            # Redirect to test environment
            test_path = self.get_test_redirect_path(primary_path)
            return GuardResult(
                allowed=True,
                action="redirect",
                original_path=str(primary_path),
                redirected_path=str(test_path),
                reason="Test mode: redirected to test environment",
                guard_type="test_redirect"
            )
        else:
            # Block production write
            return GuardResult(
                allowed=False,
                action="block",
                original_path=str(primary_path),
                reason="Production write blocked - use test mode",
                guard_type="production_guard"
            )
    
    def guard_capsule_operation(self, capsule_name: str, operation: str,
                              test_mode: bool = False) -> GuardResult:
        """Guard capsule-specific operations"""
        capsule_path = self.production_root / "capsules" / capsule_name
        
        context = {
            'test_mode': test_mode,
            'capsule': capsule_name
        }
        
        result = self.check_operation(operation, [str(capsule_path)], context)
        
        # Log significant guard actions
        if result.action in ["block", "redirect"]:
            log_event(
                level="WARNING" if result.action == "block" else "INFO",
                message=f"Guard action: {result.action} - {result.reason}",
                capsule=capsule_name,
                data={
                    "operation": operation,
                    "original_path": result.original_path,
                    "redirected_path": result.redirected_path,
                    "guard_type": result.guard_type
                }
            )
        
        return result
    
    def create_test_capsule_copy(self, capsule_name: str, 
                               preserve_runs: bool = False) -> GuardResult:
        """Create a test copy of a production capsule"""
        prod_capsule_path = self.production_root / "capsules" / capsule_name
        test_capsule_path = self.testing_root / "capsules" / capsule_name
        
        if not prod_capsule_path.exists():
            return GuardResult(
                allowed=False,
                action="error",
                original_path=str(prod_capsule_path),
                reason=f"Production capsule '{capsule_name}' not found"
            )
        
        try:
            # Remove existing test capsule if present
            if test_capsule_path.exists():
                shutil.rmtree(test_capsule_path)
            
            # Copy capsule structure
            shutil.copytree(prod_capsule_path, test_capsule_path)
            
            # Clear runs directory unless preservation requested
            if not preserve_runs:
                runs_dir = test_capsule_path / "runs"
                if runs_dir.exists():
                    shutil.rmtree(runs_dir)
                    runs_dir.mkdir()
            
            # Clear ops directory (always reset for test)
            ops_dir = test_capsule_path / "ops"
            if ops_dir.exists():
                shutil.rmtree(ops_dir)
                ops_dir.mkdir()
            
            # Update capsule.json to indicate test copy
            capsule_json = test_capsule_path / "capsule.json"
            if capsule_json.exists():
                with open(capsule_json, 'r') as f:
                    capsule_data = json.load(f)
                
                capsule_data['test_copy'] = True
                capsule_data['test_created_at'] = datetime.now().isoformat()
                capsule_data['original_capsule'] = capsule_name
                
                with open(capsule_json, 'w') as f:
                    json.dump(capsule_data, f, indent=2)
            
            log_event(
                level="INFO",
                message=f"Test capsule copy created: {capsule_name}",
                capsule=capsule_name,
                data={
                    "preserve_runs": preserve_runs,
                    "test_path": str(test_capsule_path)
                }
            )
            
            return GuardResult(
                allowed=True,
                action="create_test_copy",
                original_path=str(prod_capsule_path),
                redirected_path=str(test_capsule_path),
                reason="Test capsule copy created successfully"
            )
            
        except Exception as e:
            return GuardResult(
                allowed=False,
                action="error",
                original_path=str(prod_capsule_path),
                reason=f"Failed to create test copy: {e}"
            )
    
    def validate_test_environment(self) -> Dict[str, Any]:
        """Validate test environment setup"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "test_structure": {}
        }
        
        # Check directory structure
        required_dirs = [
            "capsules",
            "registry/daily", 
            "registry/weekly",
            "global/rag/service"
        ]
        
        for dir_path in required_dirs:
            full_path = self.testing_root / dir_path
            exists = full_path.exists()
            validation_results["test_structure"][dir_path] = exists
            
            if not exists:
                validation_results["errors"].append(f"Missing test directory: {dir_path}")
                validation_results["valid"] = False
        
        # Check test configuration
        test_config_file = self.testing_root / "global" / "config.json"
        if test_config_file.exists():
            try:
                with open(test_config_file, 'r') as f:
                    test_config = json.load(f)
                
                if test_config.get("environment") != "test":
                    validation_results["warnings"].append("Test config missing environment=test")
                    
                if not test_config.get("safety", {}).get("test_mode"):
                    validation_results["warnings"].append("Test config missing safety.test_mode=true")
                    
            except Exception as e:
                validation_results["errors"].append(f"Test config invalid: {e}")
                validation_results["valid"] = False
        else:
            validation_results["errors"].append("Test config file missing")
            validation_results["valid"] = False
        
        # Check for accidental production contamination
        test_capsules_dir = self.testing_root / "capsules"
        if test_capsules_dir.exists():
            for test_capsule in test_capsules_dir.iterdir():
                if test_capsule.is_dir():
                    capsule_json = test_capsule / "capsule.json"
                    if capsule_json.exists():
                        try:
                            with open(capsule_json, 'r') as f:
                                capsule_data = json.load(f)
                            
                            if not capsule_data.get('test_copy'):
                                validation_results["warnings"].append(
                                    f"Test capsule {test_capsule.name} missing test_copy flag"
                                )
                        except:
                            validation_results["warnings"].append(
                                f"Could not validate test capsule {test_capsule.name}"
                            )
        
        return validation_results

def main():
    """CLI interface for test lane guard"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Lane Guard - Production Protection")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check if operation is allowed")
    check_parser.add_argument("operation", help="Operation to check")
    check_parser.add_argument("paths", nargs="+", help="Paths involved in operation")
    check_parser.add_argument("--test-mode", action="store_true", help="Enable test mode")
    check_parser.add_argument("--capsule", help="Capsule name for context")
    
    # Guard command  
    guard_parser = subparsers.add_parser("guard", help="Guard capsule operation")
    guard_parser.add_argument("capsule", help="Capsule name")
    guard_parser.add_argument("operation", help="Operation to guard")
    guard_parser.add_argument("--test-mode", action="store_true", help="Enable test mode")
    
    # Copy command
    copy_parser = subparsers.add_parser("copy", help="Create test capsule copy")
    copy_parser.add_argument("capsule", help="Capsule name to copy")
    copy_parser.add_argument("--preserve-runs", action="store_true", help="Preserve run history")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate test environment")
    validate_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Setup test environment")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        guard = TestLaneGuard()
        
        if args.command == "check":
            context = {
                'test_mode': args.test_mode,
                'capsule': args.capsule
            }
            result = guard.check_operation(args.operation, args.paths, context)
            
            status_emoji = {"allow": "✅", "redirect": "↗️", "block": "❌", "error": "🚨"}
            print(f"{status_emoji.get(result.action, '?')} {result.action.upper()}: {result.reason}")
            
            if result.redirected_path:
                print(f"  Original: {result.original_path}")
                print(f"  Redirected: {result.redirected_path}")
            
            sys.exit(0 if result.allowed else 1)
        
        elif args.command == "guard":
            result = guard.guard_capsule_operation(args.capsule, args.operation, args.test_mode)
            
            status_emoji = {"allow": "✅", "redirect": "↗️", "block": "❌", "error": "🚨"}
            print(f"{status_emoji.get(result.action, '?')} {result.action.upper()}: {result.reason}")
            
            if result.redirected_path:
                print(f"  Use test path: {result.redirected_path}")
            
            sys.exit(0 if result.allowed else 1)
        
        elif args.command == "copy":
            result = guard.create_test_capsule_copy(args.capsule, args.preserve_runs)
            
            if result.allowed:
                print(f"✅ Test copy created: {args.capsule}")
                print(f"  Location: {result.redirected_path}")
            else:
                print(f"❌ Failed to create test copy: {result.reason}")
            
            sys.exit(0 if result.allowed else 1)
        
        elif args.command == "validate":
            validation = guard.validate_test_environment()
            
            if args.json:
                print(json.dumps(validation, indent=2))
            else:
                status = "✅ VALID" if validation["valid"] else "❌ INVALID"
                print(f"🧪 Test Environment Validation: {status}")
                print("=" * 50)
                
                print("Directory Structure:")
                for dir_path, exists in validation["test_structure"].items():
                    status_emoji = "✅" if exists else "❌"
                    print(f"  {status_emoji} {dir_path}")
                
                if validation["errors"]:
                    print(f"\nErrors ({len(validation['errors'])}):")
                    for error in validation["errors"]:
                        print(f"  ❌ {error}")
                
                if validation["warnings"]:
                    print(f"\nWarnings ({len(validation['warnings'])}):")
                    for warning in validation["warnings"]:
                        print(f"  ⚠️ {warning}")
            
            sys.exit(0 if validation["valid"] else 1)
        
        elif args.command == "setup":
            guard._ensure_testing_structure()
            validation = guard.validate_test_environment()
            
            if validation["valid"]:
                print("✅ Test environment setup complete")
                print(f"  Location: {guard.testing_root}")
            else:
                print("⚠️ Test environment setup completed with issues")
                for error in validation["errors"]:
                    print(f"  ❌ {error}")
            
            sys.exit(0 if validation["valid"] else 1)
    
    except Exception as e:
        logger.error(f"Guard operation failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()