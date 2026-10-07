#!/usr/bin/env python3
"""
Agent OS Enhancement Tool for Catalyst

This tool enhances existing capsules with comprehensive Agent OS directory
structures and context, integrating the Agent OS framework with Builder patterns.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class AgentOSEnhancer:
    def __init__(self, builder_root: Path):
        self.builder_root = Path(builder_root)
        self.capsules_dir = self.builder_root / "capsules"
        self.global_agent_os = self.builder_root / "global" / "agent-os"
        
    def get_capsule_metadata(self, capsule_path: Path) -> Dict:
        """Extract metadata from capsule.json and requirements.yaml"""
        metadata = {}
        
        # Read capsule.json
        capsule_json = capsule_path / "capsule.json"
        if capsule_json.exists():
            with open(capsule_json, 'r') as f:
                metadata['capsule'] = json.load(f)
        
        # Read requirements.yaml
        requirements_yaml = capsule_path / "spec" / "requirements.yaml"
        if requirements_yaml.exists():
            with open(requirements_yaml, 'r') as f:
                metadata['requirements'] = yaml.safe_load(f)
        
        return metadata
    
    def determine_capsule_characteristics(self, metadata: Dict) -> Dict:
        """Determine lane, branch, and specialization from metadata"""
        characteristics = {
            'branch': 'automation',  # default
            'targets': [],
            'type': 'general'
        }
        
        # Extract from capsule.json
        if 'capsule' in metadata:
            capsule_data = metadata['capsule']
            characteristics['type'] = capsule_data.get('type', 'general')
            
        # Extract from requirements.yaml
        if 'requirements' in metadata:
            req_data = metadata['requirements']
            if 'project' in req_data:
                project = req_data['project']
                characteristics['branch'] = project.get('branch', 'automation')
                characteristics['targets'] = project.get('targets', [])
                
        return characteristics
    
    def generate_product_context(self, capsule_name: str, metadata: Dict, characteristics: Dict) -> str:
        """Generate product layer context"""
        capsule_data = metadata.get('capsule', {})
        description = capsule_data.get('description', f'{capsule_name} capsule')
        
        return f"""# Product Vision - {capsule_name.title()}

## Project Purpose
{description}

## Business Value
- Supports Builder system's core mission of building everything needed
- Integrates with Builder ecosystem and automation patterns

## Key Success Metrics
- Reliable operation within Builder system
- Effective integration with Builder workflows

## Target Users
- Builder system (automated workflows)
- {{USER_NAME}} (direct usage and management)
- Integration with other capsules and systems

## Strategic Context
This capsule is part of the Builder ecosystem, designed to support the system's
goal of efficiently moving ideas from ideation through design, build, and deploy phases.
"""

    def generate_architecture_context(self, capsule_name: str, characteristics: Dict) -> str:
        """Generate architecture context"""
        return f"""# Architecture Overview - {capsule_name.title()}

## System Architecture
- **Branch**: {characteristics['branch']} (technology focus)
- **Targets**: {', '.join(characteristics['targets']) if characteristics['targets'] else 'General purpose'}
- **Integration**: Builder system capsule pattern

## Key Components
- Core functionality in `src/` directory
- Configuration and specifications in `spec/` directory  
- Documentation in `docs/` directory
- Operational artifacts in `ops/` and `runs/` directories

## Integration Points
- Builder system automation and monitoring
- MCP memory system for context persistence
- n8n workflows for automation integration
- Claude Code agent system for development

## Quality Architecture
- Comprehensive error handling and logging
- Integration with Builder monitoring and alerting
- Documentation and operational runbooks

## Technology Constraints
- Must integrate with Builder system patterns
- Follows established Builder conventions
- Compatible with Builder automation infrastructure
- Supports Builder's quality and security requirements
"""

    def generate_coding_standards(self, characteristics: Dict) -> str:
        """Generate capsule-specific coding standards"""
        base_standards = """# Coding Standards

## Inheritance Hierarchy
This capsule inherits standards from:
1. Global Agent OS base standards
2. Lane-specific standards ({lane})
3. Branch-specific standards ({branch})
4. Capsule-specific customizations (this file)

## Capsule-Specific Standards

### Architecture Patterns
- Follow Builder capsule structure conventions
- Maintain clean separation between configuration, implementation, and operations
- Use established Builder integration patterns

### Error Handling
- Comprehensive error handling for {lane} requirements
- Integration with Builder logging and monitoring systems
- Proper escalation and notification procedures

### Testing Strategy
- {lane} testing requirements apply
- Integration testing with Builder system components
- End-to-end testing of key workflows

### Documentation Requirements
- Complete operational runbooks
- Integration and deployment procedures
- Troubleshooting and maintenance guides

### Security Considerations
- Follow Builder security patterns and requirements
- Secure handling of configuration and secrets
- Integration with Builder security monitoring

