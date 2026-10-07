"""
Learning system for agentic loops.

Captures success/failure traces for continuous improvement.
"""

from .trace_schema import RemediationTrace, TraceType
from .trace_collector import TraceCollector

__all__ = ['RemediationTrace', 'TraceType', 'TraceCollector']
