"""Logging and JSON helpers used by the analysis CLI."""

import json

import numpy as np

from .logger import get_logger


class NumpyEncoder(json.JSONEncoder):
    """Serialize NumPy scalars and arrays in API responses."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def export_json(result):
    """Return an indented, UTF-8-safe JSON string for stdout."""
    return json.dumps(result, indent=2, ensure_ascii=False, cls=NumpyEncoder)


__all__ = ['NumpyEncoder', 'export_json', 'get_logger']
