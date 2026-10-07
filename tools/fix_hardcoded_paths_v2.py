#!/usr/bin/env python3
"""
Fix hardcoded paths throughout Catalyst - Version 2
Replaces absolute paths with environment-aware configuration
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Add common utilities to path
sys.path.insert(0, os.path.dirname(__file__))
from common.builder_utils import (
    BUILDER_ROOT, logger, PathValidator, 
    BuilderSecurityError, BuilderValidationError
)

class PathFixer:
    """Fix hardcoded paths in Builder system"""
    
    def __init__(self):
        self.validator = PathValidator()
        self.builder_root = BUILDER_ROOT
        self.fixed_files = []
        self.errors = []
    
    def find_files_with_hardcoded_paths(self) -> List[Path]:
        """Find files containing hardcoded Builder paths"""
        files_to_fix = []
        
        # Patterns to search for
        hardcoded_patterns = [
            r'{{CATALYST_ROOT}}',
            r'/home/ty/Builder',
            r'~/Documents/Builder',
            r'Documents/Builder',
        ]
        
        # File extensions to check
        extensions = {'.py', '.sh', '.yaml', '.yml', '.json', '.md'}
        
        # Directories to search
        search_dirs = ['tools', 'capsules', 'global', 'templates']
        
        for dir_name in search_dirs:
            search_path = Path(self.builder_root) / dir_name
            if not search_path.exists():
                continue
            
            for file_path in search_path.rglob('*'):
                if not file_path.is_file():
                    continue
                
                # Skip files we shouldn't modify
                skip_patterns = [
                    '__pycache__', '.git', 'node_modules', '.venv',
                    '.backup', '.bak', 'fix_hardcoded_paths_v2.py'
                ]
                if any(skip in str(file_path) for skip in skip_patterns):
                    continue
                
                # Check extension
                if file_path.suffix not in extensions:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for pattern in hardcoded_patterns:
                            if re.search(pattern, content):
                                files_to_fix.append(file_path)
                                break
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
        
        return files_to_fix
    
    def get_replacement_for_file(self, file_path: Path) -> List[Tuple[str, str]]:
        """Get replacement patterns based on file type"""
        replacements = []
        
        if file_path.suffix == '.py':
            # Python files - use os.environ.get
            replacements = [
                (r'{{CATALYST_ROOT}}', "os.environ.get('BUILDER_ROOT', '{{CATALYST_ROOT}}')"),
                (r'"/home/ty/Builder"', "os.environ.get('BUILDER_ROOT', '{{CATALYST_ROOT}}')"),
                (r"'/home/ty/Builder'", "os.environ.get('BUILDER_ROOT', '{{CATALYST_ROOT}}')"),
            ]
        elif file_path.suffix == '.sh':
            # Shell scripts - use ${BUILDER_ROOT:-default}
            replacements = [
                (r'{{CATALYST_ROOT}}', '${BUILDER_ROOT:-{{CATALYST_ROOT}}}'),
                (r'/home/ty/Builder', '${BUILDER_ROOT:-{{CATALYST_ROOT}}}'),
                (r'~/Documents/Builder', '${BUILDER_ROOT:-{{CATALYST_ROOT}}}'),
                (r'Documents/Builder', '${BUILDER_ROOT:-{{CATALYST_ROOT}}}'),
            ]
        elif file_path.suffix in ['.yaml', '.yml', '.json']:
            # Config files - keep as is but standardize
            replacements = [
                (r'/home/ty/Builder', '{{CATALYST_ROOT}}'),
                (r'~/Documents/Builder', '{{CATALYST_ROOT}}'),
                (r'Documents/Builder', '{{CATALYST_ROOT}}'),
            ]
        
        return replacements
    
    def fix_file(self, file_path: Path) -> Dict[str, any]:
        """Fix hardcoded paths in a single file"""
        result = {
            'path': str(file_path),
            'changes_made': 0,
            'backup_created': False,
            'error': None
        }
        
        try:
            # Validate path
            self.validator.validate_path(str(file_path), f"File {file_path.name}")
            
            # Read original content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            total_changes = 0
            
            # Get replacements for this file type
            replacements = self.get_replacement_for_file(file_path)
            
            # Apply replacements
            for pattern, replacement in replacements:
                new_content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    content = new_content
                    total_changes += count
            
            # If changes were made, create backup and write new content
            if total_changes > 0:
                # Create backup
                backup_path = file_path.with_suffix(file_path.suffix + '.bak')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                result['backup_created'] = True
                
                # Write updated content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                result['changes_made'] = total_changes
                self.fixed_files.append(file_path)
                logger.info(f"Fixed {total_changes} paths in {file_path}")
            
        except Exception as e:
            result['error'] = str(e)
            self.errors.append((file_path, str(e)))
            logger.error(f"Error fixing {file_path}: {e}")
        
        return result
    
    def ensure_python_imports(self, file_path: Path) -> None:
        """Ensure Python files have necessary imports for BUILDER_ROOT"""
        if file_path.suffix != '.py':
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if file now uses os.environ
            if "os.environ.get('BUILDER_ROOT'" in content:
                # Check if os is imported
                if 'import os' not in content:
                    lines = content.split('\n')
                    
                    # Find where to insert import
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if line.strip().startswith('#!'):
                            insert_index = i + 1
                        elif line.strip().startswith('"""'):
                            # Skip docstring
                            for j in range(i + 1, len(lines)):
                                if '"""' in lines[j]:
                                    insert_index = j + 1
                                    break
                            break
                        elif line.strip() and not line.strip().startswith('#'):
                            insert_index = i
                            break
                    
                    # Insert import
                    lines.insert(insert_index, 'import os')
                    
                    # Write back
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                    
                    logger.info(f"Added 'import os' to {file_path}")
        
        except Exception as e:
            logger.warning(f"Could not add import to {file_path}: {e}")
    
    def create_environment_script(self) -> None:
        """Create environment setup script"""
        script_path = Path(self.builder_root) / 'tools' / 'setup_builder_env.sh'
        
        content = """#!/bin/bash
# Catalyst Environment Setup
# Source this script to set up environment variables

export BUILDER_ROOT="${BUILDER_ROOT:-{{CATALYST_ROOT}}}"
export BUILDER_HOME="${HOME:-{{HOME_DIR}}}"

# Validate BUILDER_ROOT exists
if [ ! -d "$BUILDER_ROOT" ]; then
    echo "ERROR: BUILDER_ROOT directory does not exist: $BUILDER_ROOT" >&2
    return 1
fi

# Add tools to PATH
export PATH="$BUILDER_ROOT/tools:$PATH"

echo "Builder environment configured:"
echo "  BUILDER_ROOT: $BUILDER_ROOT"
echo "  BUILDER_HOME: $BUILDER_HOME"
echo ""
echo "To make permanent, add to your shell profile:"
echo "  echo 'export BUILDER_ROOT=\"$BUILDER_ROOT\"' >> ~/.zshrc"
echo "  echo 'source $BUILDER_ROOT/tools/setup_builder_env.sh' >> ~/.zshrc"
"""
        
        with open(script_path, 'w') as f:
            f.write(content)
        
        # Make executable
        os.chmod(script_path, 0o755)
        logger.info(f"Created environment script: {script_path}")
    
    def run(self) -> None:
        """Run the path fixing process"""
        logger.info("Starting hardcoded path fix process...")
        
        # Find files with hardcoded paths
        files_to_fix = self.find_files_with_hardcoded_paths()
        logger.info(f"Found {len(files_to_fix)} files with hardcoded paths")
        
        # Fix each file
        for file_path in files_to_fix:
            result = self.fix_file(file_path)
            
            # Ensure Python files have necessary imports
            if result['changes_made'] > 0:
                self.ensure_python_imports(file_path)
        
        # Create environment setup script
        self.create_environment_script()
        
        # Print summary
        print("\n" + "="*60)
        print("PATH FIX SUMMARY")
        print("="*60)
        print(f"Files scanned: {len(files_to_fix)}")
        print(f"Files fixed: {len(self.fixed_files)}")
        print(f"Errors: {len(self.errors)}")
        
        if self.fixed_files:
            print("\nFixed files:")
            for f in self.fixed_files[:10]:
                print(f"  - {f.relative_to(self.builder_root)}")
            if len(self.fixed_files) > 10:
                print(f"  ... and {len(self.fixed_files) - 10} more")
        
        if self.errors:
            print("\nErrors encountered:")
            for file_path, error in self.errors[:5]:
                print(f"  - {file_path.name}: {error}")
        
        print("\nNext steps:")
        print("1. Review the changes (backup files created with .bak extension)")
        print("2. Source the environment script:")
        print(f"   source {self.builder_root}/tools/setup_builder_env.sh")
        print("3. Test the system with the new paths")
        print("4. Remove .bak files once confirmed working:")
        print(f"   find {self.builder_root} -name '*.bak' -type f -delete")


def main():
    """Main entry point"""
    fixer = PathFixer()
    try:
        fixer.run()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()