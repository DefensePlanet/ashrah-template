#!/usr/bin/env python3
"""
Script to systematically remove lane system references from Catalyst
Replaces with unified capsule framework approach
"""
import os
import re
import glob
from pathlib import Path

def remove_lane_references():
    """Remove or replace lane-specific references throughout Catalyst"""
    
    builder_root = Path("{{CATALYST_ROOT}}")
    
    # Patterns to replace
    replacements = [
        # Basic lane references
        (r'\b(standard|standard)\b', 'standard'),
        (r'\b(standard|standard)\b', 'standard'),
        
        # Lane-specific logic patterns
        (r'lane\s*==\s*[\'"](?:standard|standard)[\'"]', 'True'),
        (r'lane\s*!=\s*[\'"](?:standard|standard)[\'"]', 'False'),
        (r'if.*lane.*==.*[\'"](?:standard|standard)[\'"]:', 'if True:'),
        
        # Configuration patterns
        (r'BUILDER_DEFAULT_LANE.*=.*[\'"](?:standard|standard)[\'"]', 'BUILDER_QUALITY_MODE="standard"'),
        (r'BUILDER_QUALITY_MODE="standard"
        
        # File path patterns
        (r'(?:standard|standard)\.md', 'quality_standards.md'),
        (r'agent-planner-(?:standard|standard)\.md', 'agent-planner.md'),
        
        # DoD references
        (r'DoD.*(?:standard|standard)', 'DoD standards'),
        (r'(?:Fast|Deep)\s+Lane\s+DoD', 'Quality Standards'),
    ]
    
    # Files to process (exclude certain directories)
    exclude_dirs = {
        'node_modules', '.git', 'backups', '.venv', 'versions',
        '__pycache__', '.pytest_cache', 'dist', 'build'
    }
    
    files_processed = 0
    replacements_made = 0
    
    # Process all text files
    for file_path in builder_root.rglob('*'):
        if file_path.is_file():
            # Skip excluded directories
            if any(part in exclude_dirs for part in file_path.parts):
                continue
                
            # Skip binary files
            if file_path.suffix in {'.pyc', '.so', '.dylib', '.png', '.jpg', '.gif', '.ico'}:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                original_content = content
                
                # Apply replacements
                for pattern, replacement in replacements:
                    content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
                
                # Write back if changed
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_processed += 1
                    print(f"Updated: {file_path.relative_to(builder_root)}")
                    
            except (UnicodeDecodeError, PermissionError) as e:
                # Skip files we can't read/write
                continue
    
    print(f"\n✅ Lane system removal complete!")
    print(f"   Files processed: {files_processed}")
    print(f"   Replacements made: {replacements_made}")

def update_templates():
    """Update capsule templates to use unified structure"""
    
    builder_root = Path("{{CATALYST_ROOT}}")
    templates_dir = builder_root / "capsules" / "builder-system" / "templates"
    
    if not templates_dir.exists():
        print(f"Templates directory not found: {templates_dir}")
        return
    
    # Update template files to remove lane references
    for template_file in templates_dir.rglob('*.yaml'):
        try:
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Replace lane references in YAML
            content = re.sub(r'lane:\s*[\'"]?(?:standard|standard)[\'"]?', 'quality_mode: standard', content)
            content = re.sub(r'lanes:\s*\[[^\]]*\]', 'quality_modes: [standard]', content)
            
            with open(template_file, 'w') as f:
                f.write(content)
                
            print(f"Updated template: {template_file.relative_to(builder_root)}")
            
        except Exception as e:
            continue
            
    print("✅ Templates updated to unified structure")

if __name__ == "__main__":
    print("🔧 Removing lane system from Catalyst...")
    remove_lane_references()
    update_templates()
    print("🎯 Lane system removal complete!")