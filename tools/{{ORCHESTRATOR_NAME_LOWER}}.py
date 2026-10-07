#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} - Autonomous Catalyst Interface
Your intelligent Number-2 and top agent for the Catalyst
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_builder import IntelligentBuilder
from common.logger import setup_logging
from capsule_pipeline_engine import CapsuleState
from unified_knowledge_graph import UnifiedKnowledgeGraph

class {{ORCHESTRATOR_NAME}}:
    """{{ORCHESTRATOR_NAME}} - Your intelligent Number-2 and top agent"""
    
    def __init__(self):
        self.logger = setup_logging("{{ORCHESTRATOR_NAME_LOWER}}")
        self.builder = IntelligentBuilder()
        self.logger.info("🤖 {{ORCHESTRATOR_NAME}} online. Ready to build anything you need, sir.")
        print("🤖 {{ORCHESTRATOR_NAME}} online. Ready to build anything you need, sir.")
    
    def status_report(self) -> Dict[str, Any]:
        """Generate comprehensive status report"""
        insights = self.builder.get_system_insights()
        
        # Count active work
        pipeline_stats = insights["pipeline_stats"]
        active_count = len([
            c for c in pipeline_stats["capsules"].values() 
            if c["state"] not in ["monitor", "archived"]
        ])
        
        # Knowledge graph health
        knowledge_stats = insights["knowledge_stats"]
        
        print("📊 BUILDER SYSTEM STATUS REPORT")
        print("=" * 50)
        print(f"Total Capsules: {pipeline_stats['total']}")
        print(f"Active Builds: {active_count}")
        print(f"Knowledge Nodes: {knowledge_stats['total_nodes']}")
        print(f"Knowledge Edges: {knowledge_stats['total_edges']}")
        print()
        
        # Show active capsules
        if active_count > 0:
            print("🚧 ACTIVE BUILDS:")
            for name, capsule in pipeline_stats["capsules"].items():
                if capsule["state"] not in ["monitor", "archived"]:
        else:
            print("✅ No active builds - system ready for new work")
        
        print()
        
        # Show most connected knowledge nodes
        if "graph_insights" in insights:
            top_nodes = insights["graph_insights"]["most_connected_nodes"][:3]
            print("🧠 TOP KNOWLEDGE NODES:")
            for node in top_nodes:
                print(f"  • {node['name']}: {node['connections']:.2f} connections")
        
        return insights
    
    def create_capsule(self, name: str, capsule_type: str = "general", 
                      lane: str = "standard", description: Optional[str] = None) -> Dict[str, Any]:
        """Create new capsule with intelligent setup"""
        print(f"🏗️  Creating capsule '{name}' ({capsule_type}, {lane})")
        
        result = self.builder.create_capsule(name, capsule_type, lane)
        
        print(f"✅ Capsule created at: {result['path']}")
        print(f"🎯 Initial state: {result['state']}")
        
        # Show recommendations
        recommendations = result.get("recommendations", [])
        if recommendations:
            print("💡 INTELLIGENT RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations[:5], 1):
                print(f"  {i}. {rec.get('type', 'recommendation')}: {rec.get('agent', rec.get('optimization', 'N/A'))}")
        
        # Generate requirements template with description
        if description:
            capsule_path = Path(result['path'])
            requirements_path = capsule_path / "spec" / "requirements.yaml"
            
            if requirements_path.exists():
                # Update with description
                with open(requirements_path, 'r') as f:
                    content = f.read()
                
                content = content.replace("TODO: Add description", description)
                
                with open(requirements_path, 'w') as f:
                    f.write(content)
                
                print(f"📝 Updated requirements with description")
        
        return result
    
    def advance_capsule(self, name: str) -> bool:
        """Intelligently advance a capsule to next state"""
        print(f"⚡ Advancing capsule '{name}'...")
        
        # Get current status
        status = self.builder.get_capsule_status(name)
        if "error" in status:
            print(f"❌ {status['error']}")
            return False
        
        current_state = status["current_state"]
        print(f"📍 Current state: {current_state}")
        
        # Try to advance
        success = self.builder.pipeline.advance(name)
        
        if success:
            # Get new status
            new_status = self.builder.get_capsule_status(name)
            new_state = new_status["current_state"]
            print(f"✅ Advanced to: {new_state}")
            
            # Show recommendations for new state
            recommendations = new_status.get("recommendations", [])
            if recommendations:
                print("💡 NEXT STEPS:")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {rec.get('reason', rec.get('type', 'recommendation'))}")
        else:
            print(f"⚠️  Cannot advance from {current_state} - check conditions")
            
            # Show what's needed
            context = self.builder.pipeline.capsules.get(name)
            if context:
                if current_state == "ideation":
                    print("   💡 Need: requirements.yaml in spec/ folder")
                elif current_state == "design":
                    print("   💡 Need: design approval or architecture doc")
                elif current_state == "build":
                    print("   💡 Need: source code in src/ and tests/")
                elif current_state == "validate":
                    print("   💡 Need: validation to pass")
                elif current_state == "deploy":
                    print("   💡 Need: deployment approval")
        
        return success
    
    def capsule_details(self, name: str) -> Dict[str, Any]:
        """Get detailed capsule information"""
        status = self.builder.get_capsule_status(name)
        
        if "error" in status:
            print(f"❌ {status['error']}")
            return status
        
        print(f"📋 CAPSULE: {name}")
        print("=" * 40)
        print(f"State: {status['current_state']}")
        print(f"Created: {status['created_at'][:19]}")
        print(f"Updated: {status['updated_at'][:19]}")
        
        # Show metadata
        metadata = status.get("metadata", {})
        if metadata:
            print("\n🏷️  METADATA:")
            for key, value in metadata.items():
                if key not in ["suggested_lane", "lane_suggested"]:
                    print(f"  {key}: {value}")
        
        # Show similar capsules
        similar = status.get("similar_capsules", [])
        if similar:
            print("\n🔍 SIMILAR CAPSULES:")
            for sim in similar[:3]:
                print(f"  • {sim['name']} (similarity: {sim['similarity']:.2f})")
        
        # Show errors if any
        errors = status.get("errors", [])
        if errors:
            print("\n⚠️  ERRORS:")
            for error in errors:
                print(f"  • {error}")
        
        return status
    
    def auto_mode(self):
        """Start autonomous mode"""
        print("🤖 Starting autonomous mode...")
        print("   System will automatically advance capsules when conditions are met")
        print("   Press Ctrl+C to stop")
        
        import asyncio
        try:
            asyncio.run(self.builder.start_autonomous_mode())
        except KeyboardInterrupt:
            print("\n🛑 Autonomous mode stopped")
    
    def quick_build(self, name: str, description: str, build_type: str = "automation"):
        """Quick build for simple projects"""
        print(f"🚀 QUICK BUILD: {name}")
        
        # Create capsule
        result = self.create_capsule(name, build_type, "standard", description)
        
        # Try to advance through ideation immediately
        print("\n⚡ Auto-advancing through ideation...")
        if self.advance_capsule(name):
            print("✅ Ready for design phase")
        
        return result
    
    def wisdom(self, topic: Optional[str] = None) -> None:
        """Share accumulated system wisdom with ML insights"""
        try:
            # Get enhanced insights with ML analytics
            insights = self.builder.get_enhanced_system_insights()
        except:
            # Fallback to basic insights
            insights = self.builder.get_system_insights()
        
        print("🧠 ACCUMULATED WISDOM:")
        print("=" * 30)
        
        # ML Model Status
        if "ml_models" in insights:
            ml_status = insights["ml_models"]
            print(f"🤖 ML Intelligence: {ml_status['models_trained']} models trained on {ml_status['training_data_size']} samples")
        
        # Active Predictions
        if "active_predictions" in insights:
            predictions = insights["active_predictions"]
            if predictions:
                print(f"\n🔮 Current Predictions:")
                for capsule, pred in predictions.items():
                    print(f"  • {capsule}: {pred['predicted_hours']:.1f}h estimated, {pred['success_probability']:.1%} success rate")
        
        if "graph_insights" in insights:
            graph_insights = insights["graph_insights"]
            
            # Common patterns
            patterns = graph_insights.get("common_patterns", {})
            if patterns.get("frequent_agents"):
                print("\nMost Effective Agents:")
                for agent, count in patterns["frequent_agents"][:3]:
                    print(f"  • {agent}: {count} uses")
            
            # Bottlenecks
            bottlenecks = graph_insights.get("bottlenecks", [])
            if bottlenecks:
                print("\nPotential Bottlenecks:")
                for bottleneck in bottlenecks:
                    print(f"  ⚠️  {bottleneck}")
            
            # Success factors
            success_factors = graph_insights.get("success_factors", {})
            if success_factors:
                print("\nSuccess Factors:")
                for factor, value in success_factors.items():
                    print(f"  ✅ {factor}: {value}")
        
        # Performance Analytics
        if "performance_analytics" in insights:
            perf = insights["performance_analytics"]
            if perf.get('current_bottlenecks', {}).get('total', 0) > 0:
                print(f"\n📊 Performance Issues: {perf['current_bottlenecks']['total']} detected")
        
        # Cost Optimization
        if "cost_optimizations" in insights:
            cost_opt = insights["cost_optimizations"]
            if cost_opt.get('potential_savings', 0) > 0:
                print(f"\n💰 Optimization Opportunity: ${cost_opt['potential_savings']:.2f} potential savings")
                if cost_opt.get('top_opportunities'):
                    print("Top recommendation:", cost_opt['top_opportunities'][0]['recommendation'])
        
        # Knowledge stats
        knowledge_stats = insights["knowledge_stats"]
        total_knowledge = knowledge_stats["total_nodes"] + knowledge_stats["total_edges"]
        
        print(f"\n🧠 Knowledge Base: {total_knowledge} units of accumulated intelligence")
        print("Continuously learning and optimizing from every build...")


def main():
    """CLI interface for {{ORCHESTRATOR_NAME}}"""
    parser = argparse.ArgumentParser(
        description="{{ORCHESTRATOR_NAME}} - Your intelligent Number-2 and top agent for the Catalyst",
        epilog="Examples:\n"
               "  {{ORCHESTRATOR_NAME_LOWER}} status          # System status report\n"
               "  {{ORCHESTRATOR_NAME_LOWER}} create my-app   # Create new capsule\n"
               "  {{ORCHESTRATOR_NAME_LOWER}} advance my-app  # Advance capsule to next state\n"
               "  {{ORCHESTRATOR_NAME_LOWER}} auto            # Start autonomous mode\n"
               "  {{ORCHESTRATOR_NAME_LOWER}} quick my-tool 'Quick automation tool'  # Quick build\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new capsule')
    create_parser.add_argument('name', help='Capsule name')
    create_parser.add_argument('--type', default='general', 
                              choices=['general', 'automation', 'web', 'ios', 'macos', 'backend'],
                              help='Capsule type')
    create_parser.add_argument('--lane', default='standard',
                              choices=['standard', 'standard'],
                              help='Lane assignment')
    create_parser.add_argument('--description', help='Project description')
    
    # Advance command
    advance_parser = subparsers.add_parser('advance', help='Advance capsule state')
    advance_parser.add_argument('name', help='Capsule name')
    
    # Details command
    details_parser = subparsers.add_parser('details', help='Show capsule details')
    details_parser.add_argument('name', help='Capsule name')
    
    # Auto mode command
    auto_parser = subparsers.add_parser('auto', help='Start autonomous mode')
    
    # Quick build command
    quick_parser = subparsers.add_parser('quick', help='Quick build for simple projects')
    quick_parser.add_argument('name', help='Project name')
    quick_parser.add_argument('description', help='Project description')
    quick_parser.add_argument('--type', default='automation',
                             help='Project type')
    
    # Wisdom command
    wisdom_parser = subparsers.add_parser('wisdom', help='Share accumulated wisdom')
    wisdom_parser.add_argument('--topic', help='Specific topic')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize {{ORCHESTRATOR_NAME}}
    try:
        {{ORCHESTRATOR_NAME_LOWER}} = {{ORCHESTRATOR_NAME}}()
    except Exception as e:
        print(f"❌ Failed to initialize {{ORCHESTRATOR_NAME}}: {e}")
        return
    
    # Execute command
    try:
        if args.command == 'status':
            {{ORCHESTRATOR_NAME_LOWER}}.status_report()
        
        elif args.command == 'create':
            {{ORCHESTRATOR_NAME_LOWER}}.create_capsule(args.name, args.type, args.lane, args.description)
        
        elif args.command == 'advance':
            {{ORCHESTRATOR_NAME_LOWER}}.advance_capsule(args.name)
        
        elif args.command == 'details':
            {{ORCHESTRATOR_NAME_LOWER}}.capsule_details(args.name)
        
        elif args.command == 'auto':
            {{ORCHESTRATOR_NAME_LOWER}}.auto_mode()
        
        elif args.command == 'quick':
            {{ORCHESTRATOR_NAME_LOWER}}.quick_build(args.name, args.description, args.type)
        
        elif args.command == 'wisdom':
            {{ORCHESTRATOR_NAME_LOWER}}.wisdom(args.topic)
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error executing command: {e}")


if __name__ == "__main__":
    main()