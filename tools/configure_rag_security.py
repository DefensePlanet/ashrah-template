#!/usr/bin/env python3
"""
Configure RAG Service Security
Set up authentication tokens and security settings
"""

import os
import sys
import secrets
from pathlib import Path

# Import Builder modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("paths_config", parent_dir / "global" / "config" / "paths.py")
    paths_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paths_module)
    paths = paths_module.paths
    
    # Import security functions
    spec = importlib.util.spec_from_file_location("security", parent_dir / "global" / "rag" / "service" / "security.py")
    security_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(security_module)
    generate_secure_token = security_module.generate_secure_token
    hash_token = security_module.hash_token
    
except Exception as e:
    print(f"Error importing Builder modules: {e}")
    sys.exit(1)


def create_security_config():
    """Create security configuration for RAG service"""
    print("Builder RAG Service Security Configuration")
    print("=" * 50)
    
    # Check if security config already exists
    security_dir = paths.security
    security_dir.mkdir(parents=True, exist_ok=True)
    
    rag_security_file = security_dir / "rag_security.json"
    
    if rag_security_file.exists():
        print(f"Security config already exists: {rag_security_file}")
        response = input("Do you want to regenerate it? (y/N): ").strip().lower()
        if response != 'y':
            print("Keeping existing configuration.")
            return
    
    # Generate secure token
    auth_token = generate_secure_token()
    print(f"Generated secure authentication token: {auth_token[:8]}...")
    
    # Hash the token for storage
    hashed_token, salt = hash_token(auth_token)
    
    # Create security configuration
    security_config = {
        "rag_service": {
            "auth_enabled": True,
            "auth_token_hash": hashed_token,
            "salt": salt,
            "allowed_origins": [
                "http://localhost:3000",
                "http://127.0.0.1:3000", 
                "http://localhost:8080",
                "http://127.0.0.1:8080"
            ],
            "rate_limit": {
                "enabled": True,
                "max_requests_per_minute": 100,
                "lockout_duration_minutes": 15,
                "max_failed_attempts": 10
            },
            "content_filtering": {
                "enabled": True,
                "scan_for_secrets": True
            }
        },
        "created_at": "2025-08-12T10:32:00Z",
        "version": "1.0.0"
    }
    
    import json
    with open(rag_security_file, 'w') as f:
        json.dump(security_config, f, indent=2)
    
    print(f"Security configuration saved to: {rag_security_file}")
    
    # Create environment setup script
    env_file = paths.tools / "setup_rag_security.sh"
    
    env_content = f"""#!/bin/bash
# RAG Service Security Environment Setup

# Authentication token (keep this secret!)
export BUILDER_RAG_AUTH_TOKEN="{auth_token}"

# CORS origins (adjust as needed)
export BUILDER_RAG_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"

# Service configuration
export BUILDER_RAG_HOST="127.0.0.1"
export BUILDER_RAG_PORT="8000"

echo "RAG Service security environment configured"
echo "Token: {auth_token[:8]}..."
echo "CORS origins: $BUILDER_RAG_ALLOWED_ORIGINS"
echo ""
echo "To start secure RAG service:"
echo "  cd {paths.rag_service}"
echo "  python3 rag_service.py"
echo ""
echo "WARNING: Keep the auth token secure and do not commit it to git!"
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    os.chmod(env_file, 0o700)  # Readable/executable by owner only
    
    print(f"Environment setup script created: {env_file}")
    print("")
    print("Next steps:")
    print(f"  1. Source the environment: source {env_file}")
    print(f"  2. Start RAG service: cd {paths.rag_service} && python3 rag_service.py")
    print("  3. Test with curl:")
    print(f'     curl -H "Authorization: Bearer {auth_token}" http://127.0.0.1:8000/healthz')
    print("")
    print("⚠️  IMPORTANT: Keep the auth token secure!")
    print("   - Do not commit it to git")
    print("   - Store it securely (e.g., in a password manager)")
    print("   - Rotate it periodically")


def test_security_config():
    """Test the current security configuration"""
    print("Testing RAG Service Security Configuration")
    print("=" * 50)
    
    # Check environment variables
    auth_token = os.environ.get('BUILDER_RAG_AUTH_TOKEN')
    allowed_origins = os.environ.get('BUILDER_RAG_ALLOWED_ORIGINS', '*')
    
    print(f"Auth token configured: {'Yes' if auth_token else 'No'}")
    print(f"CORS origins: {allowed_origins}")
    
    if auth_token:
        print(f"Token preview: {auth_token[:8]}...")
        
        # Test token strength
        if len(auth_token) < 32:
            print("⚠️  Warning: Auth token is shorter than recommended (32+ chars)")
        else:
            print("✓ Auth token meets length requirements")
    else:
        print("⚠️  Warning: No auth token configured - service will run without authentication")
    
    # Test service connectivity (if running)
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/healthz", 
                              headers={"Authorization": f"Bearer {auth_token}"} if auth_token else {},
                              timeout=5)
        
        if response.status_code == 200:
            print("✓ RAG service is running and accessible")
        elif response.status_code == 401:
            print("⚠️  RAG service returned 401 - check auth token")
        else:
            print(f"⚠️  RAG service returned {response.status_code}")
            
    except Exception as e:
        print(f"Cannot connect to RAG service (may not be running): {e}")


def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure RAG Service Security")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup command
    subparsers.add_parser("setup", help="Create new security configuration")
    
    # Test command  
    subparsers.add_parser("test", help="Test current security configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "setup":
        create_security_config()
    elif args.command == "test":
        test_security_config()


if __name__ == "__main__":
    main()