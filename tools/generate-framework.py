#!/usr/bin/env python3
"""
Framework Generator for Catalyst Capsules
Generates the complete framework structure (standards.yaml, product.yaml, specs/, context/)
"""

import os
import sys
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import argparse
from typing import Dict, Any, Optional
import re

class FrameworkGenerator:
    def __init__(self, builderOS_root: str):
        self.builderOS_root = Path(builderOS_root)
        self.templates_dir = self.builderOS_root / "recipes/framework-templates"
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        
    def load_capsule_config(self, capsule_path: Path) -> Dict[str, Any]:
        """Load capsule.map.json configuration"""
        config_file = capsule_path / "capsule.map.json"
        if not config_file.exists():
            raise FileNotFoundError(f"No capsule.map.json found in {capsule_path}")
            
        try:
            with open(config_file, 'r') as f:
                content = f.read().strip()
                # Remove any trailing content after the JSON
                if content.endswith('EOF < /dev/null'):
                    content = content.split('EOF < /dev/null')[0].strip()
                return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in {config_file}, using defaults")
            return {}
    
    def get_template_placeholders(self, capsule_name: str, capsule_slug: str) -> Dict[str, str]:
        """Generate placeholders for template substitution"""
        # Calculate quarter dates
        now = datetime.now()
        next_quarter = now + timedelta(days=90)
        quarter_after_next = now + timedelta(days=180)
        next_year = now + timedelta(days=365)
        
        return {
            # Basic info
            "CAPSULE_NAME": capsule_name,
            "CAPSULE_SLUG": capsule_slug,
            "CURRENT_DATE": self.current_date,
            
            # Dates
            "TARGET_DATE": next_quarter.strftime("%Y-%m-%d"),
            "NEXT_QUARTER": f"Q{((next_quarter.month-1)//3)+1} {next_quarter.year}",
            "QUARTER_AFTER_NEXT": f"Q{((quarter_after_next.month-1)//3)+1} {quarter_after_next.year}",
            "NEXT_YEAR": str(next_year.year),
            
            # Defaults that can be customized
            "LANE_TYPE": "standard",
            "ARCHITECTURE_TYPE": "modular_monolith",
            "AUTH_METHOD": "JWT",
            "SESSION_TIMEOUT": "24h",
            "CONTENT_TYPE": "application/json",
            "ERROR_FORMAT": "rfc7807",
            "ENCRYPTION_STANDARD": "AES-256",
            "SECRETS_METHOD": "environment_variables",
            "DATA_PROTECTION_METHOD": "encrypted_at_rest",
            "COMMUNICATION_SECURITY": "tls_1.3",
            "RESPONSE_TIME_TARGET": "<2s",
            "THROUGHPUT_TARGET": "1000 requests/minute",
            "CONCURRENT_USERS_TARGET": "100+",
            "UPTIME_TARGET": "99.9%",
            "AUTH_RATE_LIMIT": "1000/hour",
            "UNAUTH_RATE_LIMIT": "100/hour",
            
            # Template placeholders that need customization
            "CAPSULE_DESCRIPTION": f"TODO: Describe {capsule_name} purpose and functionality",
            "PRODUCT_VISION": f"TODO: Define vision for {capsule_name}",
            "PRODUCT_MISSION": f"TODO: Define mission for {capsule_name}",
            "PRIMARY_MARKET": "TODO: Define primary market",
            "SECONDARY_MARKET": "TODO: Define secondary market",
            "ENTERPRISE_MARKET": "TODO: Define enterprise market",
            "ENGAGEMENT_TARGET": "TODO: Define engagement target",
            "EFFICIENCY_TARGET": "TODO: Define efficiency target", 
            "QUALITY_TARGET": "TODO: Define quality target",
            "BUSINESS_TARGET": "TODO: Define business target",
            "MOAT_1": "TODO: Define competitive advantage 1",
            "MOAT_2": "TODO: Define competitive advantage 2",
            "MOAT_3": "TODO: Define competitive advantage 3",
        }
    
    def substitute_template(self, template_content: str, placeholders: Dict[str, str]) -> str:
        """Substitute template placeholders with actual values using multiple patterns"""
        result = template_content
        
        # Pattern 1: {{ KEY }} (spaces)
        for key, value in placeholders.items():
            result = result.replace(f"{{{{ {key} }}}}", value)
        
        # Pattern 2: {{KEY}} (no spaces)
        for key, value in placeholders.items():
            result = result.replace(f"{{{{{key}}}}}", value)
        
        # Pattern 3: ${KEY} (shell-style)
        for key, value in placeholders.items():
            result = result.replace(f"${{{key}}}", value)
            result = result.replace(f"${key}", value)
        
        # Pattern 4: %KEY% (Windows-style)
        for key, value in placeholders.items():
            result = result.replace(f"%{key}%", value)
        
        return result
    
    def collect_interactive_placeholders(self, base_placeholders: Dict[str, str]) -> Dict[str, str]:
        """Collect placeholder values interactively for TODO items"""
        placeholders = base_placeholders.copy()
        
        print("\n🔧 Template Variable Configuration")
        print("=" * 50)
        print("Enter values for template variables (press Enter to keep defaults):\n")
        
        # Interactive prompts for TODO items
        todo_fields = {
            "CAPSULE_DESCRIPTION": "Brief description of what this capsule does",
            "PRODUCT_VISION": "Long-term vision for this product",
            "PRODUCT_MISSION": "Core mission statement", 
            "PRIMARY_MARKET": "Primary target market/users",
            "SECONDARY_MARKET": "Secondary target market/users",
            "ENTERPRISE_MARKET": "Enterprise market segment",
            "ENGAGEMENT_TARGET": "User engagement target/metric",
            "EFFICIENCY_TARGET": "Operational efficiency target",
            "QUALITY_TARGET": "Quality metric target",
            "BUSINESS_TARGET": "Key business metric target",
            "MOAT_1": "First competitive advantage",
            "MOAT_2": "Second competitive advantage", 
            "MOAT_3": "Third competitive advantage"
        }
        
        for key, prompt in todo_fields.items():
            current_value = placeholders.get(key, "")
            if current_value.startswith("TODO:"):
                user_input = input(f"{prompt}: ").strip()
                if user_input:
                    placeholders[key] = user_input
        
        # Architecture and technical choices
        print("\n⚙️ Technical Configuration")
        print("-" * 30)
        
        arch_choices = ["modular_monolith", "microservices", "layered", "event_driven", "serverless"]
        current_arch = placeholders.get("ARCHITECTURE_TYPE", "modular_monolith")
        print(f"Architecture pattern [{current_arch}]: {', '.join(arch_choices)}")
        arch_input = input("Architecture type: ").strip()
        if arch_input and arch_input in arch_choices:
            placeholders["ARCHITECTURE_TYPE"] = arch_input
        
        auth_choices = ["JWT", "OAuth2", "session", "API_key", "basic_auth"]
        current_auth = placeholders.get("AUTH_METHOD", "JWT")
        print(f"Authentication [{current_auth}]: {', '.join(auth_choices)}")
        auth_input = input("Auth method: ").strip()
        if auth_input and auth_input in auth_choices:
            placeholders["AUTH_METHOD"] = auth_input
        
        return placeholders
    
    def generate_framework_files(self, capsule_path: Path, placeholders: Dict[str, str]):
        """Generate all framework files for a capsule"""
        
        # Ensure directories exist
        (capsule_path / "specs" / "versions").mkdir(parents=True, exist_ok=True)
        (capsule_path / "context").mkdir(parents=True, exist_ok=True)
        
        # Template mappings
        templates = {
            "standards.yaml.template": capsule_path / "standards.yaml",
            "product.yaml.template": capsule_path / "product.yaml", 
            "specs-current.yaml.template": capsule_path / "specs" / "current.yaml",
            "specs-next.yaml.template": capsule_path / "specs" / "next.yaml",
            "context-decisions.md.template": capsule_path / "context" / "decisions.md",
            "context-patterns.md.template": capsule_path / "context" / "patterns.md",
            "context-evolution.md.template": capsule_path / "context" / "evolution.md",
        }
        
        for template_name, output_path in templates.items():
            template_path = self.templates_dir / template_name
            
            if not template_path.exists():
                print(f"Warning: Template {template_name} not found, skipping")
                continue
                
            # Read template
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Substitute placeholders
            output_content = self.substitute_template(template_content, placeholders)
            
            # Write output file
            with open(output_path, 'w') as f:
                f.write(output_content)
            
            print(f"Generated: {output_path}")
    
    def generate_for_capsule(self, capsule_name: str, force: bool = False, interactive: bool = False):
        """Generate framework for a specific capsule"""
        capsule_path = self.builderOS_root / "capsules" / capsule_name
        
        if not capsule_path.exists():
            raise FileNotFoundError(f"Capsule {capsule_name} not found at {capsule_path}")
        
        # Check if framework already exists
        if not force:
            existing_files = [
                capsule_path / "standards.yaml",
                capsule_path / "product.yaml",
                capsule_path / "specs" / "current.yaml"
            ]
            
            if any(f.exists() for f in existing_files):
                print(f"Framework files already exist for {capsule_name}. Use --force to overwrite.")
                return
        
        # Load capsule config
        try:
            config = self.load_capsule_config(capsule_path)
            capsule_slug = config.get('slug', capsule_name)
        except FileNotFoundError:
            capsule_slug = capsule_name
            print(f"Warning: No capsule.map.json found, using {capsule_name} as slug")
        
        # Generate placeholders
        placeholders = self.get_template_placeholders(capsule_name, capsule_slug)
        
        # Interactive customization if requested
        if interactive:
            placeholders = self.collect_interactive_placeholders(placeholders)
        
        # Generate files
        self.generate_framework_files(capsule_path, placeholders)
        
        # Validate generated files
        if self.validate_generated_files(capsule_path):
            print(f"✅ Framework generated for capsule: {capsule_name}")
            if not interactive:
                print(f"💡 Use --interactive next time for guided setup")
                print(f"📝 TODO: Customize the generated files with project-specific details")
        else:
            print(f"⚠️  Framework generated with validation warnings")
    
    def validate_generated_files(self, capsule_path: Path) -> bool:
        """Basic validation of generated files"""
        try:
            # Test YAML parsing
            required_files = [
                capsule_path / "standards.yaml",
                capsule_path / "product.yaml", 
                capsule_path / "specs" / "current.yaml",
                capsule_path / "specs" / "next.yaml"
            ]
            
            for file_path in required_files:
                if file_path.exists():
                    with open(file_path, 'r') as f:
                        yaml.safe_load(f)
            
            return True
        except Exception as e:
            print(f"Validation error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Generate Catalyst framework for capsules")
    parser.add_argument("capsule", help="Name of the capsule to generate framework for")
    parser.add_argument("--force", action="store_true", help="Overwrite existing framework files")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive mode with guided variable setup")
    parser.add_argument("--builderOS-root", default="{{CATALYST_ROOT}}", 
                       help="Path to Catalyst root directory")
    
    args = parser.parse_args()
    
    try:
        generator = FrameworkGenerator(args.builderOS_root)
        generator.generate_for_capsule(args.capsule, args.force, args.interactive)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()