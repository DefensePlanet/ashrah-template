"""
BuilderOS Global Integrations

Centralized integration modules accessible to all capsules.

Available integrations:
- telegram: Telethon client and bot token access via Strongbox
"""

from pathlib import Path

INTEGRATIONS_ROOT = Path(__file__).parent
