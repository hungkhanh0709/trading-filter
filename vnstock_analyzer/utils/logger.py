"""
Unified logging utility for vnstock_analyzer

Provides consistent, professional logging across all modules.
All logs go to stderr, leaving stdout clean for JSON output.
"""

import sys
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """Log levels"""
    DEBUG = 0
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4


class Logger:
    """Centralized logger with consistent formatting"""
    
    # Icons for different log types
    ICONS = {
        LogLevel.DEBUG: '🔍',
        LogLevel.INFO: 'ℹ️',
        LogLevel.SUCCESS: '✅',
        LogLevel.WARNING: '⚠️',
        LogLevel.ERROR: '❌'
    }
    
    def __init__(self, module_name='', min_level=LogLevel.INFO):
        """
        Initialize logger
        
        Args:
            module_name: Name of the module (e.g., 'MWG', 'TechnicalAnalyzer')
            min_level: Minimum log level to display
        """
        self.module_name = module_name
        self.min_level = min_level
        
        # Ensure stderr is line-buffered for real-time output
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(line_buffering=True)
    
    def _log(self, level, message, **kwargs):
        """
        Internal logging method
        
        Args:
            level: LogLevel
            message: Log message
            **kwargs: Additional context (symbol, score, etc.)
        """
        if level.value < self.min_level.value:
            return
        
        icon = self.ICONS.get(level, '')
        
        # Build context string
        context_parts = []
        if self.module_name:
            context_parts.append(self.module_name)
        for key, value in kwargs.items():
            context_parts.append(f"{key}={value}")
        
        context = f"[{' | '.join(context_parts)}]" if context_parts else ""
        
        # Format: 🎯 [Module | context] Message
        log_line = f"{icon} {context} {message}".strip()
        
        print(log_line, file=sys.stderr)
    
    def debug(self, message, **kwargs):
        """Debug log (verbose details)"""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message, **kwargs):
        """Info log (normal operation)"""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def success(self, message, **kwargs):
        """Success log (completed operations)"""
        self._log(LogLevel.SUCCESS, message, **kwargs)
    
    def warning(self, message, **kwargs):
        """Warning log (potential issues)"""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message, **kwargs):
        """Error log (failures)"""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def section(self, title):
        """Print a section header"""
        if self.min_level.value <= LogLevel.INFO.value:
            print(f"\n{'─' * 60}", file=sys.stderr)
            print(f"  {title}", file=sys.stderr)
            print(f"{'─' * 60}", file=sys.stderr)


# Global logger instances
def get_logger(module_name='', level=LogLevel.INFO):
    """
    Get a logger instance
    
    Args:
        module_name: Module name for context
        level: Minimum log level
        
    Returns:
        Logger instance
    """
    return Logger(module_name, level)
