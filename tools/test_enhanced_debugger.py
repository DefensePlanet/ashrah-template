#!/usr/bin/env python3
"""
Test Suite for Enhanced Debugger Agent
Tests hybrid language context and MCP integration
"""

import os
import json
from pathlib import Path
from language_detector import CapsuleLanguageDetector
from mcp_auto_configurator import MCPAutoConfigurator
from debugger_language_patterns import LanguageDebuggingPatterns

def test_language_detection():
    """Test language detection on different capsules"""
    print("=== Testing Language Detection ===")
    
    detector = CapsuleLanguageDetector()
    test_capsules = [
        'capsules/winthemorning',  # Swift/iOS
        'capsules/brandjack',      # Web/Automation
        'testing/capsules/test-mcp-web'  # Web
    ]
    
    results = {}
    for capsule in test_capsules:
        if Path(capsule).exists():
            try:
                context = detector.detect_capsule_language(capsule)
                results[capsule] = {
                    'language': context.primary_language,
                    'technologies': context.technologies,
                    'frameworks': context.frameworks,
                    'mcp_servers': context.mcp_servers,
                    'confidence': context.confidence
                }
                print(f"✅ {capsule}: {context.primary_language} (confidence: {context.confidence:.2f})")
            except Exception as e:
                results[capsule] = {'error': str(e)}
                print(f"❌ {capsule}: Error - {e}")
        else:
            print(f"⚠️  {capsule}: Not found")
    
    return results

def test_mcp_configuration():
    """Test MCP server auto-configuration"""
    print("\n=== Testing MCP Configuration ===")
    
    configurator = MCPAutoConfigurator()
    test_cases = [
        ('capsules/winthemorning', 'swift'),
        ('capsules/brandjack', 'automation'),
    ]
    
    results = {}
    for capsule_path, expected_lang in test_cases:
        if Path(capsule_path).exists():
            try:
                # Detect language first
                context = configurator.detector.detect_capsule_language(capsule_path)
                servers = configurator._get_recommended_servers(context)
                
                results[capsule_path] = {
                    'detected_language': context.primary_language,
                    'expected_language': expected_lang,
                    'recommended_servers': servers,
                    'matches_expected': context.primary_language == expected_lang or expected_lang in context.technologies
                }
                
                status = "✅" if results[capsule_path]['matches_expected'] else "⚠️"
                print(f"{status} {capsule_path}: {context.primary_language} -> {len(servers)} servers")
                
            except Exception as e:
                results[capsule_path] = {'error': str(e)}
                print(f"❌ {capsule_path}: Error - {e}")
        else:
            print(f"⚠️  {capsule_path}: Not found")
    
    return results

def test_debugging_patterns():
    """Test debugging pattern matching"""
    print("\n=== Testing Debugging Patterns ===")
    
    patterns = LanguageDebuggingPatterns()
    test_errors = [
        ('swift', "Cannot find 'ContentView' in scope", 'SwiftUI State Management'),
        ('swift', "Linker command failed with exit code 1", 'Xcode Build Errors'),
        ('javascript', "useEffect has a missing dependency: 'data'", 'React Hook Dependencies'),
        ('python', "ModuleNotFoundError: No module named 'requests'", 'Import and Module Issues'),
        ('automation', "Workflow failed execution at node", 'n8n Workflow Issues')
    ]
    
    results = {}
    for language, error_text, expected_pattern in test_errors:
        # Create mock language context
        from types import SimpleNamespace
        context = SimpleNamespace(
            primary_language=language,
            technologies=[language],
            frameworks=['swiftui'] if language == 'swift' else ['react'] if language == 'javascript' else []
        )
        
        matches = patterns.analyze_error(error_text, context)
        
        if matches:
            best_match = matches[0][0]
            confidence = matches[0][1]
            match_found = expected_pattern in best_match.name
            
            results[f"{language}_{error_text[:20]}"] = {
                'expected_pattern': expected_pattern,
                'found_pattern': best_match.name,
                'confidence': confidence,
                'match_correct': match_found
            }
            
            status = "✅" if match_found else "⚠️"
            print(f"{status} {language}: Found '{best_match.name}' (confidence: {confidence:.2f})")
        else:
            results[f"{language}_{error_text[:20]}"] = {
                'expected_pattern': expected_pattern,
                'found_pattern': None,
                'match_correct': False
            }
            print(f"❌ {language}: No patterns matched")
    
    return results

