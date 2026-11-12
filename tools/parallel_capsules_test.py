#!/usr/bin/env python3
"""
Launch parallel capsules test with two-lane workflow
Tests both standard and standard simultaneously with different domains
"""

import json
import shutil
import pathlib
import datetime
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

BUILDER_ROOT = pathlib.Path.home() / "Documents" / "Builder"
TEST_DIR = BUILDER_ROOT / "testing" / "parallel_test"
TEMPLATES_DIR = BUILDER_ROOT / "templates"

def create_test_capsule(template_name, capsule_name, lane, customizations=None):
    """Create a test capsule from template"""
    template_dir = TEMPLATES_DIR / f"{template_name}-starter"
    capsule_dir = TEST_DIR / capsule_name
    
    if not template_dir.exists():
        raise FileNotFoundError(f"Template not found: {template_dir}")
    
    # Remove existing test capsule
    if capsule_dir.exists():
        shutil.rmtree(capsule_dir)
    
    # Copy template
    shutil.copytree(template_dir, capsule_dir)
    
    # Customize for test
    metadata_file = capsule_dir / "spec" / "metadata.yaml"
    requirements_file = capsule_dir / "spec" / "requirements.yaml"
    
    # Update metadata
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            content = f.read()
        
        # Replace template placeholders
        replacements = {
            '{{AUTOMATION_NAME}}': f'Test {capsule_name}',
            '{{AUTOMATION_SLUG}}': capsule_name,
            '{{WEB_APP_NAME}}': f'Test {capsule_name}',
            '{{WEB_APP_SLUG}}': capsule_name,
            '{{APP_NAME}}': f'Test {capsule_name}',
            '{{APP_SLUG}}': capsule_name,
            '{{CREATION_DATE}}': datetime.datetime.now().isoformat(),
            '{{USER_NAME}}': 'Builder Test',
            '{{DEADLINE}}': '2025-08-15',
            'standard': lane,
            'standard': lane
        }
        
        if customizations:
            replacements.update(customizations)
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, str(value))
        
        # Ensure correct lane setting
        if 'lane: "' in content:
            content = content.replace('lane: "standard"', f'lane: "{lane}"')
            content = content.replace('lane: "standard"', f'lane: "{lane}"')
        
        with open(metadata_file, 'w') as f:
            f.write(content)
    
    # Update requirements
    if requirements_file.exists():
        with open(requirements_file, 'r') as f:
            content = f.read()
        
        # Add test-specific requirements
        content = content.replace('{{PROJECT_NAME}}', f'Test {capsule_name}')
        content = content.replace('{{PROJECT_SLUG}}', capsule_name)
        content = content.replace('{{PROJECT_DESCRIPTION}}', f'Test capsule for {template_name} template in {lane}')
        content = content.replace('{{LANE}}', lane)
        
        # Add lane-specific requirements
        if lane == 'standard':
            content = content.replace('{{CORE_REQUIREMENT_1}}', 'Basic functionality working')
            content = content.replace('{{CORE_REQUIREMENT_2}}', 'Simple error handling')
            content = content.replace('{{CORE_REQUIREMENT_3}}', 'Quick iteration support')
        else:  # standard
            content = content.replace('{{CORE_REQUIREMENT_1}}', 'Production-ready functionality')
            content = content.replace('{{CORE_REQUIREMENT_2}}', 'Comprehensive error handling')
            content = content.replace('{{CORE_REQUIREMENT_3}}', 'Full security and performance validation')
        
        with open(requirements_file, 'w') as f:
            f.write(content)
    
    print(f"✅ Created test capsule: {capsule_name} ({lane})")
    return capsule_dir

def test_capsule_routing(capsule_dir):
    """Test that capsule routes to correct agents and MCPs"""
    capsule_name = capsule_dir.name
    
    try:
        # Test MCP resolution
        mcp_result = subprocess.run([
            str(BUILDER_ROOT / "tools" / "mcp_resolver.py"),
            str(capsule_dir),
            str(BUILDER_ROOT / "global" / "mcp" / "profiles")
        ], capture_output=True, text=True, timeout=10)
        
        if mcp_result.returncode == 0:
            mcp_servers = mcp_result.stdout.strip().split()
            print(f"  📡 {capsule_name}: MCP servers resolved: {mcp_servers}")
        else:
            print(f"  ❌ {capsule_name}: MCP resolution failed")
            return False
        
        # Test agent routing (simulate)
        metadata_file = capsule_dir / "spec" / "metadata.yaml"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                content = f.read()
            
            # Extract routing info
            if 'branch: "automation"' in content:
                expected_agent = 'automation-specialist'
            elif 'branch: "web"' in content:
                expected_agent = 'frontend-specialist'
            elif 'branch: "apple"' in content:
                expected_agent = 'ios-specialist'
            else:
                expected_agent = 'unknown'
            
            print(f"  🤖 {capsule_name}: Expected primary agent: {expected_agent}")
        
        # Test DoD validation
        lane = 'standard' if 'standard' in content else 'standard'
        dod_file = capsule_dir / "ops" / "dod.yaml"
        if dod_file.exists():
            with open(dod_file, 'r') as f:
                dod_content = f.read()
            
            if lane == 'standard':
                required_checks = ['security_scan', 'performance_benchmark', 'code_review']
                has_required = all(check in dod_content for check in required_checks)
                print(f"  🛡️  {capsule_name}: DoD validation ({lane}): {'✅' if has_required else '❌'}")
            else:
                basic_checks = ['functionality', 'basic_error_handling']
                has_basic = any(check in dod_content.lower() for check in basic_checks)
                print(f"  ⚡ {capsule_name}: DoD validation ({lane}): {'✅' if has_basic else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ {capsule_name}: Routing test failed: {e}")
        return False