## Quality Gates
All {lane} quality gates must pass before deployment or integration.
        
        return base_standards

    def generate_agent_instructions(self, capsule_name: str, metadata: Dict, characteristics: Dict) -> str:
        """Generate agent-specific instructions"""
        return f"""---
type: context
scope: capsule
priority: high
inheritable: false
---

# Agent Context - {capsule_name.title()}

## Project Context
- **Capsule**: {capsule_name}
- **Branch**: {characteristics['branch']}
- **Type**: {characteristics['type']}
- **Targets**: {characteristics['targets']}

## Development Instructions
2. Apply {characteristics['branch']}-specific best practices
3. Integrate with Builder system patterns
4. Maintain compatibility with established conventions

## Quality Requirements
- Comprehensive testing for {characteristics['branch']} workflows
- Complete documentation and operational procedures
- Integration with Builder monitoring and alerting

## Success Criteria
- Reliable operation within Builder ecosystem
- Effective integration with Builder workflows
- Maintainable and extensible implementation
"""

    def enhance_capsule(self, capsule_path: Path) -> bool:
        """Enhance a single capsule with Agent OS structure"""
        capsule_name = capsule_path.name
        print(f"Enhancing capsule: {capsule_name}")
        
        # Create .agent-os directory structure
        agent_os_dir = capsule_path / ".agent-os"
        agent_os_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (agent_os_dir / "product").mkdir(exist_ok=True)
        (agent_os_dir / "specs").mkdir(exist_ok=True)
        (agent_os_dir / "standards").mkdir(exist_ok=True)
        (agent_os_dir / "instructions").mkdir(exist_ok=True)
        
        # Get capsule metadata and characteristics
        metadata = self.get_capsule_metadata(capsule_path)
        characteristics = self.determine_capsule_characteristics(metadata)
        
        # Generate and write content
        try:
            # Product layer
            vision_file = agent_os_dir / "product" / "vision.md"
            if not vision_file.exists():
                with open(vision_file, 'w') as f:
                    f.write(self.generate_product_context(capsule_name, metadata, characteristics))
            
            architecture_file = agent_os_dir / "product" / "architecture.md"
            if not architecture_file.exists():
                with open(architecture_file, 'w') as f:
                    f.write(self.generate_architecture_context(capsule_name, characteristics))
            
            # Standards layer
            standards_file = agent_os_dir / "standards" / "coding-standards.md"
            if not standards_file.exists():
                with open(standards_file, 'w') as f:
                    f.write(self.generate_coding_standards(characteristics))
            
            # Instructions layer
            instructions_file = agent_os_dir / "instructions" / "agent-context.md"
            if not instructions_file.exists():
                with open(instructions_file, 'w') as f:
                    f.write(self.generate_agent_instructions(capsule_name, metadata, characteristics))
            
            print(f"✓ Enhanced {capsule_name} successfully")
            return True
            
        except Exception as e:
            print(f"✗ Failed to enhance {capsule_name}: {e}")
            return False

    def enhance_all_capsules(self) -> Dict[str, bool]:
        """Enhance all capsules in the capsules directory"""
        results = {}
        
        if not self.capsules_dir.exists():
            print(f"Capsules directory not found: {self.capsules_dir}")
            return results
        
        for item in self.capsules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Skip ops directory which contains special capsules
                if item.name == 'ops':
                    continue
                    
                results[item.name] = self.enhance_capsule(item)
        
        return results

    def validate_enhancement(self, capsule_path: Path) -> List[str]:
        """Validate that capsule has proper Agent OS structure"""
        issues = []
        agent_os_dir = capsule_path / ".agent-os"
        
        if not agent_os_dir.exists():
            issues.append("Missing .agent-os directory")
            return issues
        
        required_files = [
            "product/vision.md",
            "product/architecture.md", 
            "standards/coding-standards.md",
            "instructions/agent-context.md"
        ]
        
        for file_path in required_files:
            full_path = agent_os_dir / file_path
            if not full_path.exists():
                issues.append(f"Missing required file: {file_path}")
        
        return issues


def main():
    parser = argparse.ArgumentParser(description='Enhance capsules with Agent OS structure')
    parser.add_argument('--capsule', help='Specific capsule to enhance')
    parser.add_argument('--validate', action='store_true', help='Validate existing Agent OS structure')
    parser.add_argument('--builder-root', default='{{CATALYST_ROOT}}', 
                       help='Builder system root directory')
    
    args = parser.parse_args()
    
    enhancer = AgentOSEnhancer(args.builder_root)
    
    if args.validate:
        print("Validating Agent OS structure...")
        for item in enhancer.capsules_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != 'ops':
                issues = enhancer.validate_enhancement(item)
                if issues:
                    print(f"✗ {item.name}: {', '.join(issues)}")
                else:
                    print(f"✓ {item.name}: Agent OS structure valid")
    
    elif args.capsule:
        capsule_path = enhancer.capsules_dir / args.capsule
        if capsule_path.exists():
            success = enhancer.enhance_capsule(capsule_path)
            if success:
                print(f"Successfully enhanced {args.capsule}")
            else:
                print(f"Failed to enhance {args.capsule}")
        else:
            print(f"Capsule not found: {args.capsule}")
    
    else:
        print("Enhancing all capsules...")
        results = enhancer.enhance_all_capsules()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"\nEnhancement complete: {success_count}/{total_count} capsules enhanced successfully")
        
        for capsule, success in results.items():
            status = "✓" if success else "✗"
            print(f"{status} {capsule}")


if __name__ == "__main__":
    main()