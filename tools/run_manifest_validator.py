#!/usr/bin/env python3
"""
Run Manifest Validator - Validate and enforce manifest.json schema across capsules
Implements the Run Artifact Specification for consistent run tracking
"""

import json
import pathlib
import sys
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import jsonschema
from jsonschema import validate, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# JSON Schema for manifest validation
MANIFEST_SCHEMA = {
    "type": "object",
    "properties": {
        "run_id": {"type": "string", "pattern": "^[a-zA-Z0-9][a-zA-Z0-9\\-_]*$"},
        "capsule_name": {"type": "string", "minLength": 1},
        "start_time": {"type": "string", "format": "date-time"},
        "end_time": {"type": ["string", "null"], "format": "date-time"},
        "total_duration_ms": {"type": ["number", "null"], "minimum": 0},
        "status": {"type": "string", "enum": ["pending", "running", "completed", "failed"]},
        "success": {"type": "boolean"},
        "trigger": {"type": "string", "enum": ["manual", "scheduled", "webhook", "test", "replay"]},
        "exit_code": {"type": ["number", "null"]},
        "error_summary": {"type": ["string", "null"]},
        
        "environment": {
            "type": "object",
            "properties": {
                "builder_version": {"type": "string"},
                "platform": {"type": "string"},
                "working_directory": {"type": "string"},
                "environment_variables": {"type": "object"},
                "resource_limits": {"type": "object"}
            }
        },
        
        "inputs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type", "source"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["string", "file", "config", "secret"]},
                    "source": {"type": "string", "enum": ["user", "config", "environment", "file"]},
                    "value": {},  # Any type
                    "required": {"type": "boolean"}
                }
            }
        },
        
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type", "path"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["artifact", "log", "metric", "report"]},
                    "path": {"type": "string"},
                    "size_bytes": {"type": ["number", "null"]},
                    "checksum": {"type": ["string", "null"]}
                }
            }
        },
        
        "stages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "command": {"type": ["string", "null"]},
                    "start_time": {"type": ["string", "null"], "format": "date-time"},
                    "end_time": {"type": ["string", "null"], "format": "date-time"},
                    "duration_ms": {"type": ["number", "null"]},
                    "status": {"type": "string", "enum": ["pending", "running", "success", "failed"]},
                    "exit_code": {"type": ["number", "null"]},
                    "log_path": {"type": ["string", "null"]},
                    "error_message": {"type": ["string", "null"]}
                }
            }
        },
        
        "metadata": {
            "type": "object",
            "properties": {
                "user": {"type": "string"},
                "git_commit": {"type": ["string", "null"]},
                "git_branch": {"type": ["string", "null"]},
                "replay_of": {"type": ["string", "null"]},
                "fork_source": {"type": ["string", "null"]},
                "tags": {
                    "type": "array", 
                    "items": {"type": "string"}
                },
                "custom": {"type": "object"}
            }
        },
        
        "dod_validation": {
            "type": "object",
            "properties": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "checks_performed": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "status"],
                        "properties": {
                            "name": {"type": "string"},
                            "status": {"type": "string", "enum": ["pass", "fail", "skip"]},
                            "message": {"type": "string"},
                            "details": {"type": "object"}
                        }
                    }
                },
                "overall_compliance": {"type": "boolean"}
            }
        }
    }
}

@dataclass
class ValidationResult:
    """Result of manifest validation"""
    valid: bool
    errors: List[str]
    warnings: List[str] 
    manifest_path: str
    schema_version: str = "1.0"