def simulate_capsule_work(capsule_dir, duration_seconds=5):
    """Simulate work being done on a capsule"""
    capsule_name = capsule_dir.name
    
    # Log capsule start
    subprocess.run([
        str(BUILDER_ROOT / "tools" / "events_logger.py"),
        "capsule_activated",
        f"Started parallel test for {capsule_name}",
        f"--slug={capsule_name}",
        "--level=INFO"
    ], cwd=BUILDER_ROOT)
    
    print(f"  🚀 {capsule_name}: Starting work simulation...")
    
    # Simulate some file modifications
    src_dir = capsule_dir / "src"
    if src_dir.exists():
        # Touch some files to simulate activity
        for i in range(3):
            time.sleep(duration_seconds / 3)
            test_file = src_dir / f"test_file_{i}.txt"
            with open(test_file, 'w') as f:
                f.write(f"Test content {i} at {datetime.datetime.now()}\n")
            print(f"    📝 {capsule_name}: Created {test_file.name}")
    
    # Log completion
    subprocess.run([
        str(BUILDER_ROOT / "tools" / "events_logger.py"),
        "capsule_completed",
        f"Completed parallel test for {capsule_name}",
        f"--slug={capsule_name}",
        "--level=INFO"
    ], cwd=BUILDER_ROOT)
    
    print(f"  ✅ {capsule_name}: Work simulation completed")
    return True

def run_parallel_test():
    """Run the parallel capsules test"""
    print("🔀 Parallel Capsules Test - Two-Lane Workflow")
    print("=" * 60)
    
    # Ensure test directory exists
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Define test capsules
    test_capsules = [
        {
            'template': 'automation',
            'name': 'automation-fast-test',
            'description': 'Fast automation capsule'
        },
        {
            'template': 'web-dev',
            'name': 'webapp-deep-test', 
            'description': 'Deep web app capsule'
        },
        {
            'template': 'apple-app',
            'name': 'ios-deep-test',
            'description': 'Deep iOS app capsule'
        }
    ]
    
    # Create test capsules
    print("📦 Creating Test Capsules...")
    capsule_dirs = []
    for capsule_config in test_capsules:
        try:
            capsule_dir = create_test_capsule(
                capsule_config['template'],
                capsule_config['name'], 
            )
            capsule_dirs.append((capsule_dir, capsule_config))
        except Exception as e:
            print(f"❌ Failed to create {capsule_config['name']}: {e}")
    
    if not capsule_dirs:
        print("❌ No test capsules created successfully")
        return False
    
    print(f"\n🔍 Testing Capsule Routing...")
    routing_results = []
    for capsule_dir, config in capsule_dirs:
        result = test_capsule_routing(capsule_dir)
        routing_results.append(result)
    
    # Run parallel work simulation
    print(f"\n⚡ Running Parallel Work Simulation...")
    
    def run_capsule_work(capsule_info):
        capsule_dir, config = capsule_info
        return simulate_capsule_work(capsule_dir, duration_seconds=3)
    
    # Execute in parallel using ThreadPoolExecutor
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=len(capsule_dirs)) as executor:
        # Submit all tasks
        future_to_capsule = {
            executor.submit(run_capsule_work, capsule_info): capsule_info 
            for capsule_info in capsule_dirs
        }
        
        # Wait for completion
        work_results = []
        for future in as_completed(future_to_capsule):
            capsule_info = future_to_capsule[future]
            try:
                result = future.result()
                work_results.append(result)
            except Exception as e:
                capsule_dir, config = capsule_info
                print(f"❌ {config['name']} failed: {e}")
                work_results.append(False)
    
    end_time = time.time()
    
    # Results summary
    print(f"\n📊 Parallel Test Results:")
    print(f"   Duration: {end_time - start_time:.2f} seconds")
    print(f"   Capsules: {len(capsule_dirs)}")
    print(f"   Routing: {sum(routing_results)}/{len(routing_results)} passed")
    print(f"   Work Simulation: {sum(work_results)}/{len(work_results)} passed")
    
    # Lane distribution
    
    print(f"   Lane Distribution: {standard_count} standard, {standard_count} standard")
    
    # Domain distribution  
    domains = [config['template'] for _, config in capsule_dirs]
    domain_counts = {domain: domains.count(domain) for domain in set(domains)}
    print(f"   Domain Distribution: {domain_counts}")
    
    # Overall success
    overall_success = (
        all(routing_results) and 
        all(work_results) and
        len(capsule_dirs) >= 2 and  # At least 2 capsules
        standard_count > 0 and     # At least one standard
        standard_count > 0         # At least one standard
    )
    
    if overall_success:
        print("\n🎉 Parallel Capsules Test PASSED!")
        print("✅ Demonstrated:")
        print("   • Multiple capsules running simultaneously")  
        print("   • Both standard and standard workflows")
        print("   • Different domains (automation, web, mobile)")
        print("   • Independent agent routing and MCP grants")
        print("   • Concurrent event logging")
        return True
    else:
        print("\n⚠️  Parallel Capsules Test had issues")
        return False

def main():
    """Main test execution"""
    try:
        success = run_parallel_test()
        
        # Run health check after test
        print(f"\n🏥 Post-Test Health Check...")
        health_result = subprocess.run([
            str(BUILDER_ROOT / "tools" / "system_health_rollup.py")
        ], cwd=BUILDER_ROOT)
        
        return success and health_result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)