"""
Technical Analyzers - MA MASTER FOCUS

Focused entirely on Moving Average (MA) analysis for maximum accuracy and insight.
All other indicators removed to master MA-based trading strategies.

IMPORTANT: TechnicalAnalyzer (orchestrator) được import từ level trên
"""

from .ma_analyzer import MAAnalyzer

__all__ = [
    'MAAnalyzer',
]