def test_mcp_query_generation():
    """Test MCP query generation for errors"""
    print("\n=== Testing MCP Query Generation ===")
    
    patterns = LanguageDebuggingPatterns()
    test_cases = [
        ('swift', "SwiftUI layout constraint error", ['apple-doc-mcp']),
        ('javascript', "React component not rendering", ['shadcn-ui']),
        ('automation', "n8n workflow execution failed", ['n8n-mcp'])
    ]
    
    results = {}
    for language, error_text, expected_mcps in test_cases:
        from types import SimpleNamespace
        context = SimpleNamespace(
            primary_language=language,
            technologies=[language],
            frameworks=[]
        )
        
        queries = patterns.get_mcp_queries_for_error(error_text, context)
        
        # Check if expected MCP servers are in queries
        has_expected = any(any(mcp in query for mcp in expected_mcps) for query in queries)
        
        results[f"{language}_{error_text[:20]}"] = {
            'expected_mcps': expected_mcps,
            'generated_queries': queries,
            'has_expected': has_expected,
            'query_count': len(queries)
        }
        
        status = "✅" if has_expected else "⚠️"
        print(f"{status} {language}: Generated {len(queries)} queries, expected MCP: {has_expected}")
    
    return results

def run_full_integration_test():
    """Run full integration test of enhanced debugger"""
    print("\n=== Full Integration Test ===")
    
    # Test scenario: Swift app with SwiftUI error
    capsule_path = 'capsules/winthemorning'
    error_text = "Cannot find 'ContentView' in scope"
    
    if not Path(capsule_path).exists():
        print(f"⚠️  Capsule {capsule_path} not found, using mock test")
        return {'status': 'skipped', 'reason': 'capsule not found'}
    
    try:
        # Step 1: Detect language context
        detector = CapsuleLanguageDetector()
        context = detector.detect_capsule_language(capsule_path)
        print(f"1. Language detected: {context.primary_language}")
        
        # Step 2: Configure MCP servers
        configurator = MCPAutoConfigurator()
        recommended_servers = configurator._get_recommended_servers(context)
        print(f"2. MCP servers recommended: {', '.join(recommended_servers)}")
        
        # Step 3: Analyze error with patterns
        patterns = LanguageDebuggingPatterns()
        error_matches = patterns.analyze_error(error_text, context)
        print(f"3. Error patterns found: {len(error_matches)}")
        
        # Step 4: Generate MCP queries
        mcp_queries = patterns.get_mcp_queries_for_error(error_text, context)
        print(f"4. MCP queries generated: {len(mcp_queries)}")
        
        # Validate integration
        has_swift_support = 'swift' in context.technologies
        has_apple_mcp = 'apple-doc-mcp' in recommended_servers
        has_error_patterns = len(error_matches) > 0
        has_queries = len(mcp_queries) > 0
        
        integration_success = all([has_swift_support, has_apple_mcp, has_error_patterns, has_queries])
        
        result = {
            'status': 'success' if integration_success else 'partial',
            'capsule_path': capsule_path,
            'context': {
                'language': context.primary_language,
                'confidence': context.confidence,
                'frameworks': context.frameworks
            },
            'mcp_servers': recommended_servers,
            'error_analysis': {
                'patterns_found': len(error_matches),
                'best_match': error_matches[0][0].name if error_matches else None,
                'confidence': error_matches[0][1] if error_matches else 0
            },
            'mcp_queries': mcp_queries,
            'integration_checks': {
                'language_support': has_swift_support,
                'mcp_configured': has_apple_mcp,
                'error_patterns': has_error_patterns,
                'mcp_queries': has_queries
            }
        }
        
        status = "✅" if integration_success else "⚠️"
        print(f"{status} Integration test: {'PASSED' if integration_success else 'PARTIAL'}")
        
        return result
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return {'status': 'error', 'error': str(e)}

def main():
    """Run all tests"""
    print("🔧 Enhanced Debugger Agent Test Suite")
    print("=" * 50)
    
    results = {
        'language_detection': test_language_detection(),
        'mcp_configuration': test_mcp_configuration(),
        'debugging_patterns': test_debugging_patterns(),
        'mcp_query_generation': test_mcp_query_generation(),
        'integration_test': run_full_integration_test()
    }
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    for test_name, test_results in results.items():
        if isinstance(test_results, dict) and 'status' in test_results:
            status = test_results['status']
            print(f"   {test_name}: {status.upper()}")
        else:
            print(f"   {test_name}: COMPLETED")
    
    # Save detailed results
    results_file = Path('tools/test_results_debugger.json')
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    return results

if __name__ == '__main__':
    main()