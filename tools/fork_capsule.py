#!/usr/bin/env python3
"""
Capsule Fork Tool - Clone capsule to new slug for iterating on successful patterns
Preserves runs/ index and resets ops/, enabling rapid iteration from known-good states
"""

import os
import sys
import json
import shutil
import pathlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import re

# Add Builder tools to path
BUILDER_ROOT = pathlib.Path.home() / "Documents" / "Builder"
sys.path.append(str(BUILDER_ROOT / "tools"))

try:
    from events_logger import log_event
    from run_manifest_schema import RunManifest
except ImportError as e:
    print(f"Warning: Could not import Builder tools: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CapsuleForkManager:
    """Manages capsule forking for rapid iteration"""
    
    def __init__(self):
        self.builder_root = BUILDER_ROOT
        self.capsules_dir = self.builder_root / "capsules"
        
    def fork_capsule(self, source_capsule: str, new_name: str,
                    preserve_runs: bool = True, 
                    reset_ops: bool = True,
                    copy_latest_run: bool = False,
                    modifications: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fork a capsule to create a new iteration point"""
        
        logger.info(f"Forking capsule {source_capsule} -> {new_name}")
        
        fork_results = {
            "source_capsule": source_capsule,
            "new_capsule": new_name,
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "preserved_runs": 0,
            "copied_files": 0,
            "modifications_applied": [],
            "errors": []
        }
        
        try:
            # Validate inputs
            if not self._validate_fork_request(source_capsule, new_name):
                raise ValueError("Invalid fork request")
            
            # Create new capsule directory
            source_dir = self.capsules_dir / source_capsule
            target_dir = self.capsules_dir / new_name
            
            if target_dir.exists():
                raise ValueError(f"Target capsule {new_name} already exists")
            
            # Copy capsule structure
            self._copy_capsule_structure(source_dir, target_dir, 
                                       preserve_runs, reset_ops, copy_latest_run)
            
            # Update capsule metadata
            self._update_capsule_metadata(target_dir, source_capsule, new_name)
            
            # Apply modifications if provided
            if modifications:
                applied_mods = self._apply_fork_modifications(target_dir, modifications)
                fork_results["modifications_applied"] = applied_mods
            
            # Count results
            fork_results["preserved_runs"] = self._count_preserved_runs(target_dir)
            fork_results["copied_files"] = self._count_files(target_dir)
            
            # Log fork event
            self._log_fork_event(source_capsule, new_name, fork_results)
            
            fork_results["success"] = True
            logger.info(f"Fork completed successfully: {new_name}")
            
        except Exception as e:
            logger.error(f"Fork failed: {e}")
            fork_results["errors"].append(str(e))
            
            # Clean up on failure
            target_dir = self.capsules_dir / new_name
            if target_dir.exists():
                try:
                    shutil.rmtree(target_dir)
                except:
                    pass
        
        return fork_results
    
    def list_forkable_capsules(self) -> List[Dict[str, Any]]:
        """List capsules that can be forked"""
        forkable = []
        
        if not self.capsules_dir.exists():
            return forkable
        
        for capsule_dir in self.capsules_dir.iterdir():
            if capsule_dir.is_dir() and not capsule_dir.name.startswith('.'):
                info = self._get_capsule_info(capsule_dir)
                if info:
                    forkable.append(info)
        
        # Sort by most recent activity
        forkable.sort(key=lambda x: x.get("last_run", ""), reverse=True)
        return forkable
    
    def suggest_fork_name(self, source_capsule: str, purpose: str = None) -> str:
        """Suggest a fork name based on source and purpose"""
        base_name = source_capsule
        
        # Add purpose suffix if provided
        if purpose:
            # Clean purpose string
            clean_purpose = re.sub(r'[^a-zA-Z0-9]+', '-', purpose.lower()).strip('-')
            base_name = f"{source_capsule}-{clean_purpose}"
        else:
            # Default to date-based suffix
            base_name = f"{source_capsule}-fork-{datetime.now().strftime('%m%d')}"
        
        # Ensure uniqueness
        counter = 1
        suggested_name = base_name
        
        while (self.capsules_dir / suggested_name).exists():
            suggested_name = f"{base_name}-{counter}"
            counter += 1
        
        return suggested_name
    
    def _validate_fork_request(self, source_capsule: str, new_name: str) -> bool:
        """Validate fork request parameters"""
        
        # Check source exists
        source_dir = self.capsules_dir / source_capsule
        if not source_dir.exists():
            raise ValueError(f"Source capsule {source_capsule} does not exist")
        
        if not source_dir.is_dir():
            raise ValueError(f"Source capsule {source_capsule} is not a directory")
        
        # Validate new name
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-_]*$', new_name):
            raise ValueError(f"Invalid capsule name: {new_name}")
        
        if len(new_name) > 50:
            raise ValueError(f"Capsule name too long: {new_name}")
        
        # Check target doesn't exist
        target_dir = self.capsules_dir / new_name
        if target_dir.exists():
            raise ValueError(f"Target capsule {new_name} already exists")
        
        return True
    
    def _copy_capsule_structure(self, source_dir: pathlib.Path, target_dir: pathlib.Path,
                              preserve_runs: bool, reset_ops: bool, copy_latest_run: bool):
        """Copy capsule structure with selective preservation/reset"""
        
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all files and directories, with special handling
        for item in source_dir.iterdir():
            if item.is_file():
                # Copy all files at root level
                shutil.copy2(item, target_dir / item.name)
                
            elif item.is_dir():
                if item.name == "runs" and preserve_runs:
                    # Preserve runs directory
                    if copy_latest_run:
                        self._copy_latest_run_only(item, target_dir / "runs")
                    else:
                        shutil.copytree(item, target_dir / item.name)
                        
                elif item.name == "ops" and reset_ops:
                    # Reset ops directory - create empty structure
                    ops_dir = target_dir / "ops"
                    ops_dir.mkdir(exist_ok=True)
                    
                    # Create empty subdirectories if they existed
                    for sub_item in item.iterdir():
                        if sub_item.is_dir():
                            (ops_dir / sub_item.name).mkdir(exist_ok=True)
                            
                elif item.name in [".git", "__pycache__", "node_modules"]:
                    # Skip these directories
                    continue
                    
                else:
                    # Copy other directories normally
                    shutil.copytree(item, target_dir / item.name)
    
    def _copy_latest_run_only(self, runs_dir: pathlib.Path, target_runs_dir: pathlib.Path):
        """Copy only the latest run instead of all runs"""
        target_runs_dir.mkdir(exist_ok=True)
        
        # Find latest run
        latest_run = None
        latest_time = None
        
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir():
                manifest_file = run_dir / "manifest.json"
                if manifest_file.exists():
                    try:
                        manifest = RunManifest.load(manifest_file)
                        run_time = datetime.fromisoformat(manifest.start_time)
                        
                        if latest_time is None or run_time > latest_time:
                            latest_time = run_time
                            latest_run = run_dir
                    except:
                        continue
        
        # Copy latest run if found
        if latest_run:
            shutil.copytree(latest_run, target_runs_dir / latest_run.name)
            logger.info(f"Copied latest run: {latest_run.name}")
    
    def _update_capsule_metadata(self, target_dir: pathlib.Path, 
                               source_capsule: str, new_name: str):
        """Update capsule metadata files for the fork"""
        
        # Update capsule.json
        capsule_json = target_dir / "capsule.json"
        if capsule_json.exists():
            try:
                with open(capsule_json, 'r') as f:
                    capsule_data = json.load(f)
                
                # Update metadata
                capsule_data["name"] = new_name
                capsule_data["forked_from"] = source_capsule
                capsule_data["forked_at"] = datetime.now().isoformat()
                
                # Update version
                current_version = capsule_data.get("version", "1.0")
                if current_version.count('.') >= 1:
                    major, minor = current_version.split('.')[:2]
                    capsule_data["version"] = f"{major}.{int(minor) + 1}"
                else:
                    capsule_data["version"] = "1.1"
                
                with open(capsule_json, 'w') as f:
                    json.dump(capsule_data, f, indent=2)
                    
            except Exception as e:
                logger.warning(f"Could not update capsule.json: {e}")
        
        # Update requirements.yaml
        req_file = target_dir / "spec" / "requirements.yaml"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    content = f.read()
                
                # Update name references
                content = content.replace(source_capsule, new_name)
                
                # Add fork metadata
                content += f"\n# Forked from: {source_capsule}\n"
                content += f"# Forked at: {datetime.now().isoformat()}\n"
                
                with open(req_file, 'w') as f:
                    f.write(content)
                    
            except Exception as e:
                logger.warning(f"Could not update requirements.yaml: {e}")
    
    def _apply_fork_modifications(self, target_dir: pathlib.Path, 
                                modifications: Dict[str, Any]) -> List[str]:
        """Apply modifications to the forked capsule"""
        applied = []
        
        # Modify capsule.json
        if "capsule_json" in modifications:
            capsule_json = target_dir / "capsule.json"
            if capsule_json.exists():
                try:
                    with open(capsule_json, 'r') as f:
                        capsule_data = json.load(f)
                    
                    capsule_data.update(modifications["capsule_json"])
                    
                    with open(capsule_json, 'w') as f:
                        json.dump(capsule_data, f, indent=2)
                    
                    applied.append("Updated capsule.json")
                except Exception as e:
                    logger.warning(f"Failed to modify capsule.json: {e}")
        
        # Modify requirements.yaml
        if "requirements" in modifications:
            req_file = target_dir / "spec" / "requirements.yaml"
            if req_file.exists():
                try:
                    with open(req_file, 'r') as f:
                        content = f.read()
                    
                    # Apply string replacements
                    for old_text, new_text in modifications["requirements"].items():
                        content = content.replace(old_text, new_text)
                    
                    with open(req_file, 'w') as f:
                        f.write(content)
                    
                    applied.append("Updated requirements.yaml")
                except Exception as e:
                    logger.warning(f"Failed to modify requirements.yaml: {e}")
        
        # Add/modify files
        if "files" in modifications:
            for file_path, file_content in modifications["files"].items():
                try:
                    full_path = target_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_path, 'w') as f:
                        f.write(file_content)
                    
                    applied.append(f"Created/modified {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to modify {file_path}: {e}")
        
        return applied
    
    def _get_capsule_info(self, capsule_dir: pathlib.Path) -> Optional[Dict[str, Any]]:
        """Get information about a capsule for listing"""
        try:
            info = {
                "name": capsule_dir.name,
                "path": str(capsule_dir),
                "last_run": None,
                "run_count": 0,
                "description": None,
                "forkable": True
            }
            
            # Get capsule metadata
            capsule_json = capsule_dir / "capsule.json"
            if capsule_json.exists():
                with open(capsule_json, 'r') as f:
                    capsule_data = json.load(f)
                    info["description"] = capsule_data.get("description")
            
            # Get run information
            runs_dir = capsule_dir / "runs"
            if runs_dir.exists():
                run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
                info["run_count"] = len(run_dirs)
                
                # Find latest run
                latest_time = None
                for run_dir in run_dirs:
                    manifest_file = run_dir / "manifest.json"
                    if manifest_file.exists():
                        try:
                            manifest = RunManifest.load(manifest_file)
                            run_time = datetime.fromisoformat(manifest.start_time)
                            if latest_time is None or run_time > latest_time:
                                latest_time = run_time
                                info["last_run"] = manifest.start_time
                        except:
                            continue
            
            return info
            
        except Exception as e:
            logger.warning(f"Could not get info for {capsule_dir}: {e}")
            return None
    
    def _count_preserved_runs(self, target_dir: pathlib.Path) -> int:
        """Count preserved runs in target directory"""
        runs_dir = target_dir / "runs"
        if runs_dir.exists():
            return len([d for d in runs_dir.iterdir() if d.is_dir()])
        return 0
    
    def _count_files(self, target_dir: pathlib.Path) -> int:
        """Count total files in target directory"""
        total = 0
        for root, dirs, files in os.walk(target_dir):
            total += len(files)
        return total
    
    def _log_fork_event(self, source_capsule: str, new_name: str, results: Dict[str, Any]):
        """Log fork event to Builder registry"""
        try:
            log_event(
                stage="capsule_fork",
                level="INFO" if results["success"] else "ERROR",
                message=f"Capsule forked: {source_capsule} -> {new_name}",
                capsule=new_name,
                data={
                    "source_capsule": source_capsule,
                    "preserved_runs": results["preserved_runs"],
                    "copied_files": results["copied_files"],
                    "success": results["success"]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log fork event: {e}")

def main():
    """CLI interface for capsule fork tool"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Capsule Fork Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List forkable capsules")
    
    # Fork command
    fork_parser = subparsers.add_parser("fork", help="Fork a capsule")
    fork_parser.add_argument("source_capsule", help="Source capsule name")
    fork_parser.add_argument("new_name", nargs='?', help="New capsule name (auto-generated if not provided)")
    fork_parser.add_argument("--purpose", help="Purpose of the fork (used for naming)")
    fork_parser.add_argument("--no-runs", action="store_true", help="Don't preserve runs")
    fork_parser.add_argument("--keep-ops", action="store_true", help="Don't reset ops directory")
    fork_parser.add_argument("--latest-run-only", action="store_true", help="Copy only the latest run")
    fork_parser.add_argument("--lane", help="Set lane for forked capsule")
    fork_parser.add_argument("--description", help="Set description for forked capsule")
    
    # Suggest command
    suggest_parser = subparsers.add_parser("suggest", help="Suggest fork name")
    suggest_parser.add_argument("source_capsule", help="Source capsule name")
    suggest_parser.add_argument("--purpose", help="Purpose of the fork")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    manager = CapsuleForkManager()
    
    try:
        if args.command == "list":
            capsules = manager.list_forkable_capsules()
            
            if not capsules:
                print("No forkable capsules found")
            else:
                print("Forkable Capsules:")
                print("=" * 80)
                for capsule in capsules:
                    runs_info = f"{capsule['run_count']} runs" if capsule['run_count'] > 0 else "No runs"
                    last_run = capsule['last_run'][:10] if capsule['last_run'] else "Never"
                    description = capsule['description'] or "No description"
                    
                    print(f"    {description}")
                    print(f"    {runs_info} | Last run: {last_run}")
                    print()
        
        elif args.command == "suggest":
            suggested_name = manager.suggest_fork_name(args.source_capsule, args.purpose)
            print(suggested_name)
        
        elif args.command == "fork":
            # Determine new name
            if args.new_name:
                new_name = args.new_name
            else:
                new_name = manager.suggest_fork_name(args.source_capsule, args.purpose)
            
            # Prepare modifications
            modifications = {}
            
            if args.lane or args.description:
                capsule_mods = {}
                if args.lane:
                if args.description:
                    capsule_mods["description"] = args.description
                modifications["capsule_json"] = capsule_mods
            
            # Execute fork
            results = manager.fork_capsule(
                source_capsule=args.source_capsule,
                new_name=new_name,
                preserve_runs=not args.no_runs,
                reset_ops=not args.keep_ops,
                copy_latest_run=args.latest_run_only,
                modifications=modifications if modifications else None
            )
            
            print(f"🍴 Fork Results: {args.source_capsule} -> {new_name}")
            print("=" * 60)
            
            if results["success"]:
                print("✅ Fork completed successfully!")
                print(f"New capsule: {new_name}")
                print(f"Preserved runs: {results['preserved_runs']}")
                print(f"Total files: {results['copied_files']}")
                
                if results["modifications_applied"]:
                    print(f"Modifications applied:")
                    for mod in results["modifications_applied"]:
                        print(f"  - {mod}")
                        
                print(f"\n📁 Location: {manager.capsules_dir / new_name}")
            else:
                print("❌ Fork failed!")
                if results["errors"]:
                    for error in results["errors"]:
                        print(f"  Error: {error}")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()