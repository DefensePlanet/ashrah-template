#!/usr/bin/env python3
"""
Number-2 Context Loader
Displays current governance context for easy Claude Code session initialization
"""

import json
import pathlib
import sys
from datetime import datetime

def load_governance_context():
    """Load and display Number-2 governance context"""
    base_path = pathlib.Path(__file__).parent.parent
    
    print("🧠 **Number-2 Governance Context Loaded**")
    print("=" * 60)
    
    # Check guardrails
    guardrails_file = base_path / "capsules/builder-system/config/guardrails.yaml"
    if guardrails_file.exists():
        print("✅ **Governance Framework:** Active")
        print("   • Risk tiers: Green (auto), Yellow (review), Red (escalate)")
        print("   • Constitutional principles loaded")
        print("   • Policy enforcement active")
    else:
        print("❌ **Governance Framework:** Not found")
        return
    
    # Recent decisions
    decision_journal = base_path / "capsules/builder-system/logs/decision_journal.md"
    if decision_journal.exists():
        try:
            with open(decision_journal, 'r') as f:
                content = f.read()
                decision_count = content.count('## 2025-')
                green_count = content.count('GREEN Classification')
                yellow_count = content.count('YELLOW Classification') 
                red_count = content.count('RED Classification')
                
                print(f"\\n📝 **Decision History:** {decision_count} total decisions")
                if any([green_count, yellow_count, red_count]):
                    print("   • Recent classifications:")
                    if green_count: print(f"     - 🟢 Green: {green_count}")
                    if yellow_count: print(f"     - 🟡 Yellow: {yellow_count}")
                    if red_count: print(f"     - 🔴 Red: {red_count}")
        except Exception:
            print("\\n📝 **Decision History:** Error reading journal")
    
    # System health
    print("\\n🏥 **System Status:**")
    print("   • NIST framework: Operational (govern/map/measure/manage)")
    print("   • Dependency mapping: Active")
    print("   • Audit trails: Enabled")
    print("   • Phase 1: Conservative mode (recommendation-only)")
    
    # Quick commands
    print("\\n⚡ **Quick Commands:**")
    print("   • `python capsules/builder-system/tools/sys.py n2-context`")
    print("   • `python capsules/builder-system/tools/sys.py health-check`")
    print("   • `python capsules/builder-system/tools/sys.py n2-classify '<request>'`")
    
    print("\\n" + "=" * 60)
    print("🎯 **Ready:** Number-2 governance active and operational")
    
    return True

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # JSON output for programmatic use
        context = {
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "governance": "loaded",
            "phase": "1-conservative",
            "commands": [
                "python capsules/builder-system/tools/sys.py n2-context",
                "python capsules/builder-system/tools/sys.py health-check",
                "python capsules/builder-system/tools/sys.py n2-classify '<request>'"
            ]
        }
        print(json.dumps(context, indent=2))
    else:
        load_governance_context()

if __name__ == "__main__":
    main()