class ManifestValidator:
    """Validates run manifests against the specification"""
    
    def __init__(self, builder_root: pathlib.Path = None):
        self.builder_root = builder_root or pathlib.Path.home() / "Documents" / "Builder"
        self.schema = MANIFEST_SCHEMA
        
    def validate_manifest_file(self, manifest_path: pathlib.Path) -> ValidationResult:
        """Validate a manifest file against the schema"""
        result = ValidationResult(
            valid=False,
            errors=[],
            warnings=[],
            manifest_path=str(manifest_path)
        )
        
        try:
            # Check file exists
            if not manifest_path.exists():
                result.errors.append(f"Manifest file does not exist: {manifest_path}")
                return result
            
            # Parse JSON
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            # Validate schema
            validate(instance=manifest_data, schema=self.schema)
            
            # Additional business logic validation
            additional_validation = self._validate_business_logic(manifest_data)
            result.warnings.extend(additional_validation.get('warnings', []))
            result.errors.extend(additional_validation.get('errors', []))
            
            # If no errors, mark as valid
            if not result.errors:
                result.valid = True
                
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid JSON: {e}")
        except ValidationError as e:
            result.errors.append(f"Schema validation failed: {e.message}")
        except Exception as e:
            result.errors.append(f"Validation error: {e}")
        
        return result
    
    def _validate_business_logic(self, manifest_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Additional business logic validation beyond schema"""
        warnings = []
        errors = []
        
        # Lane-specific validation
        if lane == 'standard':
            # standard requires DoD validation
            if not manifest_data.get('dod_validation'):
                errors.append("standard runs require dod_validation section")
            
            # standard should have comprehensive logging
            stages = manifest_data.get('stages', [])
            for stage in stages:
                if not stage.get('log_path'):
                    warnings.append(f"standard stage '{stage.get('name')}' missing log_path")
        
        # Status consistency
        status = manifest_data.get('status')
        success = manifest_data.get('success')
        if status == 'completed' and success is None:
            errors.append("Completed runs must have success field set")
        
        # Time consistency  
        start_time = manifest_data.get('start_time')
        end_time = manifest_data.get('end_time')
        if start_time and end_time:
            try:
                start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                if end < start:
                    errors.append("end_time cannot be before start_time")
            except:
                warnings.append("Could not validate time consistency")
        
        # Stage consistency
        stages = manifest_data.get('stages', [])
        for i, stage in enumerate(stages):
            stage_name = stage.get('name', f'stage_{i}')
            
            # Stage times
            stage_start = stage.get('start_time')
            stage_end = stage.get('end_time')
            if stage_start and stage_end:
                try:
                    s_start = datetime.fromisoformat(stage_start.replace('Z', '+00:00'))
                    s_end = datetime.fromisoformat(stage_end.replace('Z', '+00:00'))
                    if s_end < s_start:
                        errors.append(f"Stage '{stage_name}' end_time before start_time")
                except:
                    warnings.append(f"Could not validate stage '{stage_name}' time consistency")
            
            # Exit code consistency
            stage_status = stage.get('status')
            exit_code = stage.get('exit_code')
            if stage_status == 'success' and exit_code is not None and exit_code != 0:
                warnings.append(f"Stage '{stage_name}' marked success but has non-zero exit code")
            elif stage_status == 'failed' and exit_code == 0:
                warnings.append(f"Stage '{stage_name}' marked failed but has zero exit code")
        
        return {'warnings': warnings, 'errors': errors}
    
    def validate_capsule_runs(self, capsule_path: pathlib.Path) -> List[ValidationResult]:
        """Validate all run manifests for a capsule"""
        results = []
        runs_dir = capsule_path / "runs"
        
        if not runs_dir.exists():
            return results
        
        for run_dir in runs_dir.iterdir():
            if run_dir.is_dir():
                manifest_file = run_dir / "manifest.json"
                result = self.validate_manifest_file(manifest_file)
                results.append(result)
        
        return results
    
    def validate_all_capsules(self) -> Dict[str, List[ValidationResult]]:
        """Validate manifests for all capsules"""
        results = {}
        capsules_dir = self.builder_root / "capsules"
        
        if not capsules_dir.exists():
            logger.warning(f"Capsules directory not found: {capsules_dir}")
            return results
        
        for capsule_dir in capsules_dir.iterdir():
            if capsule_dir.is_dir() and not capsule_dir.name.startswith('.'):
                capsule_name = capsule_dir.name
                capsule_results = self.validate_capsule_runs(capsule_dir)
                if capsule_results:  # Only include capsules with runs
                    results[capsule_name] = capsule_results
        
        return results
    
    def generate_validation_report(self, results: Dict[str, List[ValidationResult]]) -> str:
        """Generate human-readable validation report"""
        report = ["# Run Manifest Validation Report\n"]
        report.append(f"**Generated**: {datetime.now().isoformat()}\n")
        
        total_manifests = sum(len(capsule_results) for capsule_results in results.values())
        valid_manifests = sum(
            len([r for r in capsule_results if r.valid]) 
            for capsule_results in results.values()
        )
        
        report.append(f"**Summary**: {valid_manifests}/{total_manifests} manifests valid\n")
        
        if total_manifests == 0:
            report.append("No run manifests found to validate.\n")
            return "\n".join(report)
        
        # Per-capsule results
        for capsule_name, capsule_results in sorted(results.items()):
            capsule_valid = len([r for r in capsule_results if r.valid])
            capsule_total = len(capsule_results)
            
            status_emoji = "✅" if capsule_valid == capsule_total else "❌"
            report.append(f"\n## {status_emoji} {capsule_name} ({capsule_valid}/{capsule_total})\n")
            
            # Show failures and warnings
            for result in capsule_results:
                if not result.valid or result.warnings:
                    run_id = pathlib.Path(result.manifest_path).parent.name
                    
                    if not result.valid:
                        report.append(f"### ❌ {run_id}\n")
                        for error in result.errors:
                            report.append(f"- **Error**: {error}\n")
                    
                    if result.warnings:
                        if result.valid:
                            report.append(f"### ⚠️ {run_id}\n")
                        for warning in result.warnings:
                            report.append(f"- **Warning**: {warning}\n")
        
        return "\n".join(report)

def main():
    """CLI interface for manifest validation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Manifest Validator")
    parser.add_argument("--capsule", "-c", help="Validate specific capsule only")
    parser.add_argument("--manifest", "-m", help="Validate specific manifest file")
    parser.add_argument("--report", "-r", action="store_true", help="Generate detailed report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    
    args = parser.parse_args()
    
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)
    
    try:
        validator = ManifestValidator()
        
        if args.manifest:
            # Validate single manifest
            manifest_path = pathlib.Path(args.manifest)
            result = validator.validate_manifest_file(manifest_path)
            
            if args.json:
                print(json.dumps(asdict(result), indent=2))
            else:
                status = "✅ VALID" if result.valid else "❌ INVALID"
                print(f"{status}: {manifest_path}")
                
                for error in result.errors:
                    print(f"  Error: {error}")
                for warning in result.warnings:
                    print(f"  Warning: {warning}")
            
            sys.exit(0 if result.valid else 1)
            
        elif args.capsule:
            # Validate specific capsule
            capsule_path = validator.builder_root / "capsules" / args.capsule
            results = validator.validate_capsule_runs(capsule_path)
            
            if args.json:
                print(json.dumps([asdict(r) for r in results], indent=2))
            else:
                valid_count = len([r for r in results if r.valid])
                total_count = len(results)
                
                status = "✅" if valid_count == total_count else "❌"
                print(f"{status} {args.capsule}: {valid_count}/{total_count} manifests valid")
                
                for result in results:
                    if not result.valid:
                        run_id = pathlib.Path(result.manifest_path).parent.name
                        print(f"  ❌ {run_id}")
                        for error in result.errors:
                            print(f"    - {error}")
            
            sys.exit(0 if valid_count == total_count else 1)
            
        else:
            # Validate all capsules
            results = validator.validate_all_capsules()
            
            if args.json:
                json_results = {
                    capsule: [asdict(r) for r in capsule_results]
                    for capsule, capsule_results in results.items()
                }
                print(json.dumps(json_results, indent=2))
            elif args.report:
                report = validator.generate_validation_report(results)
                print(report)
            else:
                # Summary output
                total_manifests = sum(len(capsule_results) for capsule_results in results.values())
                valid_manifests = sum(
                    len([r for r in capsule_results if r.valid]) 
                    for capsule_results in results.values()
                )
                
                if total_manifests == 0:
                    print("No run manifests found")
                    sys.exit(0)
                
                status = "✅" if valid_manifests == total_manifests else "❌"
                print(f"{status} Manifest Validation: {valid_manifests}/{total_manifests} valid")
                
                # Show capsule summary
                for capsule_name, capsule_results in sorted(results.items()):
                    capsule_valid = len([r for r in capsule_results if r.valid])
                    capsule_total = len(capsule_results)
                    capsule_status = "✅" if capsule_valid == capsule_total else "❌"
                    print(f"  {capsule_status} {capsule_name}: {capsule_valid}/{capsule_total}")
                
                sys.exit(0 if valid_manifests == total_manifests else 1)
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()