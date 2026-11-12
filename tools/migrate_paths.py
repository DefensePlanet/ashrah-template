#!/usr/bin/env python3
"""
Comprehensive Path Migration Tool
Migrates all hardcoded {{CATALYST_ROOT}} references to {{CATALYST_ROOT}}
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

class PathMigrator:
    def __init__(self, base_path: str = "{{CATALYST_ROOT}}"):
        self.base_path = Path(base_path)
        self.old_path = "{{CATALYST_ROOT}}"
        self.new_path = "{{CATALYST_ROOT}}"
        
        # File extensions to process
        self.extensions = ['.py', '.sh', '.js', '.json', '.yaml', '.yml', '.md', '.txt']
        
        # Exclude directories
        self.exclude_dirs = {
            '__pycache__',
            '.git', 
            'node_modules',
            '.DS_Store',
            'versions'  # Don't modify version history
        }
        
        self.changes_made = 0
        self.files_processed = 0
    
    def should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        if file_path.suffix not in self.extensions:
            return False
        
        # Skip if in excluded directory
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return False
        
        return True
    
    def migrate_file(self, file_path: Path, dry_run: bool = False) -> int:
        """Migrate paths in a single file"""
        changes = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Replace various path patterns
            replacements = [
                # Direct path replacements
                (self.old_path, self.new_path),
                
                # Shell variable patterns
                (f'${{BUILDER_ROOT:-{self.old_path}}}', f'${{BUILDER_ROOT:-{self.new_path}}}'),
                (f'"${{BUILDER_ROOT:-{self.old_path}}}"', f'"${{BUILDER_ROOT:-{self.new_path}}}"'),
                
                # Python string patterns
                (f'"{self.old_path}"', f'"{self.new_path}"'),
                (f"'{self.old_path}'", f"'{self.new_path}'"),
                (f'Path("{self.old_path}")', f'Path("{self.new_path}")'),
                (f"Path('{self.old_path}')", f"Path('{self.new_path}')"),
                
                # JSON/YAML patterns
                (f'"{self.old_path}/', f'"{self.new_path}/'),
                (f"'{self.old_path}/", f"'{self.new_path}/"),
                
                # Comment patterns
                (f'# {self.old_path}', f'# {self.new_path}'),
                (f'## {self.old_path}', f'## {self.new_path}'),
            ]
            
            for old_pattern, new_pattern in replacements:
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    changes += content.count(new_pattern) - original_content.count(new_pattern)
            
            if content != original_content and not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Updated: {file_path} ({changes} changes)")
            elif content != original_content and dry_run:
                print(f"🔍 Would update: {file_path} ({changes} changes)")
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
        
        return changes
    
    def migrate_all(self, dry_run: bool = False):
        """Migrate all files in the base path"""
        print(f"{'🔍 DRY RUN - ' if dry_run else ''}Migrating paths from {self.old_path} to {self.new_path}")
        print("=" * 80)
        
        for root, dirs, files in os.walk(self.base_path):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            
            for file_name in files:
                file_path = Path(root) / file_name
                
                if self.should_process_file(file_path):
                    self.files_processed += 1
                    changes = self.migrate_file(file_path, dry_run)
                    self.changes_made += changes
        
        print("=" * 80)
        print(f"📊 Summary:")
        print(f"   Files processed: {self.files_processed}")
        print(f"   Changes made: {self.changes_made}")
        print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE MIGRATION'}")


def main():
    """Main entry point"""
    dry_run = '--dry-run' in sys.argv
    
    migrator = PathMigrator()
    migrator.migrate_all(dry_run=dry_run)
    
    if dry_run:
        print("\n🔧 To apply changes, run: python3 tools/migrate_paths.py")
    else:
        print("\n✅ Path migration completed!")
        print("💡 Remember to restart your shell: source ~/.zshrc")


if __name__ == '__main__':
    main()