#!/usr/bin/env python3
"""
Fix hardcoded paths throughout Catalyst
Replaces absolute paths with environment-aware configuration
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    # Import using importlib to avoid 'global' keyword issue
    import importlib.util
    spec = importlib.util.spec_from_file_location("paths_config", parent_dir / "global" / "config" / "paths.py")
    paths_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paths_module)
    paths = paths_module.paths
    config = paths_module.config
except Exception as e:
    print(f"Error: Could not import paths config: {e}")
    sys.exit(1)

def find_files_with_hardcoded_paths(base_path: Path) -> List[Path]:
    """Find files containing hardcoded Builder paths"""
    hardcoded_pattern = rstr(paths.base)
    files_to_fix = []
    
    # File extensions to check
    extensions = {'.py', '.sh', '.yaml', '.yml', '.json', '.md', '.log', '.jsonl'}
    
    for file_path in base_path.rglob('*'):
        if not file_path.is_file():
            continue
            
        # Skip binary files and virtual environments
        if any(skip in str(file_path) for skip in ['.venv', '__pycache__', '.git', 'node_modules']):
            continue
            
        # Check extension
        if file_path.suffix not in extensions:
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if hardcoded_pattern in content:
                    files_to_fix.append(file_path)
        except Exception:
            continue
    
    return files_to_fix

def get_replacement_patterns() -> List[Tuple[str, str, str]]:
    """Get patterns for replacing hardcoded paths"""
    builder_root = str(paths.base)
    
    return [
        # Python files - use paths module
        (r'str(paths.base)', 'str(paths.base)', '.py'),
        (r"str(paths.base)", 'str(paths.base)', '.py'),
        (r'str(paths.rag)', 'str(paths.rag)', '.py'),
        (r'str(paths.capsules)', 'str(paths.capsules)', '.py'),
        (r'str(paths.registry)', 'str(paths.registry)', '.py'),
        (r'str(paths.tools)', 'str(paths.tools)', '.py'),
        (r'str(paths.config)', 'str(paths.config)', '.py'),
        
        # Shell scripts - use environment variable
        (rstr(paths.base), '${BUILDER_ROOT:-' + builder_root + '}', '.sh'),
        
        # Config files - use environment variable syntax
        (rstr(paths.base), builder_root, '.json'),
        (rstr(paths.base), builder_root, '.yaml'),
        (rstr(paths.base), builder_root, '.yml'),
    ]

def fix_file(file_path: Path, patterns: List[Tuple[str, str, str]]) -> Dict[str, any]:
    """Fix hardcoded paths in a file"""
    result = {
        'path': str(file_path),
        'changes_made': 0,
        'backup_created': False,
        'error': None
    }
    
    try:
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        changes = 0
        
        # Apply relevant patterns
        for pattern, replacement, extension in patterns:
            if file_path.suffix == extension:
                new_content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    content = new_content
                    changes += count
        
        # If changes were made, create backup and write new content
        if changes > 0:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            result['backup_created'] = True
            
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            result['changes_made'] = changes
            
    except Exception as e:
        result['error'] = str(e)
    
    return result

def add_import_to_python_files(files: List[Path]) -> None:
    """Add paths import to Python files that need it"""
    import_line = "from global.config.paths import paths, config"
    
    for file_path in files:
        if file_path.suffix != '.py':
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file uses paths module
            if 'str(paths.' in content and import_line not in content:
                lines = content.split('\n')
                
                # Find where to insert import (after existing imports)
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        insert_index = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                
                # Insert the import
                lines.insert(insert_index, import_line)
                
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                    
                print(f"Added paths import to {file_path}")
                
        except Exception as e:
            print(f"Error adding import to {file_path}: {e}")

def create_environment_setup() -> None:
    """Create environment setup script"""
    env_script = paths.tools / "setup_environment.sh"
    
    content = f"""#!/bin/bash
# Catalyst Environment Setup
# Run this script to set up environment variables for portability

export BUILDER_ROOT="{paths.base}"
export BUILDER_RAG_HOST="{config.RAG_HOST}"
export BUILDER_RAG_PORT="{config.RAG_PORT}"
export BUILDER_LOG_LEVEL="{config.LOG_LEVEL}"
export BUILDER_DEFAULT_LANE="{config.DEFAULT_LANE}"

# Optional: Add to your shell profile
# echo 'export BUILDER_ROOT="{paths.base}"' >> ~/.bashrc
# echo 'export BUILDER_ROOT="{paths.base}"' >> ~/.zshrc

echo "Catalyst environment configured:"
echo "  BUILDER_ROOT: $BUILDER_ROOT"
echo "  RAG Service: $BUILDER_RAG_HOST:$BUILDER_RAG_PORT"
echo "  Log Level: $BUILDER_LOG_LEVEL"
"""
    
    with open(env_script, 'w') as f:
        f.write(content)
    
    # Make executable
    os.chmod(env_script, 0o755)
    print(f"Created environment setup script: {env_script}")

def main():
    """Main function to fix hardcoded paths"""
    print("Catalyst: Fixing hardcoded paths...")
    
    # Find files with hardcoded paths
    print("Scanning for files with hardcoded paths...")
    files_to_fix = find_files_with_hardcoded_paths(paths.base)
    
    print(f"Found {len(files_to_fix)} files with hardcoded paths")
    
    # Get replacement patterns
    patterns = get_replacement_patterns()
    
    # Fix each file
    results = []
    for file_path in files_to_fix:
        result = fix_file(file_path, patterns)
        results.append(result)
        
        if result['error']:
            print(f"ERROR fixing {file_path}: {result['error']}")
        elif result['changes_made'] > 0:
            print(f"Fixed {result['changes_made']} paths in {file_path}")
    
    # Add imports to Python files
    python_files = [f for f in files_to_fix if f.suffix == '.py']
    if python_files:
        print("Adding path imports to Python files...")
        add_import_to_python_files(python_files)
    
    # Create environment setup script
    create_environment_setup()
    
    # Summary
    total_changes = sum(r['changes_made'] for r in results)
    files_changed = len([r for r in results if r['changes_made'] > 0])
    
    print(f"\\nSummary:")
    print(f"  Files processed: {len(files_to_fix)}")
    print(f"  Files changed: {files_changed}")
    print(f"  Total replacements: {total_changes}")
    print(f"\\nTo complete the setup:")
    print(f"  1. Run: source {paths.tools}/setup_environment.sh")
    print(f"  2. Test RAG service: cd {paths.rag_service} && python rag_service.py")

if __name__ == '__main__':
    main()