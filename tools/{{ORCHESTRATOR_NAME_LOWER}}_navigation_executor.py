#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Navigation Executor - Bridge between intent detection and execution
Seamlessly executes navigation based on natural language intents
"""

import subprocess
import sys
import os
from pathlib import Path
import json


def execute_navigation(intent: str) -> tuple[bool, str]:
    """Execute navigation based on detected intent"""
    builder_root = Path(__file__).parent.parent
    nav_script = builder_root / "tools" / "nav.py"
    
    if not nav_script.exists():
        return False, f"Navigation script not found: {nav_script}"
    
    try:
        # Get navigation target using existing nav.py
        result = subprocess.run(
            [sys.executable, str(nav_script), intent],
            cwd=builder_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and "NAVIGATE_TO:" in result.stdout:
            target_path = result.stdout.split("NAVIGATE_TO:", 1)[1].strip()
            
            # Validate target path exists
            if not Path(target_path).exists():
                return False, f"Target path does not exist: {target_path}"
            
            # Use nav_with_context.py for seamless mid-session navigation
            capsule_name = Path(target_path).name
            nav_with_context = builder_root / "tools" / "nav_with_context.py"

            # Execute nav_with_context.py to load context into current session
            return True, f"python3 {nav_with_context} {capsule_name}"
            
        else:
            error_msg = result.stderr or result.stdout or "Unknown navigation error"
            return False, f"Navigation failed: {error_msg.strip()}"
            
    except FileNotFoundError:
        return False, "Python interpreter not found"
    except Exception as e:
        return False, f"Navigation execution failed: {e}"


def get_navigation_confidence(intent: str) -> dict:
    """Calculate confidence score for navigation intent"""
    builder_root = Path(__file__).parent.parent
    nav_script = builder_root / "tools" / "nav.py"
    
    # Capsule keyword mapping for confidence scoring
    capsule_keywords = {
        'jellyfin-server-ops': ['media', 'server', 'jellyfin', 'streaming', 'plex', 'movies', 'tv', 'content', 'downloads'],
        'brandjack': ['instagram', 'brand', 'social', 'content', 'posting', 'engagement', 'followers', 'scraping'],
        'catalyst-mobile': ['mobile', 'ios', 'app', 'swift', 'xcode', 'iphone', 'ipad', 'appstore'],
        'ecommerce': ['store', 'shop', 'shopify', 'products', 'checkout', 'ecommerce', 'sales', 'inventory'],
        'jar-label-automation': ['labels', 'jars', 'automation', 'shortcuts', 'organize', 'kitchen'],
        'instagram-cropper': ['crop', 'image', 'photo', 'instagram', 'resize', 'aspect', 'ratio'],
        'builder-system': ['system', 'builder', '{{ORCHESTRATOR_NAME_LOWER}}', 'framework', 'core', 'governance', 'tools'],
        'ops': ['operations', 'deployment', 'infrastructure', 'servers', 'monitoring', 'browser'],
        'system-ops-advisor': ['ops', 'advisor', 'systems', 'consultation', 'architecture', 'weekly'],
        'shortcut-demo': ['shortcut', 'demo', 'example', 'tutorial', 'workflow'],
        'winthemorning': ['morning', 'routine', 'habits', 'productivity', 'schedule']
    }
    
    intent_lower = intent.lower()
    scores = {}
    
    for capsule, keywords in capsule_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword in intent_lower:
                score += 1
        
        if score > 0:
            # Normalize score as percentage
            confidence = min(100, (score / len(keywords)) * 100)
            scores[capsule] = confidence
    
    # Return highest confidence match
    if scores:
        best_match = max(scores.items(), key=lambda x: x[1])
        return {
            'capsule': best_match[0],
            'confidence': best_match[1],
            'all_matches': scores
        }
    
    return {'capsule': None, 'confidence': 0, 'all_matches': {}}


def main():
    """CLI entry point for navigation execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="{{ORCHESTRATOR_NAME}} Navigation Executor")
    parser.add_argument("intent", help="Navigation intent to execute")
    parser.add_argument("--confidence", "-c", action="store_true", 
                       help="Show confidence analysis only")
    parser.add_argument("--dry-run", "-d", action="store_true",
                       help="Show what would be executed without running it")
    
    args = parser.parse_args()
    
    if args.confidence:
        # Show confidence analysis
        confidence_data = get_navigation_confidence(args.intent)
        print(json.dumps(confidence_data, indent=2))
        return
    
    # Execute navigation
    success, result = execute_navigation(args.intent)
    
    if success:
        if args.dry_run:
            print(f"DRY_RUN: {result}")
        else:
            print(f"EXECUTE: {result}")
    else:
        print(f"ERROR: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()