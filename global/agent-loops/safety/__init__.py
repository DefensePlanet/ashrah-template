"""
Adaptive safety mechanisms for agentic loops.

Provides guardrails, resource limits, and stuck detection.
"""

from .adaptive_limits import AdaptiveLimits
from .stuck_detector import StuckDetector
from .resource_guards import ResourceGuard
from .state_isolation import StateIsolation

__all__ = ['AdaptiveLimits', 'StuckDetector', 'ResourceGuard', 'StateIsolation']
