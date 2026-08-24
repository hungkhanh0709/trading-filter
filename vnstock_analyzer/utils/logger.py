"""Minimal stderr logger that keeps API stdout valid JSON."""

import sys


class Logger:
    ICONS = {
        'info': 'ℹ️',
        'success': '✅',
        'error': '❌',
    }

    def __init__(self, module_name=''):
        self.module_name = module_name
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(line_buffering=True)

    def _log(self, level, message):
        context = f"[{self.module_name}] " if self.module_name else ''
        print(f"{self.ICONS[level]} {context}{message}", file=sys.stderr)

    def info(self, message):
        self._log('info', message)

    def success(self, message):
        self._log('success', message)

    def error(self, message):
        self._log('error', message)

    def section(self, title):
        print(f"\n{'─' * 60}", file=sys.stderr)
        print(f"  {title}", file=sys.stderr)
        print(f"{'─' * 60}", file=sys.stderr)


def get_logger(module_name=''):
    return Logger(module_name)


__all__ = ['Logger', 'get_logger']